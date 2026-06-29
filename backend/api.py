"""
api.py — lightweight FastAPI server for the dashboard.
Runs the scanner logic and serves results as JSON.

Install: pip install fastapi uvicorn
Run:     uvicorn api:app --reload --port 8000
"""

import json
import re
import logging
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests as http

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Arb Scanner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

KALSHI_BASE    = "https://api.elections.kalshi.com/trade-api/v2"
POLY_GAMMA     = "https://gamma-api.polymarket.com"
KALSHI_FEE     = 0.01
POLYMARKET_FEE = 0.02
MIN_VOLUME     = 500
STALE_TOL      = 0.015

STATIC_PAIRS = [
    {"label": "Republican Senate Control 2026",  "kalshi_ticker": "CONTROLS-2026-R",   "polymarket_slug": "will-the-republican-party-control-the-senate-after-the-2026-midterm-elections"},
    {"label": "Democrat Senate Control 2026",    "kalshi_ticker": "CONTROLS-2026-D",   "polymarket_slug": "will-the-democratic-party-control-the-senate-after-the-2026-midterm-elections"},
    {"label": "Republican House Control 2026",   "kalshi_ticker": "CONTROLH-2026-R",   "polymarket_slug": "will-the-republican-party-control-the-house-after-the-2026-midterm-elections"},
    {"label": "Democrat House Control 2026",     "kalshi_ticker": "CONTROLH-2026-D",   "polymarket_slug": "will-the-democratic-party-control-the-house-after-the-2026-midterm-elections"},
    {"label": "Trump Impeached by Sep 2026",     "kalshi_ticker": "KXIMPEACH-26-SEP01","polymarket_slug": "will-trump-be-impeached-by-december-31-2026"},
]


def _is_stale(price: float) -> bool:
    return abs(price - 0.50) < STALE_TOL


def _get_poly_price(mkt: dict):
    volume = float(mkt.get("volume24hr") or mkt.get("volume") or 0)
    if volume < MIN_VOLUME:
        return None
    bid = mkt.get("bestBid")
    ask = mkt.get("bestAsk")
    if bid and ask and float(bid) > 0 and float(ask) > 0:
        price = (float(bid) + float(ask)) / 2
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

        r2    = http.get(f"{POLY_GAMMA}/events", params={"series_slug": "wti-daily-close-uo", "limit": 10, "active": "true", "closed": "false"}, timeout=8)
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
            "label":        pair["label"],
            "kalshi_price": round(k_price, 4),
            "poly_price":   round(p_price, 4),
            "gap":          round(gap, 4),
            "net_profit":   round(net, 4),
            "direction":    direction,
            "is_opportunity": net >= 0.02,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
        })
    results.sort(key=lambda x: x["net_profit"], reverse=True)
    return results


@app.get("/scan")
def scan():
    wti   = get_wti_pairs()
    pairs = STATIC_PAIRS + wti
    results = run_scan(pairs)
    return {
        "results":             results,
        "last_scan":           datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
        "total_pairs":         len(pairs),
        "opportunities_found": sum(1 for r in results if r["is_opportunity"]),
    }


@app.get("/health")
def health():
    return {"status": "ok"}