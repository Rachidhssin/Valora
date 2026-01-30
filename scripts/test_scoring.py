"""Test scoring calibration."""
import sys
sys.path.insert(0, '.')
import asyncio
from core.search_engine import FinBundleEngine

async def test():
    engine = FinBundleEngine()
    result = await engine.search('4K monitors', 'test_user', 800, skip_explanations=True)
    
    print('SEARCH: 4K monitors')
    print('='*70)
    for i, r in enumerate(result['results'][:5]):
        score = r.get('score', 0)
        scoring = r.get('_scoring', {})
        semantic = scoring.get('semantic_score', 0)
        price = scoring.get('price_score', 0)
        quality = scoring.get('quality_score', 0)
        print(f"{i+1}. Final: {score*100:.1f}% | Semantic: {semantic*100:.1f}% | Price: {price*100:.1f}% | Quality: {quality*100:.1f}%")
        print(f"   {r['name'][:60]}")
        print(f"   ${r['price']}")
        print()

if __name__ == '__main__':
    asyncio.run(test())
