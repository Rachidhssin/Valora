#!/usr/bin/env python3
"""Check Qdrant data"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval.qdrant_search import QdrantSearch

qdrant = QdrantSearch()

# Get sample products
print("Scrolling products...")
results = qdrant._client.scroll(
    collection_name='products_main',
    limit=50
)

print(f"\nFound {len(results[0])} products. Sample:\n")
for p in results[0][:30]:
    name = p.payload.get('name', '')[:55]
    cat = p.payload.get('category', '')[:15]
    price = p.payload.get('price', 0)
    print(f"  [{cat:<15}] ${price:>7.2f} | {name}")
