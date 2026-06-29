from dotenv import load_dotenv
load_dotenv()

import time
import logging
from dataclasses import dataclass
from datetime import datetime
import requests

from config import KALSHI_FEE, POLYMARKET_FEE, MIN_PROFIT_THRESHOLD, POLL_INTERVAL_SECONDS
from kalshi import fetch_kalshi_markets
from polymarket import fetch_polymarket_markets
from matcher import match_markets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


@dataclass
class ArbOpportunity:
    question: str
    kalshi_price: float
    poly_price: float
    gap: float
    profit_after_fees: float
    direction: str
    found_at: datetime


def calculate_profit(kalshi_price, poly_price):
    if kalshi_price < poly_price:
        combined_cost = kalshi_price + (1 - poly_price)
        gap = 1 - combined_cost
        direction = "BUY YES on Kalshi / BUY NO on Polymarket"
    else:
        combined_cost = poly_price + (1 - kalshi_price)
        gap = 1 - combined_cost
        direction = "BUY YES on Polymarket / BUY NO on Kalshi"
    profit_after_fees = gap - KALSHI_FEE - POLYMARKET_FEE
    return gap, profit_after_fees, direction


def scan_once():
    log.info("Fetching Kalshi markets...")
    kalshi = fetch_kalshi_markets()
    log.info(f"  Got {len(kalshi)} Kalshi markets")

    log.info("Fetching Polymarket markets...")
    poly = fetch_polymarket_markets()
    log.info(f"  Got {len(poly)} Polymarket markets")

    log.info("Matching markets...")
    matched = match_markets(kalshi, poly)
    log.info(f"  Matched {len(matched)} pairs")

    opportunities = []
    for k_mkt, p_mkt, score in matched:
        gap, profit, direction = calculate_profit(
            k_mkt["yes_price"], p_mkt["yes_price"]
        )

        if profit >= MIN_PROFIT_THRESHOLD:
            opp = ArbOpportunity(
                question=k_mkt["question"],
                kalshi_price=k_mkt["yes_price"],
                poly_price=p_mkt["yes_price"],
                gap=round(gap, 4),
                profit_after_fees=round(profit, 4),
                direction=direction,
                found_at=datetime.utcnow(),
            )
            opportunities.append(opp)
            log.warning(
                f"\n  *** OPPORTUNITY ***\n"
                f"  Question  : {opp.question}\n"
                f"  Match score: {score:.2f}\n"
                f"  Kalshi    : {opp.kalshi_price*100:.1f}c YES\n"
                f"  Polymarket: {opp.poly_price*100:.1f}c YES\n"
                f"  Gap       : {opp.gap*100:.2f}%\n"
                f"  Net profit: {opp.profit_after_fees*100:.2f}% after fees\n"
                f"  Action    : {opp.direction}\n"
            )

    return opportunities


def run():
    log.info("=== Arbitrage Scanner Started ===")
    log.info(f"Min profit threshold: {MIN_PROFIT_THRESHOLD*100:.1f}%")
    log.info(f"Poll interval: {POLL_INTERVAL_SECONDS}s")

    while True:
        try:
            opps = scan_once()
            if opps:
                log.info(f"FOUND {len(opps)} opportunity(s) this scan")
            else:
                log.info("No opportunities this scan")
        except requests.exceptions.RequestException as e:
            log.error(f"Network error: {e}")
        except Exception as e:
            log.exception(f"Unexpected error: {e}")

        log.info(f"Sleeping {POLL_INTERVAL_SECONDS}s...\n")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()