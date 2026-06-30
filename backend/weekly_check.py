"""
weekly_check.py

Finds current WTI oil pairs between Kalshi and Polymarket.
Uses bestBid/bestAsk midpoint for accurate prices.
Filters stale 50c prices and wide spreads instead of volume.

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
KALSHI_FEE     = 0.01
POLYMARKET_FEE = 0.02
STALE_TOL      = 0.015   # filter prices within 1.5c of 50c
MAX_SPREAD     = 0.15    # filter markets with bid/ask spread > 15c (too illiquid)


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


def _is_stale(price):
    return abs(price - 0.50) < STALE_TOL


def _get_poly_price(mkt):
    """
    Get price using bestBid/bestAsk midpoint.
    Filters stale prices and markets with spreads too wide to trade.
    """
    bid = mkt.get("bestBid")
    ask = mkt.get("bestAsk")

    if bid and ask and float(bid) > 0 and float(ask) > 0:
        bid_f = float(bid)
        ask_f = float(ask)
        spread = ask_f - bid_f

        # Skip if spread is too wide — market not liquid enough
        if spread > MAX_SPREAD:
            return None

        price = (bid_f + ask_f) / 2
        if _is_stale(price):
            return None
        return price

    # Fallback to outcomePrices
    prices = mkt.get("outcomePrices")
    if prices:
        if isinstance(prices, str):
            prices = json.loads(prices)
        if prices and float(prices[0]) > 0:
            price = float(prices[0])
            if _is_stale(price):
                return None
            return price

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
            price = _get_poly_price(m)
            if price is None:
                continue
            match = re.search(r"above \$(\d+)", m.get("question", "").lower())
            if match:
                threshold = float(match.group(1))
                bid = float(m.get("bestBid") or 0)
                ask = float(m.get("bestAsk") or 0)
                markets[(end_date, threshold)] = {
                    "slug":     m.get("slug"),
                    "question": m.get("question", ""),
                    "price":    price,
                    "spread":   round(ask - bid, 4),
                }

    log.info(f"  Polymarket: {len(markets)} WTI markets with tight enough spreads")
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
                "spread":          p_mkt["spread"],
                "gap":             gap,
                "net":             net,
                "direction":       direction,
                "close":           k_close,
            })
    return sorted(pairs, key=lambda x: (x["close"], -x["net"]))


def run():
    log.info("=== WTI Pair Finder ===")
    log.info(f"Spread filter: max {MAX_SPREAD*100:.0f}c | Stale filter: ±{STALE_TOL*100:.1f}c from 50c\n")

    log.info("Fetching Kalshi WTI markets...")
    kalshi = get_kalshi_wti()

    log.info("Fetching Polymarket WTI markets...")
    poly = get_polymarket_wti()

    log.info("Matching pairs...")
    pairs = find_pairs(kalshi, poly)

    if not pairs:
        log.info("No WTI pairs with tight spreads found yet. Try again later.")
        send_notification("WTI Check", "No liquid WTI pairs found yet.")
        return

    profitable = [p for p in pairs if p["net"] >= 0.02]

    print("\n" + "="*65)
    print(f"FOUND {len(pairs)} PAIRS  |  {len(profitable)} PROFITABLE")
    print("="*65)

    for p in pairs:
        status = "*** PROFITABLE ***" if p["net"] >= 0.02 else "monitoring"
        print(f"\n[{status}]  {p['label']}")
        print(f"  Kalshi: {p['kalshi_price']*100:.1f}c  |  Polymarket: {p['poly_price']*100:.1f}c  |  Spread: {p['spread']*100:.1f}c")
        print(f"  Gap: {p['gap']*100:.1f}%  |  Net: {p['net']*100:.1f}%")
        print(f"  Action: {p['direction']}")

    if profitable:
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