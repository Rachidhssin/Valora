"""
Comprehensive Stress Test for Valora/FinBundle
Tests all major components and identifies issues
"""
import os
import sys
import time
import json
import asyncio
import traceback
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test results collector
RESULTS = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_pass(test_name, details=""):
    print(f"  ✅ {test_name}")
    if details:
        print(f"     {details}")
    RESULTS["passed"].append({"test": test_name, "details": details})

def log_fail(test_name, error, suggestion=""):
    print(f"  ❌ {test_name}")
    print(f"     Error: {error}")
    if suggestion:
        print(f"     Fix: {suggestion}")
    RESULTS["failed"].append({"test": test_name, "error": str(error), "suggestion": suggestion})

def log_warn(test_name, warning):
    print(f"  ⚠️  {test_name}")
    print(f"     {warning}")
    RESULTS["warnings"].append({"test": test_name, "warning": warning})


# ============================================================
# TEST 1: Database Connection & Cache
# ============================================================
def test_database_and_cache():
    print("\n" + "="*60)
    print("🔍 TEST 1: Database Connection & Cache")
    print("="*60)
    
    # Test 1.1: PostgreSQL connection
    try:
        from db.connection import init_pool, close_pool, get_connection
        if init_pool():
            log_pass("PostgreSQL connection pool")
        else:
            log_fail("PostgreSQL connection pool", "init_pool() returned False", 
                    "Check DATABASE_URL in .env")
    except Exception as e:
        log_fail("PostgreSQL connection pool", e, "Ensure PostgreSQL is running")
    
    # Test 1.2: Products table
    try:
        from db.products import get_product_count, get_products_by_ids
        count = get_product_count()
        if count > 0:
            log_pass(f"Products table", f"{count} products found")
        else:
            log_warn("Products table", "No products in database - run ingest script")
    except Exception as e:
        log_fail("Products table query", e)
    
    # Test 1.3: Cache mechanism
    try:
        from retrieval.cache import PostgreSQLCache
        cache = PostgreSQLCache(table_name="test_cache")
        
        # Test set
        test_key = "stress_test_key"
        test_value = {"test": "data", "number": 123, "nested": {"a": 1}}
        cache.set(test_key, test_value, ttl=60)
        
        # Test get
        retrieved = cache.get(test_key)
        if retrieved and retrieved.get("test") == "data":
            log_pass("Cache SET/GET", "Basic caching works")
        else:
            log_fail("Cache GET", f"Retrieved: {retrieved}", "Check cache implementation")
        
        # Test with Decimal (common issue)
        from decimal import Decimal
        decimal_value = {"price": Decimal("123.45"), "quantity": 5}
        try:
            cache.set("decimal_test", decimal_value, ttl=60)
            retrieved_decimal = cache.get("decimal_test")
            if retrieved_decimal:
                log_pass("Cache with Decimal", "Decimal serialization works")
            else:
                log_fail("Cache with Decimal", "Failed to retrieve", "Check DecimalEncoder")
        except Exception as e:
            log_fail("Cache with Decimal", e, "Add Decimal handling to JSON encoder")
        
        # Test with datetime
        from datetime import datetime
        dt_value = {"timestamp": datetime.now(), "data": "test"}
        try:
            cache.set("datetime_test", dt_value, ttl=60)
            retrieved_dt = cache.get("datetime_test")
            if retrieved_dt:
                log_pass("Cache with datetime", "Datetime serialization works")
            else:
                log_fail("Cache with datetime", "Failed to retrieve")
        except Exception as e:
            log_fail("Cache with datetime", e, "Add datetime handling to JSON encoder")
        
        # Test with numpy arrays (common in search results)
        import numpy as np
        np_value = {
            "embedding": np.random.randn(384),
            "scores": np.array([0.9, 0.85, 0.7]),
            "float32": np.float32(0.95),
            "int64": np.int64(42)
        }
        try:
            cache.set("numpy_test", np_value, ttl=60)
            retrieved_np = cache.get("numpy_test")
            if retrieved_np and "embedding" in retrieved_np:
                log_pass("Cache with numpy", "Numpy arrays/scalars serialize correctly")
            else:
                log_fail("Cache with numpy", "Failed to retrieve numpy data")
        except Exception as e:
            log_fail("Cache with numpy", e, "Add numpy handling to JSON encoder")
            
    except Exception as e:
        log_fail("Cache mechanism", e, traceback.format_exc())


# ============================================================
# TEST 2: Embeddings & Vector Search
# ============================================================
def test_embeddings_and_search():
    print("\n" + "="*60)
    print("🔍 TEST 2: Embeddings & Vector Search")
    print("="*60)
    
    # Test 2.1: Sentence Transformers
    try:
        from core.embeddings import EmbeddingService
        embedder = EmbeddingService()
        
        query = "gaming laptop RTX 4070"
        vec = embedder.encode_query(query)
        
        if vec is not None and len(vec) == 384:
            log_pass("Sentence Transformers", f"Embedding shape: {vec.shape}")
        else:
            log_fail("Sentence Transformers", f"Wrong shape: {vec.shape if vec is not None else 'None'}")
            
        # Test L2 normalization
        import numpy as np
        norm = np.linalg.norm(vec)
        if 0.99 < norm < 1.01:
            log_pass("Vector normalization", f"L2 norm: {norm:.4f}")
        else:
            log_warn("Vector normalization", f"Vectors not normalized (norm={norm:.4f}), may affect scoring")
            
    except Exception as e:
        log_fail("Sentence Transformers", e)
    
    # Test 2.2: Qdrant connection
    try:
        from retrieval.qdrant_search import QdrantSearch
        qdrant = QdrantSearch()
        
        if qdrant.is_available:
            log_pass("Qdrant connection")
        else:
            log_fail("Qdrant connection", "Not available", "Check QDRANT_URL in .env")
            return
        
        # Test search
        import numpy as np
        test_vec = np.random.randn(384).tolist()
        results = qdrant.search(test_vec, limit=5)
        
        if results and len(results) > 0:
            log_pass("Qdrant search", f"Retrieved {len(results)} results")
            
            # Check result structure
            first = results[0]
            required_fields = ['product_id', 'name', 'price', 'category']
            missing = [f for f in required_fields if not hasattr(first, f) or getattr(first, f) is None]
            if missing:
                log_warn("Qdrant result structure", f"Missing fields: {missing}")
            else:
                log_pass("Qdrant result structure", "All required fields present")
        else:
            log_warn("Qdrant search", "No results - collection may be empty")
            
    except Exception as e:
        log_fail("Qdrant search", e, traceback.format_exc())


# ============================================================
# TEST 3: Visual Search (CLIP)
# ============================================================
def test_visual_search():
    print("\n" + "="*60)
    print("🔍 TEST 3: Visual Search (CLIP)")
    print("="*60)
    
    try:
        from core.visual_search import get_visual_service, _check_clip_available
        
        # Test availability
        if not _check_clip_available():
            log_fail("CLIP dependencies", "transformers/torch/PIL not installed",
                    "pip install transformers torch pillow")
            return
        
        log_pass("CLIP dependencies")
        
        vs = get_visual_service()
        
        if vs.is_available:
            log_pass("CLIP model loaded")
        else:
            log_fail("CLIP model loading", "Model failed to load")
            return
        
        # Test text encoding
        text_vec = vs.encode_text("a gaming laptop with RGB keyboard")
        if text_vec is not None and len(text_vec) == 512:
            log_pass("CLIP text encoding", f"Shape: {text_vec.shape}")
        else:
            log_fail("CLIP text encoding", f"Wrong result: {type(text_vec)}")
        
        # Test with base64 image (create a simple test image)
        try:
            from PIL import Image
            import io
            import base64
            
            # Create a simple test image
            img = Image.new('RGB', (100, 100), color='red')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_bytes = buffer.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # Test with raw bytes
            img_vec_bytes = vs.encode_image(img_bytes)
            if img_vec_bytes is not None and len(img_vec_bytes) == 512:
                log_pass("CLIP image encoding (bytes)", f"Shape: {img_vec_bytes.shape}")
            else:
                log_fail("CLIP image encoding (bytes)", "Failed to encode")
            
            # Test with base64
            img_vec_b64 = vs.encode_image(img_base64)
            if img_vec_b64 is not None and len(img_vec_b64) == 512:
                log_pass("CLIP image encoding (base64)", f"Shape: {img_vec_b64.shape}")
            else:
                log_fail("CLIP image encoding (base64)", "Failed to encode")
            
            # Test with data URL prefix (how frontend sends it)
            data_url = f"data:image/png;base64,{img_base64}"
            img_vec_dataurl = vs.encode_image(data_url)
            if img_vec_dataurl is not None and len(img_vec_dataurl) == 512:
                log_pass("CLIP image encoding (data URL)", "Frontend format works")
            else:
                log_fail("CLIP image encoding (data URL)", "Failed with data:image prefix",
                        "Check base64 parsing in visual_search.py")
                
        except Exception as e:
            log_fail("CLIP image encoding", e, traceback.format_exc())
            
    except Exception as e:
        log_fail("Visual search module", e, traceback.format_exc())


# ============================================================
# TEST 4: Scorer
# ============================================================
def test_scorer():
    print("\n" + "="*60)
    print("🔍 TEST 4: LearnedProductScorer")
    print("="*60)
    
    try:
        from core.scorer import get_scorer, LearnedProductScorer
        import numpy as np
        
        scorer = get_scorer()
        log_pass("Scorer initialization")
        
        # Test product scoring
        product = {
            'name': 'Test Laptop',
            'price': 999,
            'rating': 4.5,
            'brand': 'ASUS',
            'category': 'laptops',
            'condition': 'new'
        }
        
        query_vec = np.random.randn(384)
        query_vec = query_vec / np.linalg.norm(query_vec)
        
        product_vec = np.random.randn(384)
        product_vec = product_vec / np.linalg.norm(product_vec)
        
        user_afig = {
            'archetype': 'quality_seeker',
            'risk_tolerance': 0.5,
            'brand_sensitivity': 0.7
        }
        
        result = scorer.score_product(product, query_vec, product_vec, budget=1500, user_afig=user_afig)
        
        required_keys = ['final_score', 'semantic_score', 'price_score', 'quality_score', 'afig_score']
        missing = [k for k in required_keys if k not in result]
        
        if not missing:
            log_pass("Product scoring", f"Final score: {result['final_score']}")
        else:
            log_fail("Product scoring", f"Missing keys: {missing}")
        
        # Test edge cases
        # Zero budget
        result_zero = scorer.score_product(product, query_vec, product_vec, budget=0, user_afig=user_afig)
        if result_zero['price_score'] == 0.5:  # Should be neutral
            log_pass("Edge case: zero budget")
        else:
            log_warn("Edge case: zero budget", f"Price score: {result_zero['price_score']}")
        
        # None vectors
        result_none = scorer.score_product(product, None, None, budget=1500, user_afig=user_afig)
        if result_none['semantic_score'] == 0.5:  # Should be neutral
            log_pass("Edge case: None vectors")
        else:
            log_warn("Edge case: None vectors", f"Semantic score: {result_none['semantic_score']}")
            
    except Exception as e:
        log_fail("Scorer", e, traceback.format_exc())


# ============================================================
# TEST 5: Bundle Optimizer
# ============================================================
def test_bundle_optimizer():
    print("\n" + "="*60)
    print("🔍 TEST 5: Bundle Optimizer")
    print("="*60)
    
    try:
        from optimization.bundle_optimizer import BundleOptimizer, Product, OptStatus
        
        optimizer = BundleOptimizer()
        log_pass("Optimizer initialization")
        
        # Create test products
        products = [
            Product("1", "Gaming Laptop", 1200, "laptops", 0.9, "http://img1.jpg", "ASUS", 4.5),
            Product("2", "Monitor 27\"", 350, "monitors", 0.85, "http://img2.jpg", "LG", 4.3),
            Product("3", "Keyboard", 100, "keyboards", 0.7, "http://img3.jpg", "Logitech", 4.6),
            Product("4", "Mouse", 70, "mice", 0.65, "http://img4.jpg", "Logitech", 4.4),
            Product("5", "Headset", 120, "headsets", 0.75, "http://img5.jpg", "Sony", 4.2),
        ]
        
        user_prefs = {'archetype': 'quality_seeker'}
        
        # Test optimization
        result = optimizer.optimize(products, budget=1500, user_prefs=user_prefs)
        
        if result.status in [OptStatus.OPTIMAL, OptStatus.FEASIBLE]:
            log_pass("Bundle optimization", 
                    f"Status: {result.status.value}, Items: {len(result.bundle)}, Total: ${result.total_price:.2f}")
        else:
            log_fail("Bundle optimization", f"Status: {result.status.value}")
        
        # Test with dict input (common from API)
        dict_products = [
            {'product_id': '1', 'name': 'Laptop', 'price': 999, 'category': 'laptops', 
             'utility': 0.8, 'image_url': 'http://img.jpg', 'brand': 'Dell', 'rating': 4.5},
            {'product_id': '2', 'name': 'Monitor', 'price': 300, 'category': 'monitors',
             'utility': 0.7, 'image_url': '', 'brand': 'LG', 'rating': 4.2}
        ]
        
        result_dict = optimizer.optimize(dict_products, budget=1500, user_prefs=user_prefs)
        
        if result_dict.bundle:
            # Check if image_url is preserved
            first_item = result_dict.bundle[0]
            if hasattr(first_item, 'image_url') and first_item.image_url:
                log_pass("Optimizer preserves image_url")
            else:
                log_fail("Optimizer image_url", "image_url not preserved in Product",
                        "Check _ensure_products in bundle_optimizer.py")
            
            if hasattr(first_item, 'brand') and first_item.brand:
                log_pass("Optimizer preserves brand")
            else:
                log_fail("Optimizer brand", "brand not preserved")
                
            if hasattr(first_item, 'rating') and first_item.rating:
                log_pass("Optimizer preserves rating")
            else:
                log_fail("Optimizer rating", "rating not preserved")
        else:
            log_warn("Optimizer dict input", "No results")
        
        # Test to_dict
        result_dict_output = result.to_dict()
        if 'bundle' in result_dict_output and len(result_dict_output['bundle']) > 0:
            first_bundle_item = result_dict_output['bundle'][0]
            if 'image_url' in first_bundle_item:
                log_pass("to_dict includes image_url")
            else:
                log_fail("to_dict missing image_url", "image_url not in output",
                        "Update to_dict in OptimizationResult")
        
    except Exception as e:
        log_fail("Bundle optimizer", e, traceback.format_exc())


# ============================================================
# TEST 6: Search Engine Integration
# ============================================================
def test_search_engine():
    print("\n" + "="*60)
    print("🔍 TEST 6: Search Engine Integration")
    print("="*60)
    
    try:
        from core.search_engine import FinBundleEngine
        
        engine = FinBundleEngine()
        log_pass("Engine initialization")
        
        # Test search (async)
        async def run_search():
            result = await engine.search(
                query="gaming laptop",
                user_id="test_user",
                budget=1500,
                cart=[],
                skip_explanations=True
            )
            return result
        
        result = asyncio.run(run_search())
        
        if result and 'path' in result:
            log_pass(f"Search execution", f"Path: {result['path']}")
        else:
            log_fail("Search execution", "No result returned")
            return
        
        if 'results' in result and result['results']:
            log_pass(f"Search results", f"Count: {len(result['results'])}")
            
            # Check result structure
            first = result['results'][0]
            
            # Check for image_url
            if first.get('image_url'):
                log_pass("Results have image_url")
            else:
                log_warn("Results missing image_url", "Images may not display in frontend")
            
            # Check for scoring info
            if '_scoring' in first:
                log_pass("Results include scoring breakdown")
            else:
                log_warn("Results missing _scoring", "Scoring transparency not available")
        else:
            log_warn("Search results empty", "May need to check Qdrant/DB data")
            
    except Exception as e:
        log_fail("Search engine", e, traceback.format_exc())


# ============================================================
# TEST 7: API Endpoints
# ============================================================
def test_api_endpoints():
    print("\n" + "="*60)
    print("🔍 TEST 7: API Endpoints")
    print("="*60)
    
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        # Note: TestClient doesn't trigger lifespan by default
        # Using lifespan context manager for proper initialization
        with TestClient(app) as client:
            # Test health
            response = client.get("/api/health")
            if response.status_code == 200:
                log_pass("GET /api/health")
            else:
                log_fail("GET /api/health", f"Status: {response.status_code}")
            
            # Test search
            response = client.post("/api/search", json={
                "query": "laptop",
                "budget": 1000,
                "user_id": "test"
            })
            if response.status_code == 200:
                data = response.json()
                log_pass("POST /api/search", f"Path: {data.get('path')}")
            else:
                log_fail("POST /api/search", f"Status: {response.status_code}, {response.text[:200]}")
            
            # Test optimize
            response = client.post("/api/optimize", json={
                "cart": [
                    {"product_id": "test1", "name": "Test Product", "price": 500, "category": "laptops"}
                ],
                "budget": 1000,
                "user_id": "test"
            })
            if response.status_code == 200:
                data = response.json()
                if data.get('success') or data.get('optimized_products'):
                    log_pass("POST /api/optimize")
                else:
                    log_warn("POST /api/optimize", f"Response: {data}")
            else:
                log_fail("POST /api/optimize", f"Status: {response.status_code}, {response.text[:200]}")
            
            # Test visual search
            import base64
            from PIL import Image
            import io
            
            # Create test image
            img = Image.new('RGB', (100, 100), color='blue')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            response = client.post("/api/search/visual", json={
                "image_base64": img_base64,
                "budget": 1000,
                "user_id": "test",
                "text_query": "laptop"
            })
            if response.status_code == 200:
                data = response.json()
                log_pass("POST /api/search/visual", f"Results: {len(data.get('results', []))}")
            elif response.status_code == 503:
                log_warn("POST /api/search/visual", "CLIP not available - expected if dependencies missing")
            else:
                log_fail("POST /api/search/visual", f"Status: {response.status_code}, {response.text[:200]}")
            
            # Test with data URL format (frontend sends this)
            data_url = f"data:image/png;base64,{img_base64}"
            response = client.post("/api/search/visual", json={
                "image_base64": data_url,
                "budget": 1000
            })
            if response.status_code == 200:
                log_pass("Visual search with data URL format")
            else:
                log_fail("Visual search data URL", f"Status: {response.status_code}",
                        "Frontend sends 'data:image/png;base64,...' format")
            
    except ImportError:
        log_warn("API tests", "Install httpx for API tests: pip install httpx")
    except Exception as e:
        log_fail("API endpoints", e, traceback.format_exc())


# ============================================================
# TEST 8: AFIG (User Profiles)
# ============================================================
def test_afig():
    print("\n" + "="*60)
    print("🔍 TEST 8: AFIG (User Profiles)")
    print("="*60)
    
    try:
        from core.afig import AFIG
        
        afig = AFIG("test_user_stress")
        log_pass("AFIG initialization")
        
        # Test reconcile
        context = afig.reconcile()
        
        required_keys = ['user_id', 'archetype']
        missing = [k for k in required_keys if k not in context]
        
        if not missing:
            log_pass("AFIG reconcile", f"Archetype: {context.get('archetype')}")
        else:
            log_fail("AFIG reconcile", f"Missing keys: {missing}")
        
        # Test update
        try:
            afig.update_behavioral({'type': 'search', 'query': 'test'})
            log_pass("AFIG behavioral update")
        except Exception as e:
            log_fail("AFIG behavioral update", e)
        
        # Test close
        try:
            afig.close()
            log_pass("AFIG close")
        except Exception as e:
            log_fail("AFIG close", e)
            
    except Exception as e:
        log_fail("AFIG", e, traceback.format_exc())


# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "="*60)
    print("🚀 VALORA STRESS TEST")
    print("="*60)
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    test_database_and_cache()
    test_embeddings_and_search()
    test_visual_search()
    test_scorer()
    test_bundle_optimizer()
    test_search_engine()
    test_api_endpoints()
    test_afig()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"  ✅ Passed:   {len(RESULTS['passed'])}")
    print(f"  ❌ Failed:   {len(RESULTS['failed'])}")
    print(f"  ⚠️  Warnings: {len(RESULTS['warnings'])}")
    
    if RESULTS['failed']:
        print("\n" + "="*60)
        print("❌ FAILED TESTS - NEED TO FIX:")
        print("="*60)
        for item in RESULTS['failed']:
            print(f"\n  • {item['test']}")
            print(f"    Error: {item['error'][:100]}")
            if item.get('suggestion'):
                print(f"    Fix: {item['suggestion']}")
    
    if RESULTS['warnings']:
        print("\n" + "="*60)
        print("⚠️  WARNINGS - SHOULD REVIEW:")
        print("="*60)
        for item in RESULTS['warnings']:
            print(f"\n  • {item['test']}")
            print(f"    {item['warning']}")
    
    print("\n" + "="*60)
    print(f"Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    return len(RESULTS['failed'])


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
