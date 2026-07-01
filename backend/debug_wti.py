import requests, re, json

POLY_GAMMA = 'https://gamma-api.polymarket.com'
KALSHI_BASE = 'https://api.elections.kalshi.com/trade-api/v2'

print("=== POLYMARKET JUNE 30 MARKETS ===")
resp = requests.get(f'{POLY_GAMMA}/events', params={'slug': 'wti-closes-above-on-june-30-2026'}, timeout=10)
data = resp.json()
if data:
    for m in data[0].get('markets', []):
        bid = float(m.get('bestBid') or 0)
        ask = float(m.get('bestAsk') or 0)
        spread = ask - bid
        match = re.search(r'above \$(\d+)', m.get('question','').lower())
        thresh = match.group(1) if match else '?'
        end = data[0].get('endDate','')[:10]
        print(f'  date={end} above=${thresh}: bid={bid} ask={ask} spread={spread:.2f}')

print("\n=== KALSHI JUNE 30 MARKETS ===")
resp2 = requests.get(f'{KALSHI_BASE}/markets', params={'status':'open','limit':20,'series_ticker':'KXWTI'})
for m in resp2.json().get('markets',[]):
    close = m.get('close_time','')[:10]
    if '2026-06-30' in close:
        title = m.get('title','')
        match = re.search(r'above (\d+\.\d+)', title.lower())
        thresh = match.group(1) if match else '?'
        print(f'  date={close} above=${thresh} ticker={m.get("ticker")}')