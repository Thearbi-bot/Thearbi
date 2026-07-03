"""
api.py — FastAPI server for The Arbi dashboard.
Handles scan results, Stripe webhooks, and user notifications.
"""

import json
import re
import os
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests as http
import stripe

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="The Arbi API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

KALSHI_BASE    = "https://api.elections.kalshi.com/trade-api/v2"
POLY_GAMMA     = "https://gamma-api.polymarket.com"
KALSHI_FEE     = 0.01
POLYMARKET_FEE = 0.02
STALE_TOL      = 0.015
MAX_SPREAD     = 0.15

stripe.api_key       = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET       = os.getenv("STRIPE_WEBHOOK_SECRET")
CLERK_SECRET_KEY     = os.getenv("CLERK_SECRET_KEY")
PUSHOVER_API_TOKEN   = os.getenv("PUSHOVER_API_TOKEN")

# Deduplication: track last notified profit per pair
_last_notified: dict[str, float] = {}
NOTIFY_CHANGE_THRESHOLD = 0.01

STATIC_PAIRS = [
    {"label": "Republican Senate Control 2026",  "kalshi_ticker": "CONTROLS-2026-R",    "polymarket_slug": "will-the-republican-party-control-the-senate-after-the-2026-midterm-elections"},
    {"label": "Democrat Senate Control 2026",    "kalshi_ticker": "CONTROLS-2026-D",    "polymarket_slug": "will-the-democratic-party-control-the-senate-after-the-2026-midterm-elections"},
    {"label": "Republican House Control 2026",   "kalshi_ticker": "CONTROLH-2026-R",    "polymarket_slug": "will-the-republican-party-control-the-house-after-the-2026-midterm-elections"},
    {"label": "Democrat House Control 2026",     "kalshi_ticker": "CONTROLH-2026-D",    "polymarket_slug": "will-the-democratic-party-control-the-house-after-the-2026-midterm-elections"},
    {"label": "Trump Impeached by Sep 2026",     "kalshi_ticker": "KXIMPEACH-26-SEP01", "polymarket_slug": "will-trump-be-impeached-by-december-31-2026"},
]


def _is_stale(price: float) -> bool:
    return abs(price - 0.50) < STALE_TOL


def _get_poly_price(mkt: dict):
    bid = mkt.get("bestBid")
    ask = mkt.get("bestAsk")
    if bid and ask and float(bid) > 0 and float(ask) > 0:
        bid_f  = float(bid)
        ask_f  = float(ask)
        if ask_f - bid_f > MAX_SPREAD:
            return None
        price = (bid_f + ask_f) / 2
        return None if _is_stale(price) else price
    prices = mkt.get("outcomePrices")
    if prices:
        if isinstance(prices, str):
            prices = json.loads(prices)
        if prices and float(prices[0]) > 0:
            price = float(prices[0])
            return None if _is_stale(price) else price
    return None


def fetch_kalshi(ticker: str):
    try:
        r = http.get(f"{KALSHI_BASE}/markets/{ticker}", timeout=8)
        mkt = r.json().get("market", {})
        for field in ["yes_ask_dollars", "last_price_dollars"]:
            val = mkt.get(field)
            if val and float(val) > 0:
                return float(val)
    except Exception:
        pass
    return None


def fetch_poly(slug: str):
    try:
        r = http.get(f"{POLY_GAMMA}/markets", params={"slug": slug}, timeout=8)
        data = r.json()
        mkt  = data[0] if isinstance(data, list) and data else None
        if mkt:
            return _get_poly_price(mkt)
    except Exception:
        pass
    return None


def get_wti_pairs():
    pairs = []
    try:
        r = http.get(f"{KALSHI_BASE}/markets", params={"status": "open", "limit": 200, "series_ticker": "KXWTI"}, timeout=8)
        kalshi_mkts = {}
        for m in r.json().get("markets", []):
            price = m.get("yes_ask_dollars") or m.get("last_price_dollars")
            if not price or float(price) <= 0:
                continue
            close = m.get("close_time", "")[:10]
            match = re.search(r"above (\d+\.\d+)", m.get("title", "").lower())
            if match:
                kalshi_mkts[(close, float(match.group(1)))] = {"ticker": m["ticker"], "price": float(price)}

        r2     = http.get(f"{POLY_GAMMA}/events", params={"series_slug": "wti-daily-close-uo", "limit": 10, "active": "true", "closed": "false"}, timeout=8)
        events = r2.json() if isinstance(r2.json(), list) else r2.json().get("data", [])
        poly_mkts = {}
        for ev in events:
            slug     = ev.get("slug", "")
            end_date = ev.get("endDate", "")[:10]
            r3       = http.get(f"{POLY_GAMMA}/events", params={"slug": slug}, timeout=8)
            d3       = r3.json()
            if not d3:
                continue
            for m in d3[0].get("markets", []):
                price = _get_poly_price(m)
                if price is None:
                    continue
                match = re.search(r"above \$(\d+)", m.get("question", "").lower())
                if match:
                    poly_mkts[(end_date, float(match.group(1)))] = {"slug": m["slug"], "price": price}

        for (close, k_thresh), k_mkt in kalshi_mkts.items():
            p_thresh = float(round(k_thresh + 0.01))
            if (close, p_thresh) in poly_mkts:
                p_mkt = poly_mkts[(close, p_thresh)]
                pairs.append({"label": f"WTI above ${int(p_thresh)} on {close}", "kalshi_ticker": k_mkt["ticker"], "polymarket_slug": p_mkt["slug"]})
    except Exception as e:
        log.error(f"WTI fetch error: {e}")
    return pairs


def run_scan(pairs):
    results = []
    for pair in pairs:
        k_price = fetch_kalshi(pair["kalshi_ticker"])
        p_price = fetch_poly(pair["polymarket_slug"])
        if k_price is None or p_price is None:
            continue
        if k_price < p_price:
            gap       = 1 - (k_price + (1 - p_price))
            direction = "BUY YES on Kalshi / BUY NO on Polymarket"
        else:
            gap       = 1 - (p_price + (1 - k_price))
            direction = "BUY YES on Polymarket / BUY NO on Kalshi"
        net = gap - KALSHI_FEE - POLYMARKET_FEE
        results.append({
            "label":          pair["label"],
            "kalshi_price":   round(k_price, 4),
            "poly_price":     round(p_price, 4),
            "gap":            round(gap, 4),
            "net_profit":     round(net, 4),
            "direction":      direction,
            "is_opportunity": net >= 0.02,
            "timestamp":      datetime.now(timezone.utc).isoformat(),
        })
    results.sort(key=lambda x: x["net_profit"], reverse=True)
    return results


def get_subscribed_user_pushover_keys():
    """Fetch all subscribed users from Clerk and return their Pushover keys."""
    if not CLERK_SECRET_KEY:
        return []
    try:
        resp = http.get(
            "https://api.clerk.com/v1/users",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
            params={"limit": 100},
            timeout=10,
        )
        users = resp.json()
        keys = []
        for user in users:
            metadata = user.get("unsafe_metadata", {})
            if metadata.get("subscribed") and metadata.get("pushover_key"):
                keys.append(metadata["pushover_key"])
        return keys
    except Exception as e:
        log.error(f"Error fetching Clerk users: {e}")
        return []


def send_pushover(user_key: str, title: str, message: str):
    """Send a Pushover notification to a specific user."""
    if not PUSHOVER_API_TOKEN:
        return
    try:
        http.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token":    PUSHOVER_API_TOKEN,
                "user":     user_key,
                "title":    title,
                "message":  message,
                "sound":    "cashregister",
                "priority": 1,
            },
            timeout=10,
        )
    except Exception as e:
        log.error(f"Pushover error: {e}")


def notify_all_users(results: list):
    """Check scan results and notify all subscribed users of opportunities."""
    opportunities = [r for r in results if r["is_opportunity"]]
    if not opportunities:
        # Clear closed opportunities from dedup tracker
        for label in list(_last_notified.keys()):
            if label not in [r["label"] for r in results]:
                del _last_notified[label]
        return

    # Get all user Pushover keys
    user_keys = get_subscribed_user_pushover_keys()
    if not user_keys:
        return

    for opp in opportunities:
        label  = opp["label"]
        profit = opp["net_profit"]

        # Check if we should notify (new or changed significantly)
        last = _last_notified.get(label)
        should_notify = last is None or abs(profit - last) >= NOTIFY_CHANGE_THRESHOLD

        if not should_notify:
            continue

        is_new     = last is None
        change_str = "" if is_new else f" (was {last*100:.1f}%)"
        title      = "ARB OPPORTUNITY 🆕" if is_new else "ARB OPPORTUNITY 📈"
        message    = (
            f"{label}\n"
            f"Net: {profit*100:.1f}%{change_str}\n"
            f"Kalshi: {opp['kalshi_price']*100:.1f}c | Poly: {opp['poly_price']*100:.1f}c\n"
            f"{opp['direction']}"
        )

        for user_key in user_keys:
            send_pushover(user_key, title, message)

        _last_notified[label] = profit
        log.info(f"Notified {len(user_keys)} user(s) about {label}")

    # Clear opportunities that are no longer profitable
    for label in list(_last_notified.keys()):
        if label not in [o["label"] for o in opportunities]:
            del _last_notified[label]


def update_clerk_subscription(user_id: str, subscribed: bool):
    if not CLERK_SECRET_KEY:
        return
    try:
        resp = http.patch(
            f"https://api.clerk.com/v1/users/{user_id}/metadata",
            headers={
                "Authorization": f"Bearer {CLERK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            json={"unsafe_metadata": {"subscribed": subscribed}},
            timeout=10,
        )
        if resp.status_code == 200:
            log.info(f"Updated Clerk metadata for {user_id}: subscribed={subscribed}")
        else:
            log.error(f"Clerk metadata update failed: {resp.text}")
    except Exception as e:
        log.error(f"Clerk update error: {e}")


@app.get("/scan")
def scan():
    wti     = get_wti_pairs()
    pairs   = STATIC_PAIRS + wti
    results = run_scan(pairs)

    # Notify all subscribed users of opportunities
    notify_all_users(results)

    return {
        "results":             results,
        "last_scan":           datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "total_pairs":         len(pairs),
        "opportunities_found": sum(1 for r in results if r["is_opportunity"]),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    log.info(f"Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("userId")
        if user_id:
            update_clerk_subscription(user_id, True)
            log.info(f"Subscription activated for user {user_id}")

    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id  = subscription.get("customer")
        log.info(f"Subscription cancelled for customer {customer_id}")

    elif event_type == "customer.subscription.updated":
        subscription = event["data"]["object"]
        status       = subscription.get("status")
        log.info(f"Subscription updated: status={status}")

    return JSONResponse({"status": "ok"})