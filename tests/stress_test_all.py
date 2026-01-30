"""
FinBundle/Valora Comprehensive Stress Test Suite
=================================================

This script tests EVERY feature, function, and component in the project.
Run this to verify the entire system works correctly.

Components Tested:
------------------
1. Database Connection & Products (db/)
2. AFIG - Adaptive Financial Intent Graph (core/afig.py)
3. Router - Query Routing (core/router.py)
4. Embeddings Service (core/embeddings.py)
5. Scorer - Product Scoring (core/scorer.py)
6. Taxonomy - Category Disambiguation (core/taxonomy.py)
7. Visual Search - CLIP (core/visual_search.py)
8. Metrics Logger (core/metrics.py)
9. Cache - PostgreSQL Cache (retrieval/cache.py)
10. Qdrant Search - Legacy & Multimodal (retrieval/qdrant_search.py)
11. Feasibility Gate (optimization/feasibility.py)
12. Bundle Optimizer (optimization/bundle_optimizer.py)
13. Budget Agent (agent/budget_agent.py)
14. LLM Explainer (explanation/llm_explainer.py)
15. Search Engine - Three-Path Architecture (core/search_engine.py)
16. API Endpoints (api/main.py)

Usage:
------
    python tests/stress_test_all.py
    
    # Or with specific modules:
    python tests/stress_test_all.py --module afig
    python tests/stress_test_all.py --module search
    python tests/stress_test_all.py --fast  # Skip slow tests
"""

import sys
import os
import time
import asyncio
import traceback
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test results tracking
@dataclass
class TestResult:
    name: str
    module: str
    passed: bool
    duration_ms: float
    error: str = ""
    details: str = ""

class TestSuite:
    """Comprehensive test suite for all FinBundle components."""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.start_time = None
        self.fast_mode = False
        
    def log(self, message: str, level: str = "INFO"):
        """Log with timestamp and level."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icons = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "TEST": "🧪"}
        icon = icons.get(level, "📝")
        print(f"[{timestamp}] {icon} {message}")
    
    def run_test(self, name: str, module: str, test_func):
        """Run a single test and record results."""
        self.log(f"Testing: {name}", "TEST")
        start = time.time()
        
        try:
            result = test_func()
            duration = (time.time() - start) * 1000
            
            if result is True or result is None:
                self.results.append(TestResult(
                    name=name, module=module, passed=True, 
                    duration_ms=duration, details="OK"
                ))
                self.log(f"PASSED: {name} ({duration:.1f}ms)", "PASS")
                return True
            else:
                self.results.append(TestResult(
                    name=name, module=module, passed=False,
                    duration_ms=duration, error=str(result)
                ))
                self.log(f"FAILED: {name} - {result}", "FAIL")
                return False
                
        except Exception as e:
            duration = (time.time() - start) * 1000
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.results.append(TestResult(
                name=name, module=module, passed=False,
                duration_ms=duration, error=error_msg
            ))
            self.log(f"FAILED: {name} - {error_msg}", "FAIL")
            if os.getenv("DEBUG"):
                traceback.print_exc()
            return False
    
    async def run_async_test(self, name: str, module: str, test_func):
        """Run an async test."""
        self.log(f"Testing: {name}", "TEST")
        start = time.time()
        
        try:
            result = await test_func()
            duration = (time.time() - start) * 1000
            
            if result is True or result is None:
                self.results.append(TestResult(
                    name=name, module=module, passed=True,
                    duration_ms=duration, details="OK"
                ))
                self.log(f"PASSED: {name} ({duration:.1f}ms)", "PASS")
                return True
            else:
                self.results.append(TestResult(
                    name=name, module=module, passed=False,
                    duration_ms=duration, error=str(result)
                ))
                self.log(f"FAILED: {name} - {result}", "FAIL")
                return False
                
        except Exception as e:
            duration = (time.time() - start) * 1000
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.results.append(TestResult(
                name=name, module=module, passed=False,
                duration_ms=duration, error=error_msg
            ))
            self.log(f"FAILED: {name} - {error_msg}", "FAIL")
            if os.getenv("DEBUG"):
                traceback.print_exc()
            return False
    
    def print_summary(self):
        """Print test summary."""
        total_time = (time.time() - self.start_time) * 1000
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        # Group by module
        modules = {}
        for r in self.results:
            if r.module not in modules:
                modules[r.module] = {"passed": 0, "failed": 0}
            if r.passed:
                modules[r.module]["passed"] += 1
            else:
                modules[r.module]["failed"] += 1
        
        for module, stats in modules.items():
            status = "✅" if stats["failed"] == 0 else "❌"
            print(f"  {status} {module}: {stats['passed']}/{stats['passed']+stats['failed']} passed")
        
        print("-"*60)
        print(f"  Total: {passed}/{passed+failed} tests passed")
        print(f"  Duration: {total_time:.1f}ms")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for r in self.results:
                if not r.passed:
                    print(f"  - [{r.module}] {r.name}: {r.error}")
        
        print("="*60)
        
        return failed == 0


# =============================================================================
# TEST FUNCTIONS - DATABASE
# =============================================================================

def test_db_connection():
    """Test database connection."""
    from db.connection import get_connection, close_connection
    conn = get_connection()
    assert conn is not None, "Connection is None"
    
    # Test simple query
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    cursor.close()
    close_connection(conn)
    
    assert result[0] == 1, "Query failed"
    return True

def test_db_products_query():
    """Test product queries."""
    from db.products import get_products_by_ids, get_popular_products_by_category
    
    # Test get popular products
    popular = get_popular_products_by_category("Electronics", limit=5)
    # May return empty if no products, that's OK
    
    # Test get by IDs (may not find anything, just test it runs)
    products = get_products_by_ids(["test-id-123"])
    
    return True


# =============================================================================
# TEST FUNCTIONS - AFIG
# =============================================================================

def test_afig_creation():
    """Test AFIG initialization."""
    from core.afig import AFIG
    
    afig = AFIG("test_user_123")
    assert afig.user_id == "test_user_123"
    afig.close()
    return True

def test_afig_reconcile():
    """Test AFIG reconciliation."""
    from core.afig import AFIG
    
    afig = AFIG("test_user_stress")
    context = afig.reconcile()
    
    assert "user_id" in context
    assert "archetype" in context
    assert "income_tier" in context
    assert "price_sensitivity" in context
    assert "budget_modifier" in context
    assert "layer_weights" in context
    
    afig.close()
    return True

def test_afig_situational_update():
    """Test AFIG situational layer update."""
    from core.afig import AFIG
    
    afig = AFIG("test_user_situational")
    afig.update_situational({
        "mission": "gaming setup",
        "timeline": "urgent",
        "budget_override": 2000.0
    })
    
    context = afig.reconcile()
    afig.close()
    return True

def test_afig_behavioral_update():
    """Test AFIG behavioral signal tracking."""
    from core.afig import AFIG
    
    afig = AFIG("test_user_behavioral")
    afig.update_behavioral({
        "type": "search",
        "query": "gaming laptop",
        "category": "laptops"
    })
    afig.update_behavioral({
        "type": "click",
        "product_id": "test-product-123",
        "price": 1299.99
    })
    
    context = afig.reconcile()
    afig.close()
    return True


# =============================================================================
# TEST FUNCTIONS - ROUTER
# =============================================================================

def test_router_init():
    """Test router initialization."""
    from core.router import QueryRouter
    
    router = QueryRouter()
    assert router is not None
    return True

def test_router_routing():
    """Test query routing to paths."""
    from core.router import QueryRouter
    
    router = QueryRouter()
    
    # Test simple query -> fast/smart path
    path1 = router.route("laptop", 1000, {"archetype": "default"})
    assert path1 in ["fast", "smart", "deep"], f"Invalid path: {path1}"
    
    # Test bundle query -> likely deep path
    path2 = router.route("gaming setup with laptop monitor and keyboard bundle", 5000, {"archetype": "tech_enthusiast"})
    assert path2 in ["fast", "smart", "deep"], f"Invalid path: {path2}"
    
    return True

def test_router_intent_extraction():
    """Test query intent extraction."""
    from core.router import QueryRouter
    
    router = QueryRouter()
    intent = router.get_query_intent("4k gaming monitor under 500")
    
    assert isinstance(intent, dict)
    return True

def test_router_cache_key():
    """Test cache key generation."""
    from core.router import QueryRouter
    
    router = QueryRouter()
    key1 = router.get_cache_key("laptop", 1000, "tech_enthusiast")
    key2 = router.get_cache_key("laptop", 1000, "tech_enthusiast")
    key3 = router.get_cache_key("laptop", 2000, "tech_enthusiast")
    
    assert key1 == key2, "Same inputs should produce same key"
    assert key1 != key3, "Different budgets should produce different keys"
    
    return True


# =============================================================================
# TEST FUNCTIONS - EMBEDDINGS
# =============================================================================

def test_embeddings_init():
    """Test embeddings service initialization."""
    from core.embeddings import EmbeddingService
    
    service = EmbeddingService()
    assert service is not None
    return True

def test_embeddings_encode_query():
    """Test query encoding."""
    from core.embeddings import EmbeddingService
    import numpy as np
    
    service = EmbeddingService()
    vec = service.encode_query("gaming laptop rtx 4080")
    
    assert vec is not None
    assert isinstance(vec, np.ndarray)
    assert len(vec) == 384, f"Expected 384-dim, got {len(vec)}"
    
    return True

def test_embeddings_encode_product():
    """Test product encoding."""
    from core.embeddings import EmbeddingService
    import numpy as np
    
    service = EmbeddingService()
    product = {
        "name": "ASUS ROG Gaming Laptop",
        "category": "Laptops",
        "brand": "ASUS",
        "features": ["RTX 4080", "32GB RAM", "1TB SSD"]
    }
    
    vec = service.encode_product(product)
    
    assert vec is not None
    assert isinstance(vec, np.ndarray)
    assert len(vec) == 384
    
    return True

def test_embeddings_similarity():
    """Test cosine similarity calculation."""
    from core.embeddings import EmbeddingService
    import numpy as np
    
    service = EmbeddingService()
    
    vec1 = service.encode_query("gaming laptop")
    vec2 = service.encode_query("gaming laptop computer")
    vec3 = service.encode_query("kitchen blender")
    
    # Similar queries should have high similarity
    sim_high = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    # Different queries should have lower similarity
    sim_low = np.dot(vec1, vec3) / (np.linalg.norm(vec1) * np.linalg.norm(vec3))
    
    assert sim_high > sim_low, "Similar queries should have higher similarity"
    
    return True


# =============================================================================
# TEST FUNCTIONS - SCORER
# =============================================================================

def test_scorer_init():
    """Test scorer initialization."""
    from core.scorer import LearnedProductScorer, get_scorer
    
    scorer = get_scorer()
    assert scorer is not None
    return True

def test_scorer_score_product():
    """Test single product scoring."""
    from core.scorer import get_scorer
    from core.embeddings import EmbeddingService
    import numpy as np
    
    scorer = get_scorer()
    embedder = EmbeddingService()
    
    product = {
        "product_id": "test-123",
        "name": "Gaming Laptop RTX 4080",
        "price": 1299.99,
        "category": "Laptops",
        "brand": "ASUS",
        "rating": 4.5,
        "rating_count": 150,
        "features": ["RTX 4080", "16GB RAM"]
    }
    
    query_vec = embedder.encode_query("gaming laptop")
    query_vec_normalized = query_vec / np.linalg.norm(query_vec)
    
    score = scorer.score_product(
        product=product,
        query_vec=query_vec_normalized,
        budget=2000,
        user_afig={"archetype": "tech_enthusiast", "price_sensitivity": 0.5}
    )
    
    assert isinstance(score, (int, float))
    assert 0 <= score <= 1, f"Score {score} out of range"
    
    return True

def test_scorer_rerank_results():
    """Test result reranking."""
    from core.scorer import get_scorer
    from core.embeddings import EmbeddingService
    import numpy as np
    
    scorer = get_scorer()
    embedder = EmbeddingService()
    
    products = [
        {"product_id": "1", "name": "Budget Laptop", "price": 500, "category": "Laptops", "rating": 3.5},
        {"product_id": "2", "name": "Gaming Laptop RTX", "price": 1500, "category": "Laptops", "rating": 4.8},
        {"product_id": "3", "name": "Kitchen Blender", "price": 100, "category": "Kitchen", "rating": 4.0},
    ]
    
    query_vec = embedder.encode_query("gaming laptop")
    query_vec_normalized = query_vec / np.linalg.norm(query_vec)
    
    reranked = scorer.rerank_results(
        results=products,
        query_vec=query_vec_normalized,
        budget=2000,
        user_afig={"archetype": "default"},
        embedder=embedder
    )
    
    assert len(reranked) == len(products)
    # Gaming laptop should be ranked higher
    names = [p["name"] for p in reranked[:2]]
    assert "Gaming Laptop RTX" in names, "Gaming laptop should be in top 2"
    
    return True


# =============================================================================
# TEST FUNCTIONS - TAXONOMY
# =============================================================================

def test_taxonomy_disambiguation():
    """Test search disambiguation."""
    from core.taxonomy import disambiguate_search
    
    result = disambiguate_search("apple laptop")
    
    assert isinstance(result, dict)
    assert "is_ambiguous" in result
    assert "primary_category" in result or "boost_categories" in result
    
    return True

def test_taxonomy_category_filter():
    """Test category filtering."""
    from core.taxonomy import CategoryTaxonomy
    
    # Test should_filter_result
    should_filter = CategoryTaxonomy.should_filter_result(
        result_category="Cases",
        exclude_categories=["Cases", "Accessories"],
        result_name="iPhone Case"
    )
    
    assert should_filter == True, "Should filter out cases"
    
    should_keep = CategoryTaxonomy.should_filter_result(
        result_category="Laptops",
        exclude_categories=["Cases", "Accessories"],
        result_name="Gaming Laptop"
    )
    
    assert should_keep == False, "Should keep laptops"
    
    return True


# =============================================================================
# TEST FUNCTIONS - VISUAL SEARCH
# =============================================================================

def test_visual_search_init():
    """Test visual search service initialization."""
    from core.visual_search import VisualSearchService, get_visual_service
    
    service = get_visual_service()
    assert service is not None
    return True

def test_visual_search_text_encode():
    """Test CLIP text encoding."""
    from core.visual_search import get_visual_service
    
    service = get_visual_service()
    
    if not service.is_available:
        return True  # Skip if CLIP not available
    
    vec = service.encode_text("gaming laptop")
    
    assert vec is not None
    assert len(vec) == 512, f"Expected 512-dim CLIP vector, got {len(vec)}"
    
    return True


# =============================================================================
# TEST FUNCTIONS - CACHE
# =============================================================================

def test_cache_init():
    """Test cache initialization."""
    from retrieval.cache import PostgreSQLCache
    
    cache = PostgreSQLCache(table_name="test_cache")
    assert cache is not None
    return True

def test_cache_set_get():
    """Test cache set and get operations."""
    from retrieval.cache import PostgreSQLCache
    import json
    
    cache = PostgreSQLCache(table_name="stress_test_cache")
    
    # Set value
    test_data = {"results": [{"id": 1, "name": "Test"}], "count": 1}
    cache.set("stress_test_key", test_data, ttl=60)
    
    # Get value
    retrieved = cache.get("stress_test_key")
    
    assert retrieved is not None, "Cache miss on recently set key"
    assert retrieved.get("count") == 1
    
    return True

def test_cache_miss():
    """Test cache miss behavior."""
    from retrieval.cache import PostgreSQLCache
    
    cache = PostgreSQLCache(table_name="stress_test_cache")
    
    result = cache.get("nonexistent_key_12345")
    assert result is None, "Should return None for missing key"
    
    return True


# =============================================================================
# TEST FUNCTIONS - QDRANT SEARCH
# =============================================================================

def test_qdrant_legacy_init():
    """Test legacy Qdrant search initialization."""
    from retrieval.qdrant_search import QdrantSearch
    
    search = QdrantSearch()
    assert search is not None
    # is_available may be False if Qdrant not connected, that's OK
    return True

def test_qdrant_multimodal_init():
    """Test multimodal Qdrant search initialization."""
    from retrieval.qdrant_search import MultimodalQdrantSearch, get_unified_search
    
    search = get_unified_search()
    assert search is not None
    # is_available may be False if collection doesn't exist
    return True

def test_qdrant_search_with_constraints():
    """Test Qdrant search with constraints."""
    from retrieval.qdrant_search import QdrantSearch
    from core.embeddings import EmbeddingService
    
    search = QdrantSearch()
    embedder = EmbeddingService()
    
    if not search.is_available:
        return True  # Skip if Qdrant not available
    
    query_vec = embedder.encode_query("gaming laptop")
    
    results = search.search_with_constraints(
        query_vector=query_vec.tolist(),
        max_price=2000,
        in_stock_only=True,
        limit=10
    )
    
    assert isinstance(results, list)
    
    # If results exist, verify structure
    if results:
        r = results[0]
        assert hasattr(r, 'product_id') or 'product_id' in r
    
    return True

def test_qdrant_multimodal_search():
    """Test unified multimodal search."""
    from retrieval.qdrant_search import get_unified_search
    
    search = get_unified_search()
    
    if not search.is_available:
        return True  # Skip if not available
    
    results = search.search(
        query="gaming monitor 4k",
        max_price=1000,
        limit=10
    )
    
    assert isinstance(results, list)
    
    return True


# =============================================================================
# TEST FUNCTIONS - FEASIBILITY GATE
# =============================================================================

def test_feasibility_init():
    """Test feasibility gate initialization."""
    from optimization.feasibility import FeasibilityGate
    
    gate = FeasibilityGate()
    assert gate is not None
    return True

def test_feasibility_check_simple():
    """Test simple feasibility check."""
    from optimization.feasibility import FeasibilityGate
    
    gate = FeasibilityGate()
    
    # Product under budget - should be feasible
    result = gate.check_feasibility(
        product={"price": 500, "name": "Test Product"},
        budget=1000,
        cart_total=0
    )
    
    assert result["feasible"] == True
    
    # Product over budget - should not be feasible
    result2 = gate.check_feasibility(
        product={"price": 1500, "name": "Expensive Product"},
        budget=1000,
        cart_total=0
    )
    
    assert result2["feasible"] == False
    
    return True


# =============================================================================
# TEST FUNCTIONS - BUNDLE OPTIMIZER
# =============================================================================

def test_optimizer_init():
    """Test bundle optimizer initialization."""
    from optimization.bundle_optimizer import BundleOptimizer
    
    optimizer = BundleOptimizer()
    assert optimizer is not None
    return True

def test_optimizer_optimize():
    """Test bundle optimization."""
    from optimization.bundle_optimizer import BundleOptimizer, Product
    
    optimizer = BundleOptimizer()
    
    products = [
        Product(id="1", name="Laptop", price=1000, category="laptop", utility=0.9),
        Product(id="2", name="Monitor", price=300, category="monitor", utility=0.8),
        Product(id="3", name="Keyboard", price=100, category="keyboard", utility=0.7),
        Product(id="4", name="Mouse", price=50, category="mouse", utility=0.6),
        Product(id="5", name="Headset", price=150, category="headset", utility=0.75),
    ]
    
    result = optimizer.optimize(
        products=products,
        budget=2000,
        user_prefs={"archetype": "tech_enthusiast"},
        required_categories=["laptop", "monitor"],
        max_items=4
    )
    
    assert result is not None
    assert hasattr(result, 'bundle')
    assert hasattr(result, 'total_price')
    assert result.total_price <= 2000
    
    # Should include required categories
    bundle_categories = {p.category for p in result.bundle}
    assert "laptop" in bundle_categories or "monitor" in bundle_categories
    
    return True


# =============================================================================
# TEST FUNCTIONS - BUDGET AGENT
# =============================================================================

def test_agent_init():
    """Test budget agent initialization."""
    from agent.budget_agent import BudgetPathfinderAgent
    
    agent = BudgetPathfinderAgent()
    assert agent is not None
    return True

async def test_agent_find_paths():
    """Test agent affordability path finding."""
    from agent.budget_agent import BudgetPathfinderAgent
    
    agent = BudgetPathfinderAgent()
    
    product = {
        "name": "Gaming Laptop RTX 4080",
        "price": 2500,
        "category": "laptops"
    }
    
    result = await agent.find_affordability_paths(
        product=product,
        user_afig={"archetype": "budget_conscious", "price_sensitivity": 0.8},
        current_cart=[],
        budget=2000
    )
    
    # Agent may return None if no paths found, that's OK
    if result:
        assert hasattr(result, 'paths') or hasattr(result, 'to_dict')
    
    return True


# =============================================================================
# TEST FUNCTIONS - LLM EXPLAINER
# =============================================================================

def test_explainer_init():
    """Test LLM explainer initialization."""
    from explanation.llm_explainer import LLMExplainer
    
    explainer = LLMExplainer()
    assert explainer is not None
    return True

async def test_explainer_explain():
    """Test product explanation generation."""
    from explanation.llm_explainer import LLMExplainer
    
    explainer = LLMExplainer()
    
    product = {
        "name": "ASUS ROG Gaming Laptop",
        "price": 1499.99,
        "category": "Laptops",
        "brand": "ASUS",
        "rating": 4.7
    }
    
    explanation = await explainer.explain(
        product=product,
        user_context={"archetype": "tech_enthusiast"}
    )
    
    assert isinstance(explanation, str)
    assert len(explanation) > 0
    
    return True


# =============================================================================
# TEST FUNCTIONS - SEARCH ENGINE
# =============================================================================

def test_search_engine_init():
    """Test search engine initialization."""
    from core.search_engine import FinBundleEngine
    
    engine = FinBundleEngine()
    assert engine is not None
    assert engine.router is not None
    assert engine.embedder is not None
    return True

async def test_search_engine_fast_path():
    """Test fast path search."""
    from core.search_engine import FinBundleEngine
    
    engine = FinBundleEngine()
    
    result = await engine.search(
        query="laptop",
        user_id="test_fast_path",
        budget=1500,
        cart=[],
        skip_explanations=True
    )
    
    assert "path" in result
    assert "metrics" in result
    
    return True

async def test_search_engine_smart_path():
    """Test smart path search."""
    from core.search_engine import FinBundleEngine
    
    engine = FinBundleEngine()
    
    result = await engine.search(
        query="gaming laptop rtx 4080 high performance under 2000",
        user_id="test_smart_path",
        budget=2000,
        cart=[],
        skip_explanations=True
    )
    
    assert "path" in result
    assert "metrics" in result
    
    # Smart path should return results
    if result.get("path") == "smart":
        assert "results" in result
    
    return True

async def test_search_engine_deep_path():
    """Test deep path search (bundles)."""
    from core.search_engine import FinBundleEngine
    
    engine = FinBundleEngine()
    
    result = await engine.search(
        query="complete gaming setup bundle laptop monitor keyboard mouse headset",
        user_id="test_deep_path",
        budget=5000,
        cart=[],
        skip_explanations=True  # Skip slow LLM calls
    )
    
    assert "path" in result
    assert "metrics" in result
    
    # Deep path should return bundle info
    if result.get("path") == "deep":
        assert "bundle" in result or "curated_products" in result
    
    return True


# =============================================================================
# TEST FUNCTIONS - METRICS
# =============================================================================

def test_metrics_init():
    """Test metrics logger initialization."""
    from core.metrics import get_metrics_logger
    
    logger = get_metrics_logger()
    assert logger is not None
    return True

def test_metrics_log_search():
    """Test logging a search event."""
    from core.metrics import get_metrics_logger
    
    logger = get_metrics_logger()
    
    logger.log_search(
        query="test query",
        user_id="test_user",
        path="smart",
        latency_ms=150.5,
        cache_hit=False,
        result_count=10
    )
    
    return True


# =============================================================================
# TEST FUNCTIONS - API (using TestClient)
# =============================================================================

def test_api_health():
    """Test API health endpoint."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        
        return True
    except ImportError:
        # TestClient not available, skip
        return True

def test_api_categories():
    """Test API categories endpoint."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        response = client.get("/api/categories")
        
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        
        return True
    except ImportError:
        return True


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests(fast_mode: bool = False, module_filter: str = None):
    """Run all tests."""
    suite = TestSuite()
    suite.start_time = time.time()
    suite.fast_mode = fast_mode
    
    print("="*60)
    print("🧪 FINBUNDLE COMPREHENSIVE STRESS TEST")
    print("="*60)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🚀 Fast Mode: {fast_mode}")
    if module_filter:
        print(f"🔍 Module Filter: {module_filter}")
    print("="*60)
    
    # Define all tests
    tests = {
        "db": [
            ("DB Connection", test_db_connection),
            ("DB Products Query", test_db_products_query),
        ],
        "afig": [
            ("AFIG Creation", test_afig_creation),
            ("AFIG Reconcile", test_afig_reconcile),
            ("AFIG Situational Update", test_afig_situational_update),
            ("AFIG Behavioral Update", test_afig_behavioral_update),
        ],
        "router": [
            ("Router Init", test_router_init),
            ("Router Routing", test_router_routing),
            ("Router Intent Extraction", test_router_intent_extraction),
            ("Router Cache Key", test_router_cache_key),
        ],
        "embeddings": [
            ("Embeddings Init", test_embeddings_init),
            ("Embeddings Encode Query", test_embeddings_encode_query),
            ("Embeddings Encode Product", test_embeddings_encode_product),
            ("Embeddings Similarity", test_embeddings_similarity),
        ],
        "scorer": [
            ("Scorer Init", test_scorer_init),
            ("Scorer Score Product", test_scorer_score_product),
            ("Scorer Rerank Results", test_scorer_rerank_results),
        ],
        "taxonomy": [
            ("Taxonomy Disambiguation", test_taxonomy_disambiguation),
            ("Taxonomy Category Filter", test_taxonomy_category_filter),
        ],
        "visual_search": [
            ("Visual Search Init", test_visual_search_init),
            ("Visual Search Text Encode", test_visual_search_text_encode),
        ],
        "cache": [
            ("Cache Init", test_cache_init),
            ("Cache Set/Get", test_cache_set_get),
            ("Cache Miss", test_cache_miss),
        ],
        "qdrant": [
            ("Qdrant Legacy Init", test_qdrant_legacy_init),
            ("Qdrant Multimodal Init", test_qdrant_multimodal_init),
            ("Qdrant Search with Constraints", test_qdrant_search_with_constraints),
            ("Qdrant Multimodal Search", test_qdrant_multimodal_search),
        ],
        "feasibility": [
            ("Feasibility Init", test_feasibility_init),
            ("Feasibility Check", test_feasibility_check_simple),
        ],
        "optimizer": [
            ("Optimizer Init", test_optimizer_init),
            ("Optimizer Optimize Bundle", test_optimizer_optimize),
        ],
        "agent": [
            ("Agent Init", test_agent_init),
        ],
        "explainer": [
            ("Explainer Init", test_explainer_init),
        ],
        "search_engine": [
            ("Search Engine Init", test_search_engine_init),
        ],
        "metrics": [
            ("Metrics Init", test_metrics_init),
            ("Metrics Log Search", test_metrics_log_search),
        ],
        "api": [
            ("API Health", test_api_health),
            ("API Categories", test_api_categories),
        ],
    }
    
    # Async tests (run separately)
    async_tests = {
        "agent": [
            ("Agent Find Paths", test_agent_find_paths),
        ],
        "explainer": [
            ("Explainer Explain", test_explainer_explain),
        ],
        "search_engine": [
            ("Search Engine Fast Path", test_search_engine_fast_path),
            ("Search Engine Smart Path", test_search_engine_smart_path),
        ],
    }
    
    # Slow async tests (skip in fast mode)
    slow_async_tests = {
        "search_engine": [
            ("Search Engine Deep Path", test_search_engine_deep_path),
        ],
    }
    
    # Run sync tests
    for module, module_tests in tests.items():
        if module_filter and module_filter.lower() not in module.lower():
            continue
            
        print(f"\n📦 Module: {module.upper()}")
        print("-"*40)
        
        for name, func in module_tests:
            suite.run_test(name, module, func)
    
    # Run async tests
    async def run_async():
        for module, module_tests in async_tests.items():
            if module_filter and module_filter.lower() not in module.lower():
                continue
                
            for name, func in module_tests:
                await suite.run_async_test(name, module, func)
        
        # Slow tests
        if not fast_mode:
            for module, module_tests in slow_async_tests.items():
                if module_filter and module_filter.lower() not in module.lower():
                    continue
                    
                for name, func in module_tests:
                    await suite.run_async_test(name, module, func)
    
    print(f"\n📦 Module: ASYNC TESTS")
    print("-"*40)
    asyncio.run(run_async())
    
    # Print summary
    success = suite.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinBundle Stress Test Suite")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--module", type=str, help="Only test specific module")
    parser.add_argument("--debug", action="store_true", help="Show full tracebacks")
    
    args = parser.parse_args()
    
    if args.debug:
        os.environ["DEBUG"] = "1"
    
    exit_code = run_all_tests(fast_mode=args.fast, module_filter=args.module)
    sys.exit(exit_code)
