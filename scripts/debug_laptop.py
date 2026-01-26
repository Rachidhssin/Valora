"""Debug laptop search issue"""
import sys
import asyncio
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.search_engine import FinBundleEngine

# Test search
engine = FinBundleEngine()
result = asyncio.run(engine.search('gaming laptop', 'test', 2000))

print(f"Path: {result.get('path')}")
print(f"Results count: {len(result.get('results', []))}")

results = result.get('results', [])
print("\nFirst 3 results (full dict):")
for r in results[:3]:
    print(f"  product_id: {r.get('product_id')}")
    print(f"  name: {r.get('name')}")
    print(f"  price: {r.get('price')}")
    print(f"  ---")
