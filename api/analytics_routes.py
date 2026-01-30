"""
Analytics Routes
================
API endpoints for tracking success indicators.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from core.success_indicators import get_indicators

router = APIRouter(prefix="/analytics", tags=["analytics"])

# --- Pydantic Models ---

class SessionCreateRequest(BaseModel):
    user_id: str = "anonymous"
    query: Optional[str] = None
    budget: Optional[float] = None
    path: Optional[str] = None
    latency_ms: Optional[float] = None
    results_count: Optional[int] = 0

class ImpressionRequest(BaseModel):
    session_id: str
    products: List[Dict[str, Any]]
    budget: float
    query: str
    path: str = "unknown"
    latency_ms: float = 0
    user_id: str = "anonymous"

class ClickRequest(BaseModel):
    session_id: str
    product_id: str
    position: int
    price: float
    budget: float

class CartRequest(BaseModel):
    session_id: str
    product_id: str
    price: float
    budget: float
    is_recommended: bool = False

# --- Endpoints ---

@router.post("/session")
async def create_session(request: Optional[SessionCreateRequest] = None):
    """Start a new analytics session."""
    try:
        from core.success_indicators import generate_session_id
        session_id = generate_session_id()
        
        # If initial data provided, track it
        if request and request.query:
            get_indicators().start_session(
                session_id=session_id,
                user_id=request.user_id,
                query=request.query,
                budget=request.budget or 0,
                results_count=request.results_count or 0,
                path=request.path or "unknown",
                latency_ms=request.latency_ms or 0
            )
            
        return {"session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session/{session_id}/end")
async def end_session(session_id: str):
    """End a session."""
    try:
        get_indicators().end_session(session_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/track/impression")
async def track_impression(request: ImpressionRequest):
    """Track product impressions."""
    try:
        # Ensure session exists (lazy create if needed, though strictly we should have one)
        indicators = get_indicators()
        
        # If session not active, we might miss start_session call, 
        # but we can still track the impression linked to the ID.
        
        indicators.track_impressions(
            session_id=request.session_id,
            products=request.products,
            budget=request.budget,
            query=request.query
        )
        
        # Calculate immediate compliance for feedback
        total = len(request.products)
        within = sum(1 for p in request.products if p.get('price', 0) <= request.budget)
        compliance = (within / total * 100) if total > 0 else 100
        
        return {
            "success": True, 
            "impressions_count": total,
            "compliance_rate": round(compliance, 1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/track/click")
async def track_click(request: ClickRequest):
    """Track a product click."""
    try:
        result = get_indicators().track_click(
            session_id=request.session_id,
            product_id=request.product_id,
            position=request.position,
            price=request.price,
            budget=request.budget
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/track/cart")
async def track_cart(request: CartRequest):
    """Track add to cart."""
    try:
        result = get_indicators().track_cart_add(
            session_id=request.session_id,
            product_id=request.product_id,
            price=request.price,
            budget=request.budget,
            is_recommended=request.is_recommended
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard")
async def get_dashboard(hours: int = 24):
    """Get the full analytics dashboard."""
    try:
        return get_indicators().get_dashboard(hours=hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{metric}")
async def get_metric(metric: str, hours: int = 24):
    """Get a specific high-level metric."""
    try:
        indicators = get_indicators()
        
        if metric == "ctr":
            return indicators.calculate_ctr(hours)
        elif metric == "cart-rate":
            return indicators.calculate_cart_rate(hours)
        elif metric == "compliance":
            return indicators.calculate_constraint_compliance(hours)
        elif metric == "speed":
            return indicators.calculate_speed_metrics(hours)
        else:
            raise HTTPException(status_code=404, detail=f"Metric '{metric}' not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
