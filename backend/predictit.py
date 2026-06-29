import logging
import requests

log = logging.getLogger(__name__)

PREDICTIT_URL = "https://www.predictit.org/api/marketdata/all/"


def fetch_predictit_markets() -> list[dict]:
    """
    Fetch all PredictIt markets and flatten contracts into individual markets.
    Each contract becomes its own market with a combined question.
    """
    try:
        resp = requests.get(PREDICTIT_URL, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        log.error(f"PredictIt fetch error: {e}")
        return []

    markets = []
    for market in resp.json().get("markets", []):
        if market.get("status") != "Open":
            continue

        market_name = market.get("name", "")
        contracts = market.get("contracts", [])

        for contract in contracts:
            if contract.get("status") != "Open":
                continue

            yes_price = contract.get("bestBuyYesCost")
            if yes_price is None or not (0 < yes_price < 1):
                continue

            contract_name = contract.get("name", "")

            # If only one contract, use market name as question
            # If multiple contracts, combine market + contract name
            if len(contracts) == 1:
                question = market_name
            else:
                question = f"{market_name} — {contract_name}"

            markets.append({
                "id": f"pi_{contract['id']}",
                "question": question,
                "yes_price": yes_price,
                "no_price": round(1 - yes_price, 4),
                "volume": 0,
                "close_time": None,
                "source": "predictit",
            })

    log.info(f"  Fetched {len(markets)} PredictIt markets")
    return markets