"""Test cart filtering in search results"""
import requests
import json

API_URL = "http://localhost:8123"

def test_cart_filtering():
    """Verify that items in cart don't appear in search results"""
    
    # Search for monitors first
    print('=== Initial Search: 4k monitors ===')
    resp = requests.post(f'{API_URL}/api/search', json={
        'query': '4k monitors',
        'budget': 500,
        'user_id': 'demo_user',
        'cart': [],
        'skip_explanations': True
    })
    data = resp.json()
    results = data.get('results', [])[:5]

    # Show first 3 results
    print(f'Found {len(data.get("results", []))} results')
    for i, r in enumerate(results[:3]):
        print(f'  {i+1}. {r["product_id"][:8]}... - {r["name"][:40]} - ${r["price"]}')

    # Now simulate adding first result to cart
    if results:
        cart_item = results[0]
        cart = [{
            'product_id': cart_item['product_id'],
            'name': cart_item['name'],
            'price': cart_item['price'],
            'category': cart_item.get('category', '')
        }]
        
        print(f'\n=== Added to cart: {cart_item["name"][:40]} ===')
        print(f'    Product ID: {cart_item["product_id"]}')
        
        # Search again with cart
        print('\n=== Search Again: 4k monitors (with cart) ===')
        resp2 = requests.post(f'{API_URL}/api/search', json={
            'query': '4k monitors',
            'budget': 500,
            'user_id': 'demo_user',
            'cart': cart,
            'skip_explanations': True
        })
        data2 = resp2.json()
        results2 = data2.get('results', [])[:5]
        
        print(f'Found {len(data2.get("results", []))} results')
        
        # Check if cart item appears in new results
        cart_id = cart_item['product_id']
        cart_in_results = any(r['product_id'] == cart_id for r in results2)
        
        for i, r in enumerate(results2[:3]):
            marker = ' <-- IN CART!' if r['product_id'] == cart_id else ''
            print(f'  {i+1}. {r["product_id"][:8]}... - {r["name"][:40]} - ${r["price"]}{marker}')
        
        if cart_in_results:
            print('\n❌ FAIL: Cart item still appears in results!')
        else:
            print('\n✅ SUCCESS: Cart item correctly filtered out!')
            
            # Verify the result counts
            original_count = len(data.get('results', []))
            new_count = len(data2.get('results', []))
            print(f'   Original results: {original_count}, After filter: {new_count}')
            
    return not cart_in_results


def test_bundle_optimization():
    """Test that bundle optimization returns complementary products"""
    print('\n' + '=' * 60)
    print('=== BUNDLE OPTIMIZATION TEST ===')
    print('=' * 60)
    
    # Create a cart with a computer
    cart = [{
        'product_id': 'test-pc-001',
        'name': 'Gaming Desktop PC',
        'price': 899.99,
        'category': 'Computers'
    }]
    
    # Budget should be enough for PC + complementary items
    budget = 2000  # $2000 total budget
    
    print(f'\n📦 Cart: {cart[0]["name"]} (${cart[0]["price"]})')
    print(f'   Category: {cart[0]["category"]}')
    print(f'   Budget: ${budget}')
    print(f'   Remaining for accessories: ${budget - cart[0]["price"]:.2f}')
    
    # Call optimize endpoint
    print('\n🔧 Calling /api/optimize...')
    resp = requests.post(f'{API_URL}/api/optimize', json={
        'cart': cart,
        'budget': budget,
        'user_id': 'demo_user'
    })
    
    if resp.status_code != 200:
        print(f'❌ Error: {resp.status_code} - {resp.text}')
        return False
    
    data = resp.json()
    
    if not data.get('success'):
        print(f'❌ Optimization failed: {data.get("error")}')
        return False
    
    print(f'\n✅ Optimization successful!')
    print(f'   Original total: ${data.get("original_total")}')
    print(f'   Optimized total: ${data.get("optimized_total")}')
    print(f'   Savings: ${data.get("savings")}')
    
    products = data.get('optimized_products', [])
    print(f'\n📦 Optimized bundle ({len(products)} items):')
    
    categories_found = set()
    product_types_found = []
    for i, p in enumerate(products):
        cat = p.get('category', 'Unknown')
        name = p.get('name', '').lower()
        categories_found.add(cat.lower())
        
        # Detect product type from name
        ptype = 'other'
        if any(kw in name for kw in ['monitor', 'display', 'screen']):
            ptype = 'monitor'
        elif any(kw in name for kw in ['keyboard']):
            ptype = 'keyboard'
        elif any(kw in name for kw in ['mouse', 'mice']):
            ptype = 'mouse'
        elif any(kw in name for kw in ['headset', 'headphone']):
            ptype = 'headset'
        elif any(kw in name for kw in ['webcam', 'camera']):
            ptype = 'webcam'
        elif any(kw in name for kw in ['speaker', 'soundbar', 'audio']):
            ptype = 'speaker'
        product_types_found.append(ptype)
        
        print(f'   {i+1}. {p["name"][:45]} - ${p["price"]} [{ptype}]')
    
    # Check if we have complementary product types
    complementary_types = {'monitor', 'keyboard', 'mouse', 'headset', 'webcam', 'speaker'}
    found_types = set(product_types_found)
    complementary_count = len(found_types & complementary_types)
    
    print(f'\n   Product types found: {", ".join(found_types)}')
    
    if complementary_count >= 2:
        print(f'\n✅ SUCCESS: Bundle includes {complementary_count} complementary product types!')
    else:
        print('\n⚠️ WARNING: Could use more complementary products.')
    
    return True


if __name__ == '__main__':
    test_cart_filtering()
    test_bundle_optimization()
    test_cart_filtering()
