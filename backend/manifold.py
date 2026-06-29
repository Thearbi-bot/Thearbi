import logging
import requests

log = logging.getLogger(__name__)

MANIFOLD_SEARCH_URL = "https://api.manifold.markets/v0/search-markets"

# Search terms to find relevant political/world markets
SEARCH_TERMS = [
    "election", "senate", "governor", "president", "Fed",
    "interest rate", "Trump", "midterm", "primary", "Bitcoin",
    "Ethereum", "war", "Ukraine", "China", "NATO",
]


def fetch_manifold_markets() -> list[dict]:
    markets = []
    seen_ids = set()

    for term in SEARCH_TERMS:
        try:
            resp = requests.get(
                MANIFOLD_SEARCH_URL,
                params={"term": term, "limit": 50},
                timeout=10,
            )
            resp.raise_for_status()
        except Exception as e:
            log.debug(f"Manifold search error for '{term}': {e}")
            continue

        for mkt in resp.json():
            if mkt.get("outcomeType") != "BINARY":
                continue
            if mkt.get("isResolved"):
                continue

            mkt_id = mkt.get("id")
            if mkt_id in seen_ids:
                continue
            seen_ids.add(mkt_id)

            prob = mkt.get("probability")
            if prob is None or not (0 < prob < 1):
                continue

            markets.append({
                "id": f"mf_{mkt_id}",
                "question": mkt.get("question", ""),
                "yes_price": prob,
                "no_price": round(1 - prob, 4),
                "volume": mkt.get("volume24Hours", 0),
                "close_time": None,
                "source": "manifold",
            })

    log.info(f"  Fetched {len(markets)} Manifold markets")
    return markets