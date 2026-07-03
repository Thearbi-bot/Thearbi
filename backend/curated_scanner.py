"""
curated_scanner.py

Monitors manually curated election pairs PLUS automatically
finds and monitors today's WTI oil pairs.
Sends phone notifications only when opportunities are new or change significantly.

Run:
    python curated_scanner.py
    python curated_scanner.py --loop
"""

import time
import json
import re
import logging
import argparse
import requests
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

KALSHI_BASE           = "https://api.elections.kalshi.com/trade-api/v2"
POLY_GAMMA            = "https://gamma-api.polymarket.com"
KALSHI_FEE            = 0.01
POLYMARKET_FEE        = 0.02
MIN_PROFIT_THRESHOLD  = 0.02
POLL_INTERVAL_SECONDS = 30
STALE_TOL             = 0.015
MAX_SPREAD            = 0.15

# Only re-notify if profit changes by more than this amount
NOTIFY_CHANGE_THRESHOLD = 0.01  # 1%

# Track last notified profit per pair label
_last_notified: dict[str, float] = {}

# =============================================================================
# STATIC ELECTION PAIRS
# =============================================================================
STATIC_PAIRS = [
    {
        "label": "Republican Senate Control 2026",
        "kalshi_ticker": "CONTROLS-2026-R",
        "polymarket_slug": "will-the-republican-party-control-the-senate-after-the-2026-midterm-elections",
    },
    {
        "label": "Democrat Senate Control 2026",
        "kalshi_ticker": "CONTROLS-2026-D",
        "polymarket_slug": "will-the-democratic-party-control-the-senate-after-the-2026-midterm-elections",
    },
    {
        "label": "Republican House Control 2026",
        "kalshi_ticker": "CONTROLH-2026-R",
        "polymarket_slug": "will-the-republican-party-control-the-house-after-the-2026-midterm-elections",
    },
    {
        "label": "Democrat House Control 2026",
        "kalshi_ticker": "CONTROLH-2026-D",
        "polymarket_slug": "will-the-democratic-party-control-the-house-after-the-2026-midterm-elections",
    },
    {
        "label": "Trump Impeached by Sep 2026",
        "kalshi_ticker": "KXIMPEACH-26-SEP01",
        "polymarket_slug": "will-trump-be-impeached-by-december-31-2026",
    },
]


def _is_stale(price):
    return abs(price - 0.50) < STALE_TOL


def _get_poly_price(mkt):
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


def get_wti_pairs():
    pairs = []
    try:
        resp = requests.get(
            f"{KALSHI_BASE}/markets",
            params={"status": "open", "limit": 200, "series_ticker": "KXWTI"},
            timeout=10,
        )
        kalshi_markets = {}
        for m in resp.json().get("markets", []):
            price = m.get("yes_ask_dollars") or m.get("last_price_dollars")
            if not price or float(price) <= 0:
                continue
            close = m.get("close_time", "")[:10]
            match = re.search(r"above (\d+\.\d+)", m.get("title", "").lower())
            if match:
                threshold = float(match.group(1))
                kalshi_markets[(close, threshold)] = {
                    "ticker": m.get("ticker"),
                    "price":  float(price),
                }
    except Exception as e:
        log.debug(f"WTI Kalshi fetch error: {e}")
        return []

    try:
        resp = requests.get(
            f"{POLY_GAMMA}/events",
            params={"series_slug": "wti-daily-close-uo", "limit": 10,
                    "active": "true", "closed": "false"},
            timeout=10,
        )
        data   = resp.json()
        events = data if isinstance(data, list) else data.get("data", [])

        poly_markets = {}
        for event in events:
            slug     = event.get("slug", "")
            end_date = event.get("endDate", "")[:10]
            resp2    = requests.get(f"{POLY_GAMMA}/events", params={"slug": slug}, timeout=10)
            data2    = resp2.json()
            if not data2:
                continue
            for m in data2[0].get("markets", []):
                price = _get_poly_price(m)
                if price is None:
                    continue
                match = re.search(r"above \$(\d+)", m.get("question", "").lower())
                if match:
                    threshold = float(match.group(1))
                    poly_markets[(end_date, threshold)] = {
                        "slug":  m.get("slug"),
                        "price": price,
                    }
    except Exception as e:
        log.debug(f"WTI Polymarket fetch error: {e}")
        return []

    for (k_close, k_thresh), k_mkt in kalshi_markets.items():
        p_thresh = float(round(k_thresh + 0.01))
        p_key    = (k_close, p_thresh)
        if p_key in poly_markets:
            pairs.append({
                "label":           f"WTI above ${int(p_thresh)} on {k_close}",
                "kalshi_ticker":   k_mkt["ticker"],
                "polymarket_slug": poly_markets[p_key]["slug"],
            })

    log.info(f"  Auto-found {len(pairs)} WTI pairs with real prices")
    return pairs


def should_notify(label: str, profit: float) -> bool:
    """
    Returns True only if this is a new opportunity or
    the profit has changed significantly from last notification.
    """
    if label not in _last_notified:
        return True
    last = _last_notified[label]
    return abs(profit - last) >= NOTIFY_CHANGE_THRESHOLD


def send_phone_notification(title: str, message: str):
    user_key  = os.getenv("PUSHOVER_USER_KEY")
    api_token = os.getenv("PUSHOVER_API_TOKEN")
    if not user_key or not api_token:
        return
    try:
        resp = requests.post(
            "https://api.pushover.net/1/messages.json",
            data={"token": api_token, "user": user_key,
                  "title": title, "message": message,
                  "sound": "cashregister", "priority": 1},
            timeout=10,
        )
        if resp.status_code == 200:
            log.info("  Phone notification sent!")
    except Exception as e:
        log.error(f"Pushover error: {e}")


def fetch_kalshi_price(ticker):
    try:
        resp = requests.get(f"{KALSHI_BASE}/markets/{ticker}", timeout=10)
        resp.raise_for_status()
        mkt       = resp.json().get("market", {})
        yes_price = None
        for field in ["yes_ask_dollars", "last_price_dollars"]:
            val = mkt.get(field)
            if val and float(val) > 0:
                yes_price = float(val)
                break
        if yes_price is None:
            return None
        return {"yes_price": yes_price, "title": mkt.get("title", "")}
    except Exception as e:
        log.error(f"Kalshi fetch error for {ticker}: {e}")
        return None


def fetch_polymarket_price(slug):
    try:
        resp = requests.get(
            f"{POLY_GAMMA}/markets",
            params={"slug": slug},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        mkt  = data[0] if isinstance(data, list) and data else None
        if not mkt:
            return None
        price = _get_poly_price(mkt)
        if price is None:
            return None
        return {"yes_price": price, "title": mkt.get("question", "")}
    except Exception as e:
        log.error(f"Polymarket fetch error for {slug}: {e}")
        return None


def calculate_profit(kalshi_price, poly_price):
    if kalshi_price < poly_price:
        gap       = 1 - (kalshi_price + (1 - poly_price))
        direction = "BUY YES on Kalshi / BUY NO on Polymarket"
    else:
        gap       = 1 - (poly_price + (1 - kalshi_price))
        direction = "BUY YES on Polymarket / BUY NO on Kalshi"
    return gap, gap - KALSHI_FEE - POLYMARKET_FEE, direction


def scan_once(all_pairs):
    log.info(f"Checking {len(all_pairs)} pair(s)...")

    for pair in all_pairs:
        kalshi_data = fetch_kalshi_price(pair["kalshi_ticker"])
        poly_data   = fetch_polymarket_price(pair["polymarket_slug"])

        if not kalshi_data or not poly_data:
            log.warning(f"  Could not fetch: {pair['label']}")
            continue

        k_price            = kalshi_data["yes_price"]
        p_price            = poly_data["yes_price"]
        gap, profit, direction = calculate_profit(k_price, p_price)
        status             = "OPPORTUNITY" if profit >= MIN_PROFIT_THRESHOLD else "no edge"

        log.info(
            f"  [{status}] {pair['label']}\n"
            f"      Kalshi: {k_price*100:.1f}c  |  Polymarket: {p_price*100:.1f}c  |  "
            f"Gap: {gap*100:.2f}%  |  Net: {profit*100:.2f}%"
        )

        if profit >= MIN_PROFIT_THRESHOLD:
            log.warning(
                f"\n  *** REAL OPPORTUNITY ***\n"
                f"  {pair['label']}\n"
                f"  Kalshi    : {k_price*100:.1f}c YES\n"
                f"  Polymarket: {p_price*100:.1f}c YES\n"
                f"  Net profit: {profit*100:.2f}% after fees\n"
                f"  Action    : {direction}\n"
            )

            if should_notify(pair["label"], profit):
                last = _last_notified.get(pair["label"])
                is_new = last is None
                change_str = "" if is_new else f" (was {last*100:.1f}%)"
                send_phone_notification(
                    title="ARB OPPORTUNITY" + (" 🆕" if is_new else " 📈"),
                    message=(
                        f"{pair['label']}\n"
                        f"Net: {profit*100:.1f}%{change_str}\n"
                        f"Kalshi: {k_price*100:.1f}c | Poly: {p_price*100:.1f}c\n"
                        f"{direction}"
                    ),
                )
                _last_notified[pair["label"]] = profit
            else:
                log.info(f"  Skipping notification — profit unchanged from last alert ({_last_notified.get(pair['label'], 0)*100:.1f}%)")

        else:
            # Opportunity gone — clear it from tracking so next time it appears it notifies again
            if pair["label"] in _last_notified:
                log.info(f"  Opportunity closed for {pair['label']} — reset notification tracker")
                del _last_notified[pair["label"]]


def run_loop():
    log.info("=== Curated Pair Scanner Started ===")
    log.info(f"Static election pairs: {len(STATIC_PAIRS)}")
    log.info(f"Min profit threshold: {MIN_PROFIT_THRESHOLD*100:.0f}%")
    log.info(f"Re-notify threshold: >{NOTIFY_CHANGE_THRESHOLD*100:.0f}% change")
    log.info("WTI oil pairs: auto-detected, stale + wide-spread filtered")
    log.info(f"Scanning every {POLL_INTERVAL_SECONDS}s\n")

    while True:
        try:
            wti_pairs = get_wti_pairs()
            scan_once(STATIC_PAIRS + wti_pairs)
        except Exception as e:
            log.exception(f"Scan error: {e}")
        log.info(f"Sleeping {POLL_INTERVAL_SECONDS}s...\n")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()
    if args.loop:
        run_loop()
    else:
        wti_pairs = get_wti_pairs()
        scan_once(STATIC_PAIRS + wti_pairs)