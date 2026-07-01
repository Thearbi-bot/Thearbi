import requests

KALSHI_BASE = 'https://api.elections.kalshi.com/trade-api/v2'
POLY_GAMMA = 'https://gamma-api.polymarket.com'

print("=== KALSHI WTI open markets (all dates) ===")
resp = requests.get(f'{KALSHI_BASE}/markets', params={'status':'open','limit':50,'series_ticker':'KXWTI'})
dates = set()
for m in resp.json().get('markets',[]):
    close = m.get('close_time','')
    dates.add(close[:16])
for d in sorted(dates):
    print(' ', d)

print("\n=== POLYMARKET WTI active events (all dates) ===")
resp2 = requests.get(f'{POLY_GAMMA}/events', params={'series_slug':'wti-daily-close-uo','limit':10,'active':'true','closed':'false'})
for e in resp2.json():
    print(' ', e.get('slug'), '| end:', e.get('endDate'), '| liquidity:', e.get('liquidity'))
