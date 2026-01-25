"""
FinBundle FastAPI Backend
RESTful API for the React frontend
"""
import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
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
from core.metrics import get_metrics_logger


# --- Pydantic Models ---

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    budget: float = Field(..., ge=10, le=50000)
    user_id: str = Field(default="anonymous")
    cart: List[Dict[str, Any]] = Field(default_factory=list)
    skip_explanations: bool = Field(default=False, description="Skip slow LLM explanations for faster response")


class SearchResponse(BaseModel):
    path: str
    results: Optional[List[Dict]] = None
    bundle: Optional[Dict] = None
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
    engine = app.state.engine
    return {
        "status": "healthy",
        "components": {
            "qdrant": engine.qdrant.is_available,
            "cache": True,
            "engine": True
        },
        "stats": engine.get_stats()
    }


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Main search endpoint.
    Routes to fast/smart/deep path based on query analysis.
    """
    try:
        engine = app.state.engine
        
        result = await engine.search(
            query=request.query,
            user_id=request.user_id,
            budget=request.budget,
            cart=request.cart,
            skip_explanations=request.skip_explanations
        )
        
        # Log to metrics
        app.state.metrics.log_search(
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
            agent_paths=result.get('agent_paths'),
            explanations=result.get('explanations'),
            bundle_explanation=result.get('bundle_explanation'),
            metrics=result.get('metrics', {}),
            cache_hit=result.get('cache_hit', False)
        )
        
    except Exception as e:
        app.state.metrics.log_error("search", str(e), {"query": request.query})
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


@app.get("/api/user/{user_id}/profile", response_model=UserProfile)
async def get_user_profile(user_id: str):
    """Get user's AFIG profile."""
    try:
        afig = AFIG(user_id)
        profile = afig.reconcile()
        afig.close()
        
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


@app.put("/api/user/{user_id}/situational")
async def update_situational(user_id: str, update: AFIGUpdate):
    """Update user's situational context."""
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
        afig.close()
        
        return {"success": True, "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/user/{user_id}/signal")
async def track_signal(user_id: str, signal: BehavioralSignal):
    """Track a behavioral signal."""
    try:
        afig = AFIG(user_id)
        afig.update_behavioral({
            "type": signal.type,
            **signal.data
        })
        afig.close()
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        metrics = app.state.metrics
        return metrics.analyze(last_n_hours=24)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Run Server ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
