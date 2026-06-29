import re
import logging
from difflib import SequenceMatcher
from config import MATCH_SIMILARITY_THRESHOLD

log = logging.getLogger(__name__)

_STOPWORDS = {
    "will", "the", "a", "an", "be", "is", "are", "in", "of", "to",
    "and", "or", "by", "at", "on", "for", "with", "did", "do", "does",
    "has", "have", "had", "this", "that", "it", "its", "win", "lose",
    "get", "go", "make", "take", "above", "below", "over", "under",
    "settle", "settlement", "price", "final", "trading", "day",
}

TOPIC_TAGS = {
    "oil":      ["oil", "wti", "crude", "bbl", "barrel"],
    "fed":      ["fed", "federal", "funds", "rate", "fomc", "interest", "bps"],
    "cpi":      ["cpi", "inflation", "consumer", "price", "index"],
    "gdp":      ["gdp", "growth", "economy", "economic"],
    "bitcoin":  ["bitcoin", "btc"],
    "ethereum": ["ethereum", "eth"],
    "elon":     ["elon", "musk", "spacex", "tesla"],
    "pope":     ["pope", "papal", "vatican", "catholic"],
}

THRESHOLD_TOPICS = {"oil", "bitcoin", "ethereum", "fed", "cpi", "gdp"}

TOLERANCE_BY_TOPIC = {
    "oil": 0.51, "bitcoin": 500, "ethereum": 25,
    "fed": 0.13, "cpi": 0.06, "gdp": 0.06,
}
DEFAULT_TOLERANCE = 0.51

MONTHS = (
    "january|february|march|april|may|june|july|august|"
    "september|october|november|december|"
    "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)


def _tokens(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    return [t for t in text.split() if t and t not in _STOPWORDS and len(t) > 1]


def _norm(text):
    return " ".join(_tokens(text))


def _sorted_norm(text):
    return " ".join(sorted(_tokens(text)))


def _keyword_overlap(a, b):
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    shorter = sa if len(sa) <= len(sb) else sb
    longer  = sa if len(sa) > len(sb) else sb
    return len(shorter & longer) / len(shorter)


def _get_topic(text):
    text_lower = text.lower()
    for topic, keywords in TOPIC_TAGS.items():
        if any(k in text_lower for k in keywords):
            return topic
    return None


def _is_range_market(text):
    return bool(re.search(r"\d+\s*[-–]\s*\$?\d+", text))


def _extract_threshold_numbers(text):
    nums = re.findall(r"-?\d+\.?\d*", text)
    result = []
    for n in nums:
        f = float(n)
        if f in (2024, 2025, 2026, 2027, 2028):
            continue
        result.append(f)
    return result


def _extract_month(text):
    """Find the first month mentioned — used to check both questions
    refer to the same date/meeting/period."""
    match = re.search(MONTHS, text.lower())
    return match.group(0)[:3] if match else None


def _closest_threshold_match(a, b, topic):
    """
    Find the single closest pair of numbers between two questions.
    Returns True only if that closest pair is within tolerance.
    This avoids accidentally matching on a SECOND number (like a date)
    when the actual threshold numbers are far apart.
    """
    tolerance = TOLERANCE_BY_TOPIC.get(topic, DEFAULT_TOLERANCE)
    nums_a = _extract_threshold_numbers(a)
    nums_b = _extract_threshold_numbers(b)
    if not nums_a or not nums_b:
        return None

    best_diff = min(abs(na - nb) for na in nums_a for nb in nums_b)
    return best_diff <= tolerance


def similarity(a, b):
    tok_a = _tokens(a)
    tok_b = _tokens(b)

    kw = _keyword_overlap(tok_a, tok_b)
    if kw < 0.2:
        return kw

    topic_a = _get_topic(a)
    topic_b = _get_topic(b)

    if topic_a and topic_b and topic_a != topic_b:
        return 0.0

    if _is_range_market(a) != _is_range_market(b):
        return 0.0

    topic = topic_a or topic_b
    if topic in THRESHOLD_TOPICS:
        # For date-anchored topics (fed/cpi/gdp), months must match too
        if topic in ("fed", "cpi", "gdp"):
            month_a = _extract_month(a)
            month_b = _extract_month(b)
            if month_a and month_b and month_a != month_b:
                return 0.0

        match = _closest_threshold_match(a, b, topic)
        if match is False or match is None:
            return 0.0

    topic_bonus = 0.2 if topic_a and topic_a == topic_b else 0.0

    s1 = SequenceMatcher(None, _norm(a), _norm(b)).ratio()
    s2 = SequenceMatcher(None, _sorted_norm(a), _sorted_norm(b)).ratio()
    base = max(s1, s2, kw)

    return min(base + topic_bonus, 1.0)


def match_markets(kalshi_markets, poly_markets):
    if not kalshi_markets or not poly_markets:
        return []

    poly_index = [(mkt, _tokens(mkt["question"])) for mkt in poly_markets]
    matched = []
    used_poly_ids = set()

    for k in kalshi_markets:
        k_tokens = _tokens(k["question"])
        if not k_tokens:
            continue

        best_score = 0.0
        best_poly = None

        for p_mkt, p_tokens in poly_index:
            if p_mkt["id"] in used_poly_ids:
                continue
            if _keyword_overlap(k_tokens, p_tokens) < 0.2:
                continue
            score = similarity(k["question"], p_mkt["question"])
            if score > best_score:
                best_score = score
                best_poly = p_mkt

        if best_poly and best_score >= MATCH_SIMILARITY_THRESHOLD:
            log.debug(f"Match {best_score:.2f}: {k['question'][:50]} <-> {best_poly['question'][:50]}")
            matched.append((k, best_poly, best_score))
            used_poly_ids.add(best_poly["id"])

    log.info(f"  Matched {len(matched)} pairs from {len(kalshi_markets)} Kalshi and {len(poly_markets)} Polymarket markets")
    return matched