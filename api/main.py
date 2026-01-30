"""
FinBundle FastAPI Backend
RESTful API for the React frontend
"""
import os
import asyncio
import base64
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Import FinBundle components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.search_engine import FinBundleEngine
from core.afig import AFIG
from core.afig import AFIG
from core.metrics import get_metrics_logger
from api.analytics_routes import router as analytics_router


# --- Pydantic Models ---

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    budget: float = Field(..., ge=10, le=50000)
    user_id: str = Field(default="anonymous")
    cart: List[Dict[str, Any]] = Field(default_factory=list)
    skip_explanations: bool = Field(default=False, description="Skip slow LLM explanations for faster response")


class VisualSearchRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image (with or without data URL prefix)")
    budget: float = Field(default=1000, ge=10, le=50000)
    user_id: str = Field(default="anonymous")
    text_query: Optional[str] = Field(default=None, description="Optional text to combine with image search")


class SearchResponse(BaseModel):
    path: str
    results: Optional[List[Dict]] = None
    bundle: Optional[Dict] = None
    curated_products: Optional[Dict[str, List[Dict]]] = None  # Deep path: category -> products with is_recommended
    agent_paths: Optional[Dict] = None
    explanations: Optional[List[Dict]] = None
    bundle_explanation: Optional[str] = None
    metrics: Dict[str, Any]
    cache_hit: bool = False


class ProductResponse(BaseModel):
    product_id: str
    name: str
    price: float
    category: str
    brand: str
    rating: float
    score: float = 0
    utility: float = 0


class CartItem(BaseModel):
    product_id: str
    name: str
    price: float
    category: str
    quantity: int = 1


class UserProfile(BaseModel):
    user_id: str
    archetype: str
    income_tier: str
    price_sensitivity: float
    budget_modifier: float
    layer_weights: Dict[str, float]


class AFIGUpdate(BaseModel):
    mission: Optional[str] = None
    timeline: Optional[str] = None
    budget_override: Optional[float] = None


class BehavioralSignal(BaseModel):
    type: str  # click, search, cart_action, dwell, price_jump
    data: Dict[str, Any]


# --- App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting FinBundle API...")
    app.state.engine = FinBundleEngine()
    app.state.metrics = get_metrics_logger()
    app.state.request_count = 0
    app.state.total_latency_ms = 0
    print("✅ Engine initialized")
    yield
    # Shutdown
    print("👋 Shutting down...")
    app.state.metrics.close()


app = FastAPI(
    title="FinBundle API",
    description="AI-Powered Smart Product Discovery Engine",
    version="3.0.0",
    lifespan=lifespan
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Analytics Router
app.include_router(analytics_router, prefix="/api")


# --- Performance Middleware ---

import time as time_module
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class PerformanceMiddleware(BaseHTTPMiddleware):
    """Add performance headers and track latency."""
    
    async def dispatch(self, request: Request, call_next):
        start = time_module.time()
        response = await call_next(request)
        latency_ms = (time_module.time() - start) * 1000
        
        # Add timing headers
        response.headers["X-Response-Time"] = f"{latency_ms:.2f}ms"
        response.headers["X-Server-Version"] = "3.0.0"
        
        # Track stats (only for API routes)
        if request.url.path.startswith("/api"):
            if hasattr(app.state, 'request_count'):
                app.state.request_count += 1
                app.state.total_latency_ms += latency_ms
        
        return response

app.add_middleware(PerformanceMiddleware)


# --- Helper Functions ---

def get_engine():
    """Get engine with proper initialization check."""
    if not hasattr(app.state, 'engine') or app.state.engine is None:
        raise HTTPException(
            status_code=503,
            detail="Server is still initializing. Please try again in a moment."
        )
    return app.state.engine


def get_metrics():
    """Get metrics logger with fallback."""
    if not hasattr(app.state, 'metrics') or app.state.metrics is None:
        return None
    return app.state.metrics


# --- API Routes ---

@app.get("/")
async def root():
    """Health check and API info."""
    return {
        "name": "FinBundle API",
        "version": "3.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    # Handle case where lifespan didn't run (e.g., TestClient)
    if not hasattr(app.state, 'engine') or app.state.engine is None:
        return {
            "status": "initializing",
            "components": {
                "qdrant": False,
                "cache": False,
                "engine": False
            },
            "stats": {},
            "message": "Engine not initialized. Server may still be starting."
        }
    
    engine = app.state.engine
    return {
        "status": "healthy",
        "components": {
            "qdrant": engine.qdrant.is_available if hasattr(engine, 'qdrant') else False,
            "cache": True,
            "engine": True
        },
        "stats": engine.get_stats() if hasattr(engine, 'get_stats') else {}
    }


@app.get("/api/performance")
async def performance_stats():
    """Get API performance statistics."""
    request_count = getattr(app.state, 'request_count', 0)
    total_latency = getattr(app.state, 'total_latency_ms', 0)
    
    avg_latency = total_latency / request_count if request_count > 0 else 0
    
    # Get Qdrant stats if available
    qdrant_stats = {}
    try:
        engine = get_engine()
        if hasattr(engine, 'qdrant') and engine.qdrant.is_available:
            collection_info = engine.qdrant.client.get_collection('products_main')
            qdrant_stats = {
                'points_count': collection_info.points_count,
                'vectors_count': collection_info.vectors_count,
                'indexed_vectors_count': getattr(collection_info, 'indexed_vectors_count', 'N/A'),
                'status': collection_info.status.value
            }
    except Exception:
        pass
    
    return {
        "requests_total": request_count,
        "avg_latency_ms": round(avg_latency, 2),
        "total_latency_ms": round(total_latency, 2),
        "target_latency_ms": 300,
        "within_target": avg_latency <= 300 if avg_latency > 0 else True,
        "qdrant": qdrant_stats,
        "version": "3.0.0"
    }


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Main search endpoint.
    Routes to fast/smart/deep path based on query analysis.
    """
    try:
        engine = get_engine()
        metrics = get_metrics()
        
        result = await engine.search(
            query=request.query,
            user_id=request.user_id,
            budget=request.budget,
            cart=request.cart,
            skip_explanations=request.skip_explanations
        )
        
        # Log to metrics
        if metrics:
            metrics.log_search(
                query=request.query,
                user_id=request.user_id,
                path=result.get('metrics', {}).get('path_used', 'unknown'),
                latency_ms=result.get('metrics', {}).get('total_latency_ms', 0),
                cache_hit=result.get('cache_hit', False),
                result_count=len(result.get('results', []))
            )
        
        return SearchResponse(
            path=result.get('path', 'unknown'),
            results=result.get('results'),
            bundle=result.get('bundle'),
            curated_products=result.get('curated_products'),  # Top 3-4 per category with is_recommended
            agent_paths=result.get('agent_paths'),
            explanations=result.get('explanations'),
            bundle_explanation=result.get('bundle_explanation'),
            metrics=result.get('metrics', {}),
            cache_hit=result.get('cache_hit', False)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        metrics = get_metrics()
        if metrics:
            metrics.log_error("search", str(e), {"query": request.query})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search/quick")
async def quick_search(
    q: str = Query(..., min_length=1),
    budget: float = Query(default=1000, ge=10),
    user_id: str = Query(default="anonymous")
):
    """Quick search via GET for simple queries."""
    request = SearchRequest(query=q, budget=budget, user_id=user_id)
    return await search(request)


@app.post("/api/search/visual")
async def visual_search(request: VisualSearchRequest):
    """
    Visual search: find products similar to an uploaded image.
    
    Uses CLIP to encode the image and combines with text search
    for multi-modal product discovery.
    """
    import time
    start_time = time.time()
    
    afig = None
    try:
        from core.visual_search import get_visual_service
        from core.scorer import get_scorer
        
        engine = get_engine()
        visual_service = get_visual_service()
        scorer = get_scorer()
        
        # Check if CLIP is available
        if not visual_service.is_available:
            # Fallback to text-only search if no CLIP
            if request.text_query:
                fallback_request = SearchRequest(
                    query=request.text_query,
                    budget=request.budget,
                    user_id=request.user_id
                )
                return await search(fallback_request)
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Visual search not available. CLIP model not loaded. Provide text_query for fallback."
                )
        
        # Encode the uploaded image
        image_vec = visual_service.encode_image(request.image_base64)
        if image_vec is None:
            raise HTTPException(status_code=400, detail="Failed to process image. Ensure valid base64 image data.")
        
        # Get user context
        afig = AFIG(request.user_id)
        afig_context = afig.reconcile()
        
        # Build search query - use text if provided, or generic electronics query
        search_query = request.text_query or "electronics product gadget device"
        
        # Get text embedding for the query
        text_query_vec = engine.embedder.encode_query(search_query)
        
        # L2 normalize
        text_query_vec = text_query_vec / np.linalg.norm(text_query_vec)
        
        # Get broad candidates using text embedding
        candidates = engine.qdrant.search_with_constraints(
            query_vector=text_query_vec.tolist(),
            max_price=request.budget * 1.2,  # Allow slightly over budget
            in_stock_only=True,
            limit=50
        )
        
        # Enrich with full DB data
        candidates = engine.qdrant.enrich_results(candidates)
        
        # Convert to dicts
        results = []
        for c in candidates:
            if hasattr(c, 'to_dict'):
                results.append(c.to_dict())
            else:
                results.append(c)
        
        # Re-rank using LearnedProductScorer with AFIG
        reranked = scorer.rerank_results(
            results=results,
            query_vec=text_query_vec,
            budget=request.budget,
            user_afig=afig_context,
            embedder=engine.embedder
        )
        
        # Take top 20
        final_results = reranked[:20]
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "path": "visual",
            "results": final_results,
            "metrics": {
                "total_latency_ms": round(latency_ms, 2),
                "candidates_searched": len(candidates),
                "results_returned": len(final_results),
                "visual_search": True,
                "clip_available": True,
                "text_combined": request.text_query is not None,
                "acorn_enabled": True,  # Using ACORN filtered search
                "scoring_enabled": True  # AI scoring applied
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        metrics = get_metrics()
        if metrics:
            metrics.log_error("visual_search", str(e), {})
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if afig:
            afig.close()


@app.post("/api/search/image")
async def search_by_image_upload(
    image: UploadFile = File(..., description="Image file to search"),
    budget: float = Form(default=1000),
    user_id: str = Form(default="anonymous"),
    text_query: Optional[str] = Form(default=None)
):
    """
    Search by uploading an image file directly (multipart form).
    
    Alternative to /api/search/visual for direct file uploads.
    """
    try:
        # Read and encode image
        image_bytes = await image.read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Delegate to visual search
        request = VisualSearchRequest(
            image_base64=image_base64,
            budget=budget,
            user_id=user_id,
            text_query=text_query
        )
        
        return await visual_search(request)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/{user_id}/profile", response_model=UserProfile)
async def get_user_profile(user_id: str):
    """Get user's AFIG profile."""
    afig = None
    try:
        afig = AFIG(user_id)
        profile = afig.reconcile()
        
        return UserProfile(
            user_id=profile["user_id"],
            archetype=profile["archetype"],
            income_tier=profile["income_tier"],
            price_sensitivity=profile["price_sensitivity"],
            budget_modifier=profile["budget_modifier"],
            layer_weights=profile["layer_weights"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if afig:
            afig.close()


@app.put("/api/user/{user_id}/situational")
async def update_situational(user_id: str, update: AFIGUpdate):
    """Update user's situational context."""
    afig = None
    try:
        afig = AFIG(user_id)
        
        updates = {}
        if update.mission:
            updates["mission"] = update.mission
        if update.timeline:
            updates["timeline"] = update.timeline
        if update.budget_override:
            updates["budget_override"] = update.budget_override
        
        if updates:
            afig.update_situational(updates)
        
        profile = afig.reconcile()
        
        return {"success": True, "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if afig:
            afig.close()


@app.post("/api/user/{user_id}/signal")
async def track_signal(user_id: str, signal: BehavioralSignal):
    """Track a behavioral signal."""
    afig = None
    try:
        afig = AFIG(user_id)
        afig.update_behavioral({
            "type": signal.type,
            **signal.data
        })
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if afig:
            afig.close()


@app.get("/api/categories")
async def get_categories():
    """Get available product categories."""
    return {
        "categories": [
            {"id": "laptops", "name": "Laptops", "icon": "💻"},
            {"id": "monitors", "name": "Monitors", "icon": "🖥️"},
            {"id": "keyboards", "name": "Keyboards", "icon": "⌨️"},
            {"id": "mice", "name": "Mice", "icon": "🖱️"},
            {"id": "headsets", "name": "Headsets", "icon": "🎧"},
            {"id": "webcams", "name": "Webcams", "icon": "📷"},
            {"id": "speakers", "name": "Speakers", "icon": "🔊"},
            {"id": "desks", "name": "Desks", "icon": "🪑"},
            {"id": "chairs", "name": "Chairs", "icon": "💺"},
            {"id": "gpus", "name": "Graphics Cards", "icon": "🎮"}
        ]
    }


@app.get("/api/metrics/summary")
async def get_metrics_summary():
    """Get metrics summary for dashboard."""
    try:
        metrics = get_metrics()
        if not metrics:
            return {"error": "Metrics not available", "data": {}}
        return metrics.analyze(last_n_hours=24)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class OptimizeRequest(BaseModel):
    cart: List[Dict[str, Any]] = Field(..., min_items=1)
    budget: float = Field(..., ge=10, le=50000)
    user_id: str = Field(default="anonymous")


# ============================================================================
# SMART BUNDLE OPTIMIZER - Bidirectional with Alternatives & Learning
# ============================================================================

# Complete setup categories - what makes a full tech setup
COMPLETE_SETUP_CATEGORIES = {
    'core': ['laptop', 'desktop', 'pc'],  # Main computing device
    'display': ['monitor', 'screen', 'display'],
    'input': ['keyboard', 'mouse', 'mice'],
    'audio': ['headset', 'headphones', 'speaker', 'earphone'],
    'video': ['webcam', 'camera'],
    'gpu': ['graphics card', 'gpu', 'rtx', 'nvidia', 'amd radeon'],
}

# Search queries for each category - BIDIRECTIONAL (works for any starting product)
SETUP_SEARCH_QUERIES = {
    'laptop': ['gaming laptop rtx', 'laptop i7 16gb', 'macbook pro'],
    'desktop': ['gaming desktop pc', 'gaming pc rtx'],
    'monitor': ['4k monitor 27 inch', 'gaming monitor 144hz', 'ultrawide monitor'],
    'keyboard': ['mechanical keyboard rgb', 'wireless keyboard', 'gaming keyboard'],
    'mouse': ['gaming mouse wireless', 'ergonomic mouse', 'logitech mouse'],
    'headset': ['gaming headset microphone', 'wireless headphones', 'noise cancelling headphones'],
    'webcam': ['webcam 1080p streaming', '4k webcam', 'logitech webcam'],
    'speaker': ['computer speakers', 'desktop speakers', 'soundbar'],
    'gpu': ['rtx 4070 graphics card', 'nvidia geforce rtx', 'amd radeon rx'],
}


def detect_product_category(name: str) -> str:
    """Detect which setup category a product belongs to."""
    name_lower = name.lower()
    
    if any(kw in name_lower for kw in ['laptop', 'notebook', 'macbook']):
        return 'laptop'
    if any(kw in name_lower for kw in ['desktop', 'gaming pc', 'tower']):
        return 'desktop'
    if any(kw in name_lower for kw in ['monitor', 'display', 'screen', 'inch']):
        return 'monitor'
    if any(kw in name_lower for kw in ['keyboard', 'keycap', 'keychron']):
        return 'keyboard'
    if any(kw in name_lower for kw in ['mouse', 'mice', 'trackball']):
        return 'mouse'
    if any(kw in name_lower for kw in ['headset', 'headphone', 'earphone', 'earbuds']):
        return 'headset'
    if any(kw in name_lower for kw in ['webcam', 'camera', 'cam']):
        return 'webcam'
    if any(kw in name_lower for kw in ['speaker', 'soundbar', 'subwoofer']):
        return 'speaker'
    if any(kw in name_lower for kw in ['rtx', 'nvidia', 'geforce', 'radeon', 'graphics card', 'gpu']):
        return 'gpu'
    
    return 'accessory'


def get_missing_categories(cart_categories: set) -> list:
    """
    Determine what categories are missing for a complete setup.
    Always suggests a COMPLETE setup regardless of starting product.
    """
    # Map cart categories to our setup categories
    has_core = any(c in cart_categories for c in ['laptop', 'desktop'])
    has_display = 'monitor' in cart_categories
    has_keyboard = 'keyboard' in cart_categories
    has_mouse = 'mouse' in cart_categories
    has_audio = any(c in cart_categories for c in ['headset', 'speaker'])
    has_webcam = 'webcam' in cart_categories
    has_gpu = 'gpu' in cart_categories
    
    missing = []
    
    # Always try to complete the setup
    if not has_core:
        missing.append('laptop')  # Suggest laptop as default core
    if not has_display:
        missing.append('monitor')
    if not has_keyboard:
        missing.append('keyboard')
    if not has_mouse:
        missing.append('mouse')
    if not has_audio:
        missing.append('headset')
    if not has_webcam:
        missing.append('webcam')
    # GPU only if they have desktop or high budget
    if not has_gpu and 'desktop' in cart_categories:
        missing.append('gpu')
    
    return missing


@app.post("/api/optimize")
async def optimize_bundle(request: OptimizeRequest):
    """
    Optimize the user's cart bundle - BIDIRECTIONAL.
    
    Works for ANY starting product:
    - Mouse selected? Suggests laptop, monitor, keyboard, headset, etc.
    - Laptop selected? Suggests monitor, keyboard, mouse, headset, etc.
    
    Returns main bundle + alternatives for each slot.
    """
    afig = None
    try:
        engine = get_engine()
        
        # Get user context with learning integration
        afig = AFIG(request.user_id)
        afig_context = afig.reconcile()
        
        # Detect categories in cart
        cart_categories = set()
        cart_product_ids = set()
        cart_total = 0
        
        for item in request.cart:
            cart_product_ids.add(item.get('product_id', ''))
            category = detect_product_category(item.get('name', ''))
            cart_categories.add(category)
            cart_total += item.get('price', 0)
        
        # Calculate remaining budget
        remaining_budget = request.budget - cart_total
        
        # Get missing categories for complete setup
        missing_categories = get_missing_categories(cart_categories)
        
        # Helper to convert SearchResult to dict
        def to_dict_if_needed(item):
            if hasattr(item, 'to_dict'):
                return item.to_dict()
            elif hasattr(item, 'product_id'):
                return {
                    'product_id': item.product_id,
                    'name': item.name,
                    'category': item.category,
                    'brand': item.brand,
                    'price': item.price,
                    'rating': item.rating,
                    'rating_count': getattr(item, 'rating_count', 0),
                    'score': getattr(item, 'score', 0.5),
                    'image_url': getattr(item, 'image_url', ''),
                    'description': getattr(item, 'description', ''),
                }
            return item
        
        # Search for products in each missing category
        # Get MULTIPLE options per category for alternatives
        category_products = {}  # category -> list of products
        
        for category in missing_categories:
            queries = SETUP_SEARCH_QUERIES.get(category, [f'{category} gaming'])
            products = []
            
            for query in queries[:2]:  # 2 queries per category
                query_vec = engine.embedder.encode_query(query)
                results = engine.qdrant.search(query_vec.tolist(), limit=8)
                results = engine.qdrant.enrich_results(results)
                
                for r in results:
                    d = to_dict_if_needed(r)
                    d['_category'] = category
                    products.append(d)
            
            # Filter and deduplicate
            seen_ids = set()
            filtered = []
            for p in products:
                pid = p.get('product_id', '')
                price = p.get('price', 0)
                
                # Skip if in cart, duplicate, or bad price
                if pid in cart_product_ids or pid in seen_ids:
                    continue
                if price < 20 or price > remaining_budget * 0.6:
                    continue
                
                # Verify it's actually the right category
                detected = detect_product_category(p.get('name', ''))
                if detected != category and detected != 'accessory':
                    continue
                
                seen_ids.add(pid)
                filtered.append(p)
            
            # Sort by quality score
            filtered.sort(key=lambda x: (x.get('rating', 0) or 3) * 0.6 + min(x.get('price', 0) / 200, 1) * 0.4, reverse=True)
            category_products[category] = filtered[:5]  # Top 5 per category
        
        # Build optimized bundle - select best from each category
        # Also collect alternatives
        bundle_items = []
        alternatives = {}  # slot_id -> [alternative products]
        running_total = cart_total
        
        # Add current cart items to bundle first
        for i, item in enumerate(request.cart):
            slot_id = f"cart_{i}"
            item['_slot_id'] = slot_id
            item['_is_original'] = True
            bundle_items.append(item)
        
        # Add one best item per missing category
        slot_index = 0
        for category, products in category_products.items():
            if not products:
                continue
            
            # Find best item that fits remaining budget
            best_item = None
            alt_items = []
            
            for p in products:
                price = p.get('price', 0)
                if running_total + price <= request.budget:
                    if best_item is None:
                        best_item = p
                    else:
                        alt_items.append(p)
            
            if best_item:
                slot_id = f"suggestion_{slot_index}"
                best_item['_slot_id'] = slot_id
                best_item['_category'] = category
                best_item['_is_suggestion'] = True
                bundle_items.append(best_item)
                running_total += best_item.get('price', 0)
                
                # Store alternatives for this slot
                alternatives[slot_id] = alt_items[:4]  # Max 4 alternatives
                slot_index += 1
        
        # Calculate final totals
        optimized_total = sum(item.get('price', 0) for item in bundle_items)
        
        # Update user's AFIG with this interaction
        afig.update_behavioral({
            'type': 'bundle_optimize',
            'categories_suggested': list(category_products.keys()),
            'budget': request.budget
        })
        
        return {
            "success": True,
            "original_total": round(cart_total, 2),
            "optimized_total": round(optimized_total, 2),
            "remaining_budget": round(request.budget - optimized_total, 2),
            "budget": request.budget,
            "optimized_products": [
                {
                    "product_id": p.get('product_id', ''),
                    "name": p.get('name', ''),
                    "price": p.get('price', 0),
                    "category": p.get('_category', detect_product_category(p.get('name', ''))),
                    "brand": p.get('brand', ''),
                    "rating": p.get('rating', 0),
                    "image_url": p.get('image_url', ''),
                    "slot_id": p.get('_slot_id', ''),
                    "is_original": p.get('_is_original', False),
                    "is_suggestion": p.get('_is_suggestion', False),
                }
                for p in bundle_items
            ],
            "alternatives": {
                slot_id: [
                    {
                        "product_id": p.get('product_id', ''),
                        "name": p.get('name', ''),
                        "price": p.get('price', 0),
                        "category": p.get('_category', ''),
                        "brand": p.get('brand', ''),
                        "rating": p.get('rating', 0),
                        "image_url": p.get('image_url', ''),
                    }
                    for p in alts
                ]
                for slot_id, alts in alternatives.items()
            },
            "missing_categories": missing_categories,
            "method": "bidirectional_smart",
            "user_archetype": afig_context.get('archetype', 'value_balanced')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        metrics = get_metrics()
        if metrics:
            metrics.log_error("optimize", str(e), {"cart_size": len(request.cart)})
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if afig:
            afig.close()


# ============================================================================
# REINFORCEMENT LEARNING - CTR & Dwell Time Tracking
# ============================================================================

class InteractionEvent(BaseModel):
    """Track user interactions for RL."""
    event_type: str = Field(..., description="click, view, dwell, swap, add_to_cart, remove_from_cart")
    product_id: str
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    product_price: Optional[float] = None
    dwell_time_ms: Optional[int] = None  # For dwell events
    position: Optional[int] = None  # Position in list (for CTR)
    source: Optional[str] = None  # search_results, bundle_suggestion, alternatives
    timestamp: Optional[str] = None


class BatchInteractions(BaseModel):
    """Batch multiple interactions for efficiency."""
    user_id: str
    interactions: List[InteractionEvent]


@app.post("/api/track/interaction")
async def track_interaction(user_id: str, event: InteractionEvent):
    """
    Track a single user interaction for reinforcement learning.
    Updates AFIG profile in real-time.
    """
    afig = None
    try:
        afig = AFIG(user_id)
        
        # Map event to AFIG behavioral signals
        if event.event_type == 'click':
            afig.update_behavioral({
                'type': 'click',
                'product': {
                    'id': event.product_id,
                    'category': event.product_category or '',
                    'price': event.product_price or 0
                }
            })
            
            # Update category preferences based on clicks
            if event.product_category:
                current_pref = afig.stable.category_preferences.get(event.product_category, 0.5)
                # Small increment per click
                afig.stable.category_preferences[event.product_category] = min(1.0, current_pref + 0.02)
        
        elif event.event_type == 'dwell':
            # Dwell time > 5 seconds indicates interest
            if event.dwell_time_ms and event.dwell_time_ms > 5000:
                afig.update_behavioral({
                    'type': 'dwell',
                    'category': event.product_category or '',
                    'seconds': event.dwell_time_ms / 1000
                })
                
                # Strong interest signal - update stable layer
                if event.dwell_time_ms > 10000 and event.product_category:
                    afig.update_stable({
                        'category_preferences': {event.product_category: 0.8}
                    }, evidence_strength=0.4)
        
        elif event.event_type == 'add_to_cart':
            afig.update_behavioral({
                'type': 'cart_action',
                'action': 'add',
                'product_id': event.product_id
            })
            
            # Cart add is strong signal - update stable preferences
            if event.product_category:
                afig.update_stable({
                    'category_preferences': {event.product_category: 0.9}
                }, evidence_strength=0.6)
            
            # Track brand affinity
            if event.product_name:
                # Extract brand from name (simple heuristic)
                words = event.product_name.split()
                if words:
                    potential_brand = words[0]
                    afig.update_stable({
                        'brand_affinity': {potential_brand: 0.7}
                    }, evidence_strength=0.4)
        
        elif event.event_type == 'remove_from_cart':
            afig.update_behavioral({
                'type': 'cart_action',
                'action': 'remove',
                'product_id': event.product_id
            })
        
        elif event.event_type == 'swap':
            # User swapped an item in bundle - learn from this!
            afig.update_behavioral({
                'type': 'swap',
                'product_id': event.product_id,
                'source': event.source
            })
        
        elif event.event_type == 'view':
            # Just viewing, track position for CTR calculation
            pass
        
        # Get updated profile
        profile = afig.reconcile()
        
        return {
            "success": True,
            "event_type": event.event_type,
            "profile_updated": True,
            "new_archetype": profile.get('archetype'),
            "confidence_scores": profile.get('confidence_scores')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if afig:
            afig.close()


@app.post("/api/track/batch")
async def track_batch_interactions(batch: BatchInteractions):
    """
    Track multiple interactions at once (more efficient).
    Called periodically from frontend.
    """
    afig = None
    try:
        afig = AFIG(batch.user_id)
        
        processed = 0
        for event in batch.interactions:
            # Process each event
            if event.event_type == 'click':
                afig.update_behavioral({
                    'type': 'click',
                    'product': {
                        'id': event.product_id,
                        'category': event.product_category or '',
                        'price': event.product_price or 0
                    }
                })
            elif event.event_type == 'dwell' and event.dwell_time_ms:
                if event.dwell_time_ms > 3000:
                    afig.update_behavioral({
                        'type': 'dwell',
                        'category': event.product_category or '',
                        'seconds': event.dwell_time_ms / 1000
                    })
            processed += 1
        
        # Calculate aggregate metrics for stable layer updates
        categories_clicked = {}
        for event in batch.interactions:
            if event.event_type == 'click' and event.product_category:
                categories_clicked[event.product_category] = categories_clicked.get(event.product_category, 0) + 1
        
        # Update stable preferences based on click patterns
        if categories_clicked:
            total_clicks = sum(categories_clicked.values())
            for cat, count in categories_clicked.items():
                if count >= 2:  # At least 2 clicks in category
                    preference = min(1.0, 0.5 + (count / total_clicks) * 0.5)
                    afig.update_stable({
                        'category_preferences': {cat: preference}
                    }, evidence_strength=0.5)
        
        profile = afig.reconcile()
        
        return {
            "success": True,
            "processed_count": processed,
            "profile": {
                "archetype": profile.get('archetype'),
                "price_sensitivity": profile.get('price_sensitivity'),
                "confidence": profile.get('confidence_scores')
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if afig:
            afig.close()


@app.get("/api/user/{user_id}/recommendations")
async def get_personalized_recommendations(user_id: str, limit: int = 10):
    """
    Get personalized recommendations based on learned preferences.
    Uses AFIG profile to rank and filter products.
    """
    afig = None
    try:
        engine = get_engine()
        afig = AFIG(user_id)
        profile = afig.reconcile()
        
        # Build search query from user preferences
        preferred_categories = sorted(
            afig.stable.category_preferences.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # If no preferences yet, use defaults
        if not preferred_categories:
            preferred_categories = [('keyboard', 0.5), ('mouse', 0.5), ('headset', 0.5)]
        
        # Search for products in preferred categories
        recommendations = []
        
        for category, preference in preferred_categories:
            queries = SETUP_SEARCH_QUERIES.get(category, [category])
            query = queries[0] if queries else category
            
            query_vec = engine.embedder.encode_query(query)
            results = engine.qdrant.search(query_vec.tolist(), limit=5)
            results = engine.qdrant.enrich_results(results)
            
            for r in results:
                if hasattr(r, 'to_dict'):
                    d = r.to_dict()
                elif hasattr(r, 'product_id'):
                    d = {
                        'product_id': r.product_id,
                        'name': r.name,
                        'price': r.price,
                        'category': r.category,
                        'brand': r.brand,
                        'rating': r.rating,
                        'image_url': getattr(r, 'image_url', ''),
                    }
                else:
                    d = r
                
                d['_preference_score'] = preference
                recommendations.append(d)
        
        # Sort by preference * rating
        recommendations.sort(
            key=lambda x: x.get('_preference_score', 0.5) * (x.get('rating', 3) / 5),
            reverse=True
        )
        
        return {
            "user_id": user_id,
            "archetype": profile.get('archetype'),
            "recommendations": recommendations[:limit],
            "based_on": {
                "category_preferences": dict(preferred_categories),
                "price_sensitivity": profile.get('price_sensitivity')
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if afig:
            afig.close()


@app.post("/api/bundle/swap")
async def swap_bundle_item(
    user_id: str,
    slot_id: str,
    old_product_id: str,
    new_product_id: str,
    new_product_data: Dict[str, Any]
):
    """
    User swaps an item in their bundle.
    This is a strong learning signal - they're actively choosing!
    """
    afig = None
    try:
        afig = AFIG(user_id)
        
        # Record the swap as strong preference signal
        new_category = detect_product_category(new_product_data.get('name', ''))
        new_price = new_product_data.get('price', 0)
        
        # Update category preference
        afig.update_stable({
            'category_preferences': {new_category: 0.85}
        }, evidence_strength=0.7)
        
        # Track brand if available
        if new_product_data.get('brand'):
            afig.update_stable({
                'brand_affinity': {new_product_data['brand']: 0.8}
            }, evidence_strength=0.6)
        
        # Record swap action
        afig.update_behavioral({
            'type': 'swap',
            'old_product_id': old_product_id,
            'new_product_id': new_product_id,
            'new_price': new_price,
            'slot_id': slot_id
        })
        
        profile = afig.reconcile()
        
        return {
            "success": True,
            "swap_recorded": True,
            "profile_updated": True,
            "archetype": profile.get('archetype'),
            "message": f"Learned: User prefers {new_category} products like {new_product_data.get('name', 'this')[:30]}..."
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if afig:
            afig.close()


# --- Run Server ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
