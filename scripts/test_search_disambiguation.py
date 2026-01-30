"""Test search with taxonomy disambiguation."""
import sys
sys.path.insert(0, '.')
import asyncio
from core.search_engine import FinBundleEngine

async def test_search():
    engine = FinBundleEngine()
    
    # Test 'gaming keyboard' - should return computer keyboards, not musical
    result = await engine.search(
        query='gaming keyboard',
        user_id='test_user',
        budget=200,
        skip_explanations=True
    )
    
    print('=' * 60)
    print('SEARCH: gaming keyboard')
    print('=' * 60)
    print(f"Path: {result['path']}")
    if 'disambiguation' in result:
        print(f"Disambiguation: {result['disambiguation']}")
    print(f"Results: {len(result['results'])}")
    for i, r in enumerate(result['results'][:5]):
        name = r['name'][:50]
        cat = r['category']
        print(f"  {i+1}. {name}... ({cat})")
    
    print()
    
    # Test 'screen' - should return monitors
    result2 = await engine.search(
        query='screen',
        user_id='test_user',
        budget=500,
        skip_explanations=True
    )
    
    print('=' * 60)
    print('SEARCH: screen')
    print('=' * 60)
    print(f"Path: {result2['path']}")
    if 'disambiguation' in result2:
        print(f"Disambiguation: {result2['disambiguation']}")
    print(f"Results: {len(result2['results'])}")
    for i, r in enumerate(result2['results'][:5]):
        name = r['name'][:50]
        cat = r['category']
        print(f"  {i+1}. {name}... ({cat})")
    
    print()
    
    # Test 'keyboard' - default to computer keyboards
    result3 = await engine.search(
        query='keyboard',
        user_id='test_user',
        budget=150,
        skip_explanations=True
    )
    
    print('=' * 60)
    print('SEARCH: keyboard')
    print('=' * 60)
    print(f"Path: {result3['path']}")
    if 'disambiguation' in result3:
        print(f"Disambiguation: {result3['disambiguation']}")
    print(f"Results: {len(result3['results'])}")
    for i, r in enumerate(result3['results'][:5]):
        name = r['name'][:50]
        cat = r['category']
        print(f"  {i+1}. {name}... ({cat})")

if __name__ == '__main__':
    asyncio.run(test_search())
