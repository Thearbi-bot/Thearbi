"""
weekly_check.py

Finds current WTI oil pairs between Kalshi and Polymarket.
Uses Polymarket CLOB API for live prices.

Run any morning:
    python weekly_check.py
"""

import json
import re
import logging
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

KALSHI_BASE    = "https://api.elections.kalshi.com/trade-api/v2"
POLY_GAMMA     = "https://gamma-api.polymarket.com"
POLY_CLOB      = "https://clob.polymarket.com"
KALSHI_FEE     = 0.01
POLYMARKET_FEE = 0.02


def send_notification(title, message):
    user_key  = os.getenv("PUSHOVER_USER_KEY")
    api_token = os.getenv("PUSHOVER_API_TOKEN")
    if not user_key or not api_token:
        return
    try:
        requests.post("https://api.pushover.net/1/messages.json", data={
            "token": api_token, "user": user_key,
            "title": title, "message": message, "sound": "pushover",
        }, timeout=10)
    except Exception as e:
        log.error(f"Notification error: {e}")


def get_clob_price(yes_token):
    """Get live price from Polymarket CLOB API."""
    try:
        resp = requests.get(
            f"{POLY_CLOB}/last-trade-price",
            params={"token_id": yes_token},
            timeout=10,
        )
        data  = resp.json()
        price = data.get("price")
        return float(price) if price else None
    except Exception:
        return None


def get_kalshi_wti():
    markets = {}
    resp = requests.get(
        f"{KALSHI_BASE}/markets",
        params={"status": "open", "limit": 200, "series_ticker": "KXWTI"},
        timeout=10,
    )
    for m in resp.json().get("markets", []):
        price = m.get("yes_ask_dollars") or m.get("last_price_dollars")
        if not price or float(price) <= 0:
            continue
        close = m.get("close_time", "")[:10]
        match = re.search(r"above (\d+\.\d+)", m.get("title", "").lower())
        if match:
            threshold = float(match.group(1))
            markets[(close, threshold)] = {
                "ticker": m.get("ticker"),
                "title":  m.get("title", ""),
                "price":  float(price),
            }
    log.info(f"  Kalshi: {len(markets)} WTI markets")
    return markets


def get_polymarket_wti():
    markets = {}
    resp = requests.get(
        f"{POLY_GAMMA}/events",
        params={"series_slug": "wti-daily-close-uo", "limit": 10,
                "active": "true", "closed": "false"},
        timeout=10,
    )
    data   = resp.json()
    events = data if isinstance(data, list) else data.get("data", [])
    log.info(f"  Polymarket: {len(events)} active WTI events")

    for event in events:
        slug     = event.get("slug", "")
        end_date = event.get("endDate", "")[:10]
        resp2    = requests.get(f"{POLY_GAMMA}/events", params={"slug": slug}, timeout=10)
        data2    = resp2.json()
        if not data2:
            continue

        for m in data2[0].get("markets", []):
            token_ids = m.get("clobTokenIds")
            if isinstance(token_ids, str):
                token_ids = json.loads(token_ids)
            if not token_ids:
                continue

            yes_token   = token_ids[0]
            live_price  = get_clob_price(yes_token)
            if live_price is None or live_price <= 0:
                continue

            match = re.search(r"above \$(\d+)", m.get("question", "").lower())
            if match:
                threshold = float(match.group(1))
                markets[(end_date, threshold)] = {
                    "slug":      m.get("slug"),
                    "question":  m.get("question", ""),
                    "price":     live_price,
                    "yes_token": yes_token,
                }

    log.info(f"  Polymarket: {len(markets)} WTI sub-markets (live CLOB prices)")
    return markets


def find_pairs(kalshi, poly):
    pairs = []
    for (k_close, k_thresh), k_mkt in kalshi.items():
        p_thresh = float(round(k_thresh + 0.01))
        p_key    = (k_close, p_thresh)
        if p_key in poly:
            p_mkt     = poly[p_key]
            gap       = abs(k_mkt["price"] - p_mkt["price"])
            net       = gap - KALSHI_FEE - POLYMARKET_FEE
            direction = ("BUY YES Kalshi / BUY NO Polymarket"
                         if k_mkt["price"] < p_mkt["price"]
                         else "BUY YES Polymarket / BUY NO Kalshi")
            pairs.append({
                "label":           f"WTI above ${int(p_thresh)} on {k_close}",
                "kalshi_ticker":   k_mkt["ticker"],
                "polymarket_slug": p_mkt["slug"],
                "kalshi_price":    k_mkt["price"],
                "poly_price":      p_mkt["price"],
                "gap":             gap,
                "net":             net,
                "direction":       direction,
                "close":           k_close,
            })
    return sorted(pairs, key=lambda x: (x["close"], -x["net"]))


def run():
    log.info("=== WTI Pair Finder (Live CLOB Prices) ===\n")

    log.info("Fetching Kalshi WTI markets...")
    kalshi = get_kalshi_wti()

    log.info("Fetching Polymarket WTI markets (live prices)...")
    poly = get_polymarket_wti()

    log.info("Matching pairs...")
    pairs = find_pairs(kalshi, poly)

    if not pairs:
        log.info("No WTI pairs found. Try again tomorrow.")
        send_notification("WTI Check", "No active WTI pairs found.")
        return

    profitable = [p for p in pairs if p["net"] >= 0.02]

    print("\n" + "="*65)
    print(f"FOUND {len(pairs)} PAIRS  |  {len(profitable)} PROFITABLE")
    print("="*65)

    for p in pairs:
        status = "*** PROFITABLE ***" if p["net"] >= 0.02 else "monitoring"
        print(f"\n[{status}]  {p['label']}")
        print(f"  Kalshi: {p['kalshi_price']*100:.1f}c  |  Polymarket (live): {p['poly_price']*100:.1f}c")
        print(f"  Gap: {p['gap']*100:.1f}%  |  Net: {p['net']*100:.1f}%")
        print(f"  Action: {p['direction']}")

    if profitable:
        print("\n" + "="*65)
        print("PASTE THESE INTO curated_scanner.py STATIC_PAIRS list:")
        print("="*65)
        for p in profitable:
            print(f"""
    {{
        "label": "{p['label']}",
        "kalshi_ticker": "{p['kalshi_ticker']}",
        "polymarket_slug": "{p['polymarket_slug']}",
    }},""")

        send_notification(
            f"WTI: {len(profitable)} profitable pair(s)!",
            "\n".join(f"{p['label']}: {p['net']*100:.1f}% net" for p in profitable[:5])
        )
    else:
        best = max(pairs, key=lambda x: x["net"])
        send_notification(
            f"WTI: {len(pairs)} pairs, none profitable yet",
            f"Best: {best['label']} at {best['net']*100:.1f}% net"
        )


if __name__ == "__main__":
    run()