"""
Tests for Three-Path Architecture (Router & Engine)
"""
import pytest
import asyncio
from core.router import QueryRouter, RoutePath
from core.search_engine import FinBundleEngine

# --- Router Tests ---

def test_router_complexity_fast():
    router = QueryRouter()
    # "laptop" -> simple, length 1, no budget -> low complexity
    query = "laptop"
    complexity = router.estimate_complexity(query)
    assert complexity < 0.3
    decision = router.analyze(query)
    assert decision.path == RoutePath.FAST

def test_router_complexity_smart():
    router = QueryRouter()
    # "gaming mouse under $50" -> medium length, budget -> smart path
    query = "gaming mouse under $50"
    complexity = router.estimate_complexity(query, budget=50)
    assert 0.3 <= complexity < 0.7
    decision = router.analyze(query, budget=50)
    assert decision.path == RoutePath.SMART

def test_router_complexity_deep():
    router = QueryRouter()
    # "complete gaming setup with monitor and chair" -> high complexity (keywords 'complete', 'setup', 'with', 'and')
    query = "complete gaming setup with monitor and chair"
    complexity = router.estimate_complexity(query, budget=2000)
    assert complexity >= 0.7
    decision = router.analyze(query, budget=2000)
    assert decision.path == RoutePath.DEEP

def test_router_cache_key():
    router = QueryRouter()
    k1 = router.get_cache_key("Laptop", 1000, "student")
    k2 = router.get_cache_key("laptop ", 1040, "student") # Should match (trim, lower, budget bucket)
    assert k1 == k2

# --- Engine Tests ---

def test_fast_path_execution():
    async def _test():
        engine = FinBundleEngine()
        # Preset cache or rely on popular fallback
        result = await engine.search("laptop", "user_test", 1000)
        assert result['path'] == 'fast'
        assert result['metrics']['total_latency_ms'] < 200  # Target (relaxed for dev env)
        assert len(result['results']) > 0
    
    asyncio.run(_test())

def test_smart_path_execution():
    async def _test():
        engine = FinBundleEngine()
        # Mocking Qdrant availability check or ensuring it handles offline gracefully
        # Assuming Qdrant is available or returns empty list safely
        try:
            # "gaming mouse with high dpi" -> length 5 (score 0.3) -> Smart Path
            result = await engine.search("gaming mouse with high dpi", "user_test", 100)
            assert result['path'] == 'smart'
            # It might return empty results if Qdrant is empty/offline, but path should be correct
            assert 'results' in result
        except Exception as e:
            pytest.fail(f"Smart path failed: {e}")

    asyncio.run(_test())

def test_deep_path_execution_skip_explanations():
    async def _test():
        engine = FinBundleEngine()
        # Force deep path via query
        query = "complete gaming setup bundle"
        result = await engine.search(query, "user_test", 2000, skip_explanations=True)
        
        assert result['path'] == 'deep'
        assert 'bundle' in result
        # Explanations should be empty/skipped
        assert len(result.get('explanations', [])) == 0

    asyncio.run(_test())

def test_timeout_fallback():
    async def _test():
        # This is harder to test without mocking sleep, but we can verify the structure exists
        engine = FinBundleEngine()
        # A normal query shouldn't timeout unless we force it.
        # Just verify it runs successfully.
        result = await engine.search("laptop", "user_test", 1000)
        assert result is not None

    asyncio.run(_test())
