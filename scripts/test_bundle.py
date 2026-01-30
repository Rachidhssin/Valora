#!/usr/bin/env python3
"""Test Bundle Optimizer via Search Engine"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.search_engine import FinBundleEngine

async def test_bundle():
    print("\n🎮 Testing Bundle Optimization")
    print("=" * 60)
    
    engine = FinBundleEngine()
    
    # Test queries that should trigger deep path (bundle optimization)
    test_cases = [
        ("gaming setup", 1500),
        ("home office bundle", 1000),
        ("streaming kit", 800),
    ]
    
    for query, budget in test_cases:
        print(f"\n📝 Query: '{query}' | Budget: ${budget}")
        print("-" * 50)
        
        try:
            result = await engine.search(query, 'test_user', budget, skip_explanations=True)
            
            path = result.get('path', 'unknown')
            print(f"   Path: {path}")
            
            if path == 'deep':
                bundle = result.get('bundle', {})
                items = bundle.get('bundle', [])
                total = bundle.get('total_price', 0)
                method = bundle.get('method', 'unknown')
                status = bundle.get('status', 'unknown')
                
                print(f"   Status: {status} | Method: {method}")
                print(f"   Total: ${total:.2f} | Items: {len(items)}")
                print(f"\n   🛒 Bundle Items:")
                
                for i, item in enumerate(items, 1):
                    print(f"      {i}. {item.get('name', '')[:45]}")
                    print(f"         Category: {item.get('category', '')} | ${item.get('price', 0):.2f}")
            else:
                # Smart path - show top results
                results = result.get('results', [])
                print(f"   Results: {len(results)}")
                for i, r in enumerate(results[:5], 1):
                    print(f"      {i}. {r.get('name', '')[:45]} | ${r.get('price', 0):.2f}")
                    
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_bundle())
