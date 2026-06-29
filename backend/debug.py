from manifold import fetch_manifold_markets

m = fetch_manifold_markets()
print(f"Got {len(m)} Manifold markets")
for mkt in m[:15]:
    print(f"  {mkt['yes_price']:.2f}  {mkt['question']}")