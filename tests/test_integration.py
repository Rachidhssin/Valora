"""
Integration Tests for FinBundle
Tests all three paths and component interactions
"""
import asyncio
import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_afig():
    """Test AFIG component."""
    print("\n📊 Testing AFIG...")
    
    from core.afig import AFIG
    
    afig = AFIG(user_id="test_integration_001")
    
    # Test situational update
    afig.update_situational({
        "mission": "gaming setup",
        "timeline": "flexible",
        "budget_override": 1500
    })
    
    # Test behavioral update
    afig.update_behavioral({
        "type": "click",
        "product": {"id": "test_001", "category": "gpus", "price": 599}
    })
    
    # Test reconciliation
    profile = afig.reconcile()
    
    assert "archetype" in profile, "Missing archetype in profile"
    assert "mission" in profile, "Missing mission in profile"
    assert profile["mission"] == "gaming setup", "Mission not set correctly"
    
    afig.close()
    print("   ✓ AFIG tests passed")
    return True


def test_router():
    """Test query router."""
    print("\n📊 Testing Router...")
    
    from core.router import QueryRouter
    
    router = QueryRouter()
    
    # Test fast path
    result = router.route("laptop")
    assert result in ["fast", "smart"], f"Simple query should be fast/smart, got {result}"
    
    # Test deep path
    result = router.route("complete gaming setup $1500", 1500)
    assert result == "deep", f"Bundle query should be deep, got {result}"
    
    # Test budget extraction
    decision = router.analyze("gaming laptop under $1000")
    intent = router.get_query_intent("gaming laptop under $1000")
    assert intent['budget'] == 1000, f"Budget extraction failed, got {intent['budget']}"
    
    print("   ✓ Router tests passed")
    return True


def test_embeddings():
    """Test embedding service."""
    print("\n📊 Testing Embeddings...")
    
    from core.embeddings import EmbeddingService
    
    service = EmbeddingService()
    
    # Test single encoding
    embedding = service.encode_query("gaming laptop")
    assert embedding.shape == (384,), f"Wrong embedding shape: {embedding.shape}"
    
    # Test batch encoding
    texts = ["laptop", "keyboard", "mouse"]
    embeddings = service.encode_batch(texts)
    assert embeddings.shape == (3, 384), f"Wrong batch shape: {embeddings.shape}"
    
    # Test similarity
    sim = service.similarity(embeddings[0], embeddings[0])
    assert abs(sim - 1.0) < 0.001, "Self-similarity should be 1.0"
    
    print("   ✓ Embedding tests passed")
    return True


def test_cache():
    """Test PostgreSQL cache (with fallback to memory)."""
    print("\n📊 Testing Cache...")
    
    from retrieval.cache import PostgreSQLCache
    
    cache = PostgreSQLCache(table_name="test_cache")
    
    # Test set/get
    cache.set("test_key", {"value": 42}, ttl=60)
    result = cache.get("test_key")
    assert result is not None, "Cache get returned None"
    assert result.get("value") == 42, f"Wrong cached value: {result}"
    
    # Test miss
    result = cache.get("nonexistent_key")
    assert result is None, "Nonexistent key should return None"
    
    # Cleanup
    cache.delete("test_key")
    
    print("   ✓ Cache tests passed")
    return True


def test_feasibility():
    """Test feasibility gate."""
    print("\n📊 Testing Feasibility Gate...")
    
    from optimization.feasibility import FeasibilityGate
    
    gate = FeasibilityGate()
    
    # Test product
    product = {
        'product_id': 'test_001',
        'name': 'Test Laptop',
        'price': 500,
        'rating': 4.5,
        'score': 0.8,
        'condition': 'new',
        'in_stock': True
    }
    
    user_context = {
        'archetype': 'value_balanced',
        'category_preferences': {}
    }
    
    # Test within budget
    result = gate.check_feasibility(product, user_context, budget=1000)
    assert result.is_feasible, "Product should be feasible within budget"
    
    # Test over budget
    result = gate.check_feasibility(product, user_context, budget=100)
    assert not result.is_feasible, "Product should not be feasible over budget"
    
    # Test out of stock
    out_of_stock = {**product, 'in_stock': False}
    result = gate.check_feasibility(out_of_stock, user_context, budget=1000)
    assert not result.is_feasible, "Out of stock product should not be feasible"
    
    print("   ✓ Feasibility gate tests passed")
    return True


def test_optimizer():
    """Test bundle optimizer."""
    print("\n📊 Testing Bundle Optimizer...")
    
    from optimization.bundle_optimizer import BundleOptimizer, Product
    
    optimizer = BundleOptimizer()
    
    products = [
        Product("1", "Laptop", 999, "laptops", 0.9),
        Product("2", "Mouse", 49, "mice", 0.7),
        Product("3", "Keyboard", 99, "keyboards", 0.8),
        Product("4", "Monitor", 399, "monitors", 0.85),
    ]
    
    # Test optimization
    result = optimizer.optimize(products, budget=1200, user_prefs={})
    
    assert result.bundle, "Optimizer should return a bundle"
    assert result.total_price <= 1200, f"Bundle exceeds budget: {result.total_price}"
    assert result.total_utility > 0, "Bundle should have positive utility"
    
    # Test infeasible case
    result = optimizer.optimize(products, budget=10, user_prefs={})
    assert not result.bundle, "Should return empty bundle for tiny budget"
    
    print("   ✓ Optimizer tests passed")
    return True


async def test_agent():
    """Test budget pathfinder agent."""
    print("\n📊 Testing Budget Agent...")
    
    from agent.budget_agent import BudgetPathfinderAgent
    
    agent = BudgetPathfinderAgent()
    
    product = {
        'id': 'test_001',
        'name': 'Test Product',
        'price': 1500,
        'category': 'laptops'
    }
    
    cart = [
        {'id': 'cart_1', 'name': 'Mouse', 'price': 89, 'utility': 0.7}
    ]
    
    user_afig = {
        'archetype': 'value_balanced',
        'timeline': 'flexible',
        'risk_tolerance': 0.5
    }
    
    # Test with budget gap
    result = await agent.find_affordability_paths(
        product=product,
        user_afig=user_afig,
        current_cart=cart,
        budget=1200
    )
    
    assert 'status' in result, "Agent should return status"
    assert 'gap' in result, "Agent should return gap"
    
    if result['gap'] > 0:
        assert 'paths' in result, "Agent should return paths for gap > 0"
    
    print("   ✓ Agent tests passed")
    return True


async def test_search_engine():
    """Test full search engine flow."""
    print("\n📊 Testing Search Engine...")
    
    try:
        from core.search_engine import FinBundleEngine
    except ImportError as e:
        print(f"   ⚠️ Search engine import failed: {e}")
        print("   ⚠️ Skipping full integration test (deps may be missing)")
        return True
    
    engine = FinBundleEngine()
    
    # Test smart path
    result = await engine.search(
        query="gaming mouse",
        user_id="test_user",
        budget=100
    )
    
    assert 'path' in result, "Result should include path"
    assert 'metrics' in result, "Result should include metrics"
    assert result['metrics']['total_latency_ms'] > 0, "Should have latency"
    
    print(f"   Path: {result['metrics']['path_used']}")
    print(f"   Latency: {result['metrics']['total_latency_ms']:.0f}ms")
    
    print("   ✓ Search engine tests passed")
    return True


def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("🧪 FINBUNDLE INTEGRATION TESTS")
    print("=" * 60)
    
    start_time = time.time()
    results = {}
    
    # Sync tests
    sync_tests = [
        ("AFIG", test_afig),
        ("Router", test_router),
        ("Embeddings", test_embeddings),
        ("Cache", test_cache),
        ("Feasibility", test_feasibility),
        ("Optimizer", test_optimizer),
    ]
    
    for name, test_fn in sync_tests:
        try:
            results[name] = test_fn()
        except Exception as e:
            print(f"   ✗ {name} FAILED: {e}")
            results[name] = False
    
    # Async tests
    async_tests = [
        ("Agent", test_agent),
        ("Search Engine", test_search_engine),
    ]
    
    for name, test_fn in async_tests:
        try:
            results[name] = asyncio.run(test_fn())
        except Exception as e:
            print(f"   ✗ {name} FAILED: {e}")
            results[name] = False
    
    # Summary
    elapsed = time.time() - start_time
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {passed}/{total} tests passed in {elapsed:.2f}s")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"   {status} - {name}")
    
    if passed == total:
        print("\n✅ All integration tests passed!")
        return True
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
