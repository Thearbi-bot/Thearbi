import json
import logging
import requests
from datetime import datetime, timezone
from config import MAX_DAYS_TO_EXPIRY

log = logging.getLogger(__name__)
POLY_GAMMA = "https://gamma-api.polymarket.com"

def fetch_polymarket_markets() -> list[dict]:
    markets = []
    offset, limit = 0, 100

    while True:
        try:
            resp = requests.get(
                f"{POLY_GAMMA}/markets",
                params={"active": "true", "closed": "false", "limit": limit, "offset": offset},
                timeout=10,
            )
            resp.raise_for_status()
        except Exception as e:
            log.debug(f"Polymarket fetch stopped at offset {offset}: {e}")
            break

        batch = resp.json()
        if isinstance(batch, dict):
            batch = batch.get("data", [])
        if not batch:
            break

        for mkt in batch:
            normalised = _normalise(mkt)
            if normalised:
                markets.append(normalised)

        if len(batch) < limit:
            break
        offset += limit

        # Safety cap — don't fetch more than 5000 markets
        if offset >= 5000:
            break

    log.info(f"  Fetched {len(markets)} Polymarket markets")
    return markets


def _normalise(raw: dict) -> dict | None:
    try:
        outcomes = raw.get("outcomes", [])
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        if len(outcomes) != 2:
            return None

        end_str = raw.get("endDate") or raw.get("end_date_iso")
        if not end_str:
            return None
        close_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        days = (close_time - datetime.now(timezone.utc)).days
        if not (0 <= days <= MAX_DAYS_TO_EXPIRY):
            return None

        prices = raw.get("outcomePrices", "[]")
        if isinstance(prices, str):
            prices = json.loads(prices)
        if len(prices) < 2:
            return None

        yes_price = float(prices[0])
        if not (0 < yes_price < 1):
            return None

        return {
            "id": raw.get("conditionId") or raw.get("id", ""),
            "question": raw.get("question", ""),
            "yes_price": yes_price,
            "no_price": float(prices[1]),
            "volume": float(raw.get("volume", 0) or 0),
            "close_time": close_time,
            "source": "polymarket",
        }
    except Exception:
        return None