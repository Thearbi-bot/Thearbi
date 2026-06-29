import logging
import requests
from datetime import datetime, timezone
from config import MAX_DAYS_TO_EXPIRY

log = logging.getLogger(__name__)
KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Only series with single, unambiguous yes/no outcomes — no price/percentage
# thresholds that can be confused with each other.
GOOD_SERIES = [
    "KXSENATE", "KXHOUSE", "SENATE", "HOUSE", "PRES",
    "KXELONMARS", "KXNEWPOPE", "KXUKRWAR", "KXIRAN",
    "KXCHINA", "KXNATO", "KXTRUMP",
]

def fetch_kalshi_markets() -> list[dict]:
    markets = []

    for series in GOOD_SERIES:
        cursor = None
        while True:
            params = {"status": "open", "limit": 200, "series_ticker": series}
            if cursor:
                params["cursor"] = cursor

            try:
                resp = requests.get(
                    f"{KALSHI_BASE}/markets",
                    params=params,
                    timeout=10,
                )
                resp.raise_for_status()
            except Exception as e:
                log.debug(f"Error fetching series {series}: {e}")
                break

            data = resp.json()
            for mkt in data.get("markets", []):
                normalised = _normalise(mkt)
                if normalised:
                    markets.append(normalised)

            cursor = data.get("cursor")
            if not cursor:
                break

    log.info(f"  Fetched {len(markets)} Kalshi markets")
    return markets


def _normalise(mkt: dict) -> dict | None:
    try:
        if mkt.get("market_type") != "binary":
            return None
        if mkt.get("mve_collection_ticker"):
            return None

        close_time_str = mkt.get("close_time") or mkt.get("expiration_time")
        if not close_time_str:
            return None
        close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
        days = (close_time - datetime.now(timezone.utc)).days
        if not (0 <= days <= MAX_DAYS_TO_EXPIRY):
            return None

        yes_price = None
        for field in ["yes_ask_dollars", "last_price_dollars"]:
            val = mkt.get(field)
            if val and float(val) > 0.02:
                yes_price = float(val)
                break
        if yes_price is None or not (0 < yes_price < 1):
            return None

        question = mkt.get("title", "")
        # Skip any threshold-style questions that slipped through
        if re_has_threshold(question):
            return None

        return {
            "id": mkt["ticker"],
            "question": question,
            "yes_price": yes_price,
            "no_price": round(1 - yes_price, 4),
            "volume": float(mkt.get("volume_fp", 0) or 0),
            "close_time": close_time,
            "source": "kalshi",
        }
    except Exception:
        return None


def re_has_threshold(text: str) -> bool:
    """Filter out 'above X%' / 'above $X' style threshold questions —
    these need exact-pair matching that's too error-prone for fuzzy text."""
    import re
    return bool(re.search(r"(above|below|over|under)\s+[\d.]+", text.lower()))
