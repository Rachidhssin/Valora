#!/usr/bin/env python3
"""Quick search test"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.search_engine import FinBundleEngine

async def test_search(query):
    print(f"\n🔍 Testing: '{query}'")
    print("-" * 60)
    
    engine = FinBundleEngine()
    result = await engine.search(query, 'test_user', 5000)
    
    products = result.get('results', [])
    print(f"Found {len(products)} results:\n")
    
    for i, p in enumerate(products[:15], 1):
        name = p.get('name', '')[:50]
        category = p.get('category', '')[:20]
        price = p.get('price', 0)
        score = p.get('score', 0)
        print(f"{i:2}. [{score:.0%}] ${price:>7.2f} | {category:<20} | {name}")

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "4k monitors"
    asyncio.run(test_search(query))
