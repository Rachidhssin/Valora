"""
Success Indicators Analytics Module
====================================

Tracks and analyzes key success metrics for FinBundle:
1. CTR (Click-through Rate) - % of shown products that get clicked
2. Add-to-Cart Rate - % of clicks that result in cart adds
3. Constraint Compliance - % of recommendations within budget
4. Faster Product Finding - Time to first click, session duration

Usage:
------
    from core.success_indicators import get_indicators, track_impression, track_click
    
    # Track when products are shown
    track_impression(session_id, product_ids, budget, query)
    
    # Track when user clicks a product
    track_click(session_id, product_id, position, price, budget)
    
    # Track when user adds to cart
    track_cart_add(session_id, product_id, price, budget)
    
    # Get analytics dashboard
    dashboard = get_indicators().get_dashboard()
"""

import json
import time
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class Impression:
    """Tracks a single product impression (shown to user)."""
    session_id: str
    product_id: str
    position: int  # 0 = top result
    price: float
    budget: float
    query: str
    timestamp: str
    within_budget: bool


@dataclass
class Click:
    """Tracks a click on a product."""
    session_id: str
    product_id: str
    position: int
    price: float
    budget: float
    timestamp: str
    time_to_click_ms: float  # Time from search to click


@dataclass
class CartAdd:
    """Tracks adding a product to cart."""
    session_id: str
    product_id: str
    price: float
    budget: float
    timestamp: str
    is_recommended: bool  # Was this an AI recommendation?


@dataclass
class SearchSession:
    """Tracks a complete search session."""
    session_id: str
    user_id: str
    query: str
    budget: float
    start_time: str
    first_click_time: Optional[str]
    cart_add_time: Optional[str]
    results_count: int
    path_used: str
    latency_ms: float


class SuccessIndicators:
    """
    Comprehensive success metrics tracking for FinBundle.
    
    Key Metrics:
    - CTR: clicks / impressions
    - Cart Rate: cart_adds / clicks
    - Conversion Rate: cart_adds / impressions
    - Constraint Compliance: within_budget_recommendations / total_recommendations
    - Time to First Click: average time from search to first interaction
    - Time to Cart: average time from search to cart add
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Event log files
        self.impressions_file = self.data_dir / "impressions.jsonl"
        self.clicks_file = self.data_dir / "clicks.jsonl"
        self.cart_adds_file = self.data_dir / "cart_adds.jsonl"
        self.sessions_file = self.data_dir / "search_sessions.jsonl"
        
        # In-memory tracking for active sessions
        self._active_sessions: Dict[str, SearchSession] = {}
        self._session_impressions: Dict[str, List[Impression]] = defaultdict(list)
        
    # =========================================================================
    # EVENT TRACKING
    # =========================================================================
    
    def start_session(self, session_id: str, user_id: str, query: str, 
                      budget: float, results_count: int, path: str, 
                      latency_ms: float) -> str:
        """Start tracking a new search session."""
        session = SearchSession(
            session_id=session_id,
            user_id=user_id,
            query=query,
            budget=budget,
            start_time=datetime.now().isoformat(),
            first_click_time=None,
            cart_add_time=None,
            results_count=results_count,
            path_used=path,
            latency_ms=latency_ms
        )
        
        self._active_sessions[session_id] = session
        return session_id
    
    def track_impressions(self, session_id: str, products: List[Dict], 
                          budget: float, query: str):
        """
        Track product impressions (products shown to user).
        
        Args:
            session_id: Current session
            products: List of products shown (with product_id, price)
            budget: User's budget
            query: Search query
        """
        timestamp = datetime.now().isoformat()
        
        for position, product in enumerate(products):
            price = product.get('price', 0)
            impression = Impression(
                session_id=session_id,
                product_id=product.get('product_id', ''),
                position=position,
                price=price,
                budget=budget,
                query=query,
                timestamp=timestamp,
                within_budget=price <= budget
            )
            
            self._session_impressions[session_id].append(impression)
            self._write_event(self.impressions_file, asdict(impression))
    
    def track_click(self, session_id: str, product_id: str, 
                    position: int, price: float, budget: float) -> Dict:
        """
        Track a product click.
        
        Returns click metrics for the frontend.
        """
        now = datetime.now()
        timestamp = now.isoformat()
        
        # Calculate time to click
        time_to_click_ms = 0
        if session_id in self._active_sessions:
            session = self._active_sessions[session_id]
            start = datetime.fromisoformat(session.start_time)
            time_to_click_ms = (now - start).total_seconds() * 1000
            
            # Update first click time
            if session.first_click_time is None:
                session.first_click_time = timestamp
        
        click = Click(
            session_id=session_id,
            product_id=product_id,
            position=position,
            price=price,
            budget=budget,
            timestamp=timestamp,
            time_to_click_ms=time_to_click_ms
        )
        
        self._write_event(self.clicks_file, asdict(click))
        
        return {
            "tracked": True,
            "time_to_click_ms": time_to_click_ms,
            "within_budget": price <= budget,
            "position": position
        }
    
    def track_cart_add(self, session_id: str, product_id: str, 
                       price: float, budget: float, 
                       is_recommended: bool = False) -> Dict:
        """
        Track adding a product to cart.
        """
        now = datetime.now()
        timestamp = now.isoformat()
        
        # Update session
        if session_id in self._active_sessions:
            session = self._active_sessions[session_id]
            if session.cart_add_time is None:
                session.cart_add_time = timestamp
        
        cart_add = CartAdd(
            session_id=session_id,
            product_id=product_id,
            price=price,
            budget=budget,
            timestamp=timestamp,
            is_recommended=is_recommended
        )
        
        self._write_event(self.cart_adds_file, asdict(cart_add))
        
        return {
            "tracked": True,
            "within_budget": price <= budget,
            "is_recommended": is_recommended
        }
    
    def end_session(self, session_id: str):
        """End and save a search session."""
        if session_id in self._active_sessions:
            session = self._active_sessions[session_id]
            self._write_event(self.sessions_file, asdict(session))
            
            del self._active_sessions[session_id]
            if session_id in self._session_impressions:
                del self._session_impressions[session_id]
    
    def _write_event(self, file_path: Path, data: Dict):
        """Append event to JSONL file."""
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
    
    # =========================================================================
    # ANALYTICS CALCULATIONS
    # =========================================================================
    
    def calculate_ctr(self, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate Click-Through Rate.
        
        CTR = clicks / impressions
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        impressions = self._read_events(self.impressions_file, cutoff)
        clicks = self._read_events(self.clicks_file, cutoff)
        
        total_impressions = len(impressions)
        total_clicks = len(clicks)
        
        if total_impressions == 0:
            return {"ctr": 0, "impressions": 0, "clicks": 0, "message": "No data"}
        
        ctr = (total_clicks / total_impressions) * 100
        
        # CTR by position (are top results clicked more?)
        position_clicks = defaultdict(int)
        position_impressions = defaultdict(int)
        
        for imp in impressions:
            pos = min(imp.get('position', 0), 9)  # Group 10+ into "10"
            position_impressions[pos] += 1
        
        for click in clicks:
            pos = min(click.get('position', 0), 9)
            position_clicks[pos] += 1
        
        position_ctr = {}
        for pos in range(10):
            if position_impressions[pos] > 0:
                position_ctr[f"pos_{pos}"] = round(
                    (position_clicks[pos] / position_impressions[pos]) * 100, 2
                )
        
        return {
            "ctr": round(ctr, 2),
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ctr_by_position": position_ctr,
            "period_hours": hours
        }
    
    def calculate_cart_rate(self, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate Add-to-Cart Rate.
        
        Cart Rate = cart_adds / clicks
        Conversion Rate = cart_adds / impressions
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        impressions = self._read_events(self.impressions_file, cutoff)
        clicks = self._read_events(self.clicks_file, cutoff)
        cart_adds = self._read_events(self.cart_adds_file, cutoff)
        
        total_impressions = len(impressions)
        total_clicks = len(clicks)
        total_cart_adds = len(cart_adds)
        
        # Calculate rates
        cart_rate = (total_cart_adds / total_clicks * 100) if total_clicks > 0 else 0
        conversion_rate = (total_cart_adds / total_impressions * 100) if total_impressions > 0 else 0
        
        # Cart adds from recommendations vs organic
        recommended_adds = sum(1 for ca in cart_adds if ca.get('is_recommended', False))
        organic_adds = total_cart_adds - recommended_adds
        
        return {
            "cart_rate": round(cart_rate, 2),  # clicks -> cart
            "conversion_rate": round(conversion_rate, 2),  # impressions -> cart
            "total_clicks": total_clicks,
            "total_cart_adds": total_cart_adds,
            "recommended_cart_adds": recommended_adds,
            "organic_cart_adds": organic_adds,
            "recommendation_effectiveness": round(
                (recommended_adds / total_cart_adds * 100) if total_cart_adds > 0 else 0, 2
            ),
            "period_hours": hours
        }
    
    def calculate_constraint_compliance(self, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate Constraint Compliance.
        
        Compliance = recommendations_within_budget / total_recommendations
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        impressions = self._read_events(self.impressions_file, cutoff)
        clicks = self._read_events(self.clicks_file, cutoff)
        cart_adds = self._read_events(self.cart_adds_file, cutoff)
        
        # Impressions compliance
        total_impressions = len(impressions)
        within_budget_impressions = sum(1 for imp in impressions if imp.get('within_budget', False))
        impression_compliance = (within_budget_impressions / total_impressions * 100) if total_impressions > 0 else 100
        
        # Clicks compliance (did users click within-budget items?)
        total_clicks = len(clicks)
        within_budget_clicks = sum(
            1 for c in clicks 
            if c.get('price', 0) <= c.get('budget', float('inf'))
        )
        click_compliance = (within_budget_clicks / total_clicks * 100) if total_clicks > 0 else 100
        
        # Cart compliance (did users add within-budget items?)
        total_adds = len(cart_adds)
        within_budget_adds = sum(
            1 for ca in cart_adds 
            if ca.get('price', 0) <= ca.get('budget', float('inf'))
        )
        cart_compliance = (within_budget_adds / total_adds * 100) if total_adds > 0 else 100
        
        # Over-budget recommendations (products shown above budget)
        over_budget = total_impressions - within_budget_impressions
        over_budget_rate = (over_budget / total_impressions * 100) if total_impressions > 0 else 0
        
        return {
            "impression_compliance": round(impression_compliance, 2),
            "click_compliance": round(click_compliance, 2),
            "cart_compliance": round(cart_compliance, 2),
            "overall_compliance": round(
                (impression_compliance + click_compliance + cart_compliance) / 3, 2
            ),
            "over_budget_rate": round(over_budget_rate, 2),
            "total_impressions": total_impressions,
            "within_budget_impressions": within_budget_impressions,
            "period_hours": hours
        }
    
    def calculate_speed_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Calculate Faster Product Finding metrics.
        
        - Time to First Click: How quickly users find what they want
        - Time to Cart: How quickly users convert
        - Search Latency: How fast results appear
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        
        clicks = self._read_events(self.clicks_file, cutoff)
        sessions = self._read_events(self.sessions_file, cutoff)
        
        # Time to first click
        first_click_times = [c.get('time_to_click_ms', 0) for c in clicks if c.get('time_to_click_ms')]
        avg_time_to_click = sum(first_click_times) / len(first_click_times) if first_click_times else 0
        
        # Time to cart (from session start)
        cart_times = []
        for session in sessions:
            if session.get('cart_add_time') and session.get('start_time'):
                try:
                    start = datetime.fromisoformat(session['start_time'])
                    cart = datetime.fromisoformat(session['cart_add_time'])
                    cart_times.append((cart - start).total_seconds() * 1000)
                except:
                    pass
        
        avg_time_to_cart = sum(cart_times) / len(cart_times) if cart_times else 0
        
        # Search latency
        latencies = [s.get('latency_ms', 0) for s in sessions if s.get('latency_ms')]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        # Latency by path
        path_latencies = defaultdict(list)
        for s in sessions:
            path = s.get('path_used', 'unknown')
            if s.get('latency_ms'):
                path_latencies[path].append(s['latency_ms'])
        
        latency_by_path = {
            path: round(sum(lats) / len(lats), 2) 
            for path, lats in path_latencies.items()
        }
        
        return {
            "avg_time_to_first_click_ms": round(avg_time_to_click, 2),
            "avg_time_to_cart_ms": round(avg_time_to_cart, 2),
            "avg_search_latency_ms": round(avg_latency, 2),
            "latency_by_path": latency_by_path,
            "total_sessions": len(sessions),
            "sessions_with_clicks": len(first_click_times),
            "sessions_with_cart": len(cart_times),
            "period_hours": hours
        }
    
    def _read_events(self, file_path: Path, cutoff: datetime) -> List[Dict]:
        """Read events from JSONL file filtered by time."""
        if not file_path.exists():
            return []
        
        events = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    timestamp = datetime.fromisoformat(event.get('timestamp', '1970-01-01'))
                    if timestamp >= cutoff:
                        events.append(event)
                except (json.JSONDecodeError, ValueError):
                    continue
        
        return events
    
    # =========================================================================
    # DASHBOARD
    # =========================================================================
    
    def get_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get complete success indicators dashboard.
        
        Returns all metrics for the specified time period.
        """
        return {
            "generated_at": datetime.now().isoformat(),
            "period_hours": hours,
            "engagement": {
                "ctr": self.calculate_ctr(hours),
                "cart_rate": self.calculate_cart_rate(hours)
            },
            "constraint_compliance": self.calculate_constraint_compliance(hours),
            "speed_metrics": self.calculate_speed_metrics(hours),
            "summary": self._generate_summary(hours)
        }
    
    def _generate_summary(self, hours: int) -> Dict[str, Any]:
        """Generate a human-readable summary of success indicators."""
        ctr = self.calculate_ctr(hours)
        cart = self.calculate_cart_rate(hours)
        compliance = self.calculate_constraint_compliance(hours)
        speed = self.calculate_speed_metrics(hours)
        
        # Score each metric (0-100)
        scores = {
            "engagement_score": min(100, (ctr.get('ctr', 0) * 5)),  # 20% CTR = 100
            "conversion_score": min(100, (cart.get('cart_rate', 0) * 2)),  # 50% cart rate = 100
            "compliance_score": compliance.get('overall_compliance', 0),  # Already 0-100
            "speed_score": max(0, 100 - (speed.get('avg_search_latency_ms', 300) / 3))  # 300ms = 0, 0ms = 100
        }
        
        overall = sum(scores.values()) / len(scores)
        
        return {
            "scores": scores,
            "overall_score": round(overall, 2),
            "rating": self._get_rating(overall),
            "insights": self._generate_insights(ctr, cart, compliance, speed)
        }
    
    def _get_rating(self, score: float) -> str:
        """Convert score to star rating."""
        if score >= 90:
            return "⭐⭐⭐⭐⭐ Excellent"
        elif score >= 75:
            return "⭐⭐⭐⭐ Great"
        elif score >= 60:
            return "⭐⭐⭐ Good"
        elif score >= 40:
            return "⭐⭐ Needs Improvement"
        else:
            return "⭐ Poor"
    
    def _generate_insights(self, ctr: Dict, cart: Dict, 
                           compliance: Dict, speed: Dict) -> List[str]:
        """Generate actionable insights from metrics."""
        insights = []
        
        # CTR insights
        if ctr.get('ctr', 0) < 5:
            insights.append("⚠️ Low CTR: Consider improving result relevance or UI visibility")
        elif ctr.get('ctr', 0) > 20:
            insights.append("✅ Strong CTR: Users are finding relevant products")
        
        # Position CTR
        pos_ctr = ctr.get('ctr_by_position', {})
        if pos_ctr.get('pos_0', 0) < pos_ctr.get('pos_1', 0):
            insights.append("📊 Top result isn't clicked most - ranking may need adjustment")
        
        # Cart rate
        if cart.get('cart_rate', 0) < 10:
            insights.append("🛒 Low cart rate: Users click but don't add - check pricing or details")
        
        # Recommendation effectiveness
        if cart.get('recommendation_effectiveness', 0) > 50:
            insights.append("✅ Recommendations drive >50% of cart adds")
        
        # Compliance
        if compliance.get('over_budget_rate', 0) > 20:
            insights.append("💰 20%+ recommendations are over-budget - tighten filters")
        elif compliance.get('over_budget_rate', 0) < 5:
            insights.append("✅ Excellent budget compliance (<5% over-budget)")
        
        # Speed
        if speed.get('avg_search_latency_ms', 0) > 500:
            insights.append("🐌 Search is slow (>500ms) - optimize queries")
        elif speed.get('avg_search_latency_ms', 0) < 200:
            insights.append("⚡ Excellent search speed (<200ms)")
        
        if speed.get('avg_time_to_first_click_ms', 0) > 10000:
            insights.append("⏱️ Users take >10s to click - results may not be relevant")
        
        if not insights:
            insights.append("📈 Metrics look healthy - keep monitoring")
        
        return insights
    
    def print_dashboard(self, hours: int = 24):
        """Print a formatted dashboard to console."""
        dashboard = self.get_dashboard(hours)
        
        print("\n" + "=" * 60)
        print("📊 FINBUNDLE SUCCESS INDICATORS DASHBOARD")
        print("=" * 60)
        print(f"Period: Last {hours} hours")
        print(f"Generated: {dashboard['generated_at'][:19]}")
        
        # Engagement
        print("\n🎯 ENGAGEMENT METRICS")
        print("-" * 40)
        ctr = dashboard['engagement']['ctr']
        cart = dashboard['engagement']['cart_rate']
        print(f"  CTR: {ctr.get('ctr', 0)}% ({ctr.get('clicks', 0)}/{ctr.get('impressions', 0)})")
        print(f"  Cart Rate: {cart.get('cart_rate', 0)}%")
        print(f"  Conversion Rate: {cart.get('conversion_rate', 0)}%")
        
        # Compliance
        print("\n💰 CONSTRAINT COMPLIANCE")
        print("-" * 40)
        comp = dashboard['constraint_compliance']
        print(f"  Recommendation Compliance: {comp.get('impression_compliance', 0)}%")
        print(f"  Over-Budget Rate: {comp.get('over_budget_rate', 0)}%")
        print(f"  Overall Compliance: {comp.get('overall_compliance', 0)}%")
        
        # Speed
        print("\n⚡ SPEED METRICS")
        print("-" * 40)
        speed = dashboard['speed_metrics']
        print(f"  Avg Search Latency: {speed.get('avg_search_latency_ms', 0):.0f}ms")
        print(f"  Avg Time to Click: {speed.get('avg_time_to_first_click_ms', 0):.0f}ms")
        print(f"  Avg Time to Cart: {speed.get('avg_time_to_cart_ms', 0):.0f}ms")
        
        # Summary
        print("\n📈 OVERALL SUMMARY")
        print("-" * 40)
        summary = dashboard['summary']
        print(f"  Overall Score: {summary.get('overall_score', 0)}")
        print(f"  Rating: {summary.get('rating', 'N/A')}")
        
        print("\n💡 INSIGHTS:")
        for insight in summary.get('insights', []):
            print(f"  {insight}")
        
        print("\n" + "=" * 60)


# =============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# =============================================================================

_indicators_instance = None


def get_indicators() -> SuccessIndicators:
    """Get singleton SuccessIndicators instance."""
    global _indicators_instance
    if _indicators_instance is None:
        _indicators_instance = SuccessIndicators()
    return _indicators_instance


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def track_search(session_id: str, user_id: str, query: str, budget: float,
                 results: List[Dict], path: str, latency_ms: float):
    """
    Convenience function to track a complete search event.
    
    Call this after returning search results to the user.
    """
    indicators = get_indicators()
    
    # Start session
    indicators.start_session(
        session_id=session_id,
        user_id=user_id,
        query=query,
        budget=budget,
        results_count=len(results),
        path=path,
        latency_ms=latency_ms
    )
    
    # Track impressions
    indicators.track_impressions(
        session_id=session_id,
        products=results,
        budget=budget,
        query=query
    )


def track_click(session_id: str, product_id: str, position: int,
                price: float, budget: float) -> Dict:
    """Convenience function to track a click."""
    return get_indicators().track_click(
        session_id=session_id,
        product_id=product_id,
        position=position,
        price=price,
        budget=budget
    )


def track_cart_add(session_id: str, product_id: str, price: float,
                   budget: float, is_recommended: bool = False) -> Dict:
    """Convenience function to track a cart add."""
    return get_indicators().track_cart_add(
        session_id=session_id,
        product_id=product_id,
        price=price,
        budget=budget,
        is_recommended=is_recommended
    )


# =============================================================================
# DEMO / TEST
# =============================================================================

if __name__ == "__main__":
    print("🧪 Testing Success Indicators...")
    
    indicators = SuccessIndicators()
    
    # Simulate a user session
    session_id = generate_session_id()
    
    # 1. User searches
    print("\n1️⃣ Simulating search...")
    products = [
        {"product_id": "laptop-1", "price": 999.99},
        {"product_id": "laptop-2", "price": 1299.99},
        {"product_id": "laptop-3", "price": 799.99},
        {"product_id": "laptop-4", "price": 1599.99},  # Over budget
        {"product_id": "laptop-5", "price": 899.99},
    ]
    
    track_search(
        session_id=session_id,
        user_id="demo_user",
        query="gaming laptop",
        budget=1200,
        results=products,
        path="smart",
        latency_ms=185.5
    )
    print(f"   ✅ Tracked {len(products)} impressions")
    
    # 2. User clicks a product
    print("\n2️⃣ Simulating click...")
    import time
    time.sleep(0.5)  # Simulate user thinking
    
    result = track_click(
        session_id=session_id,
        product_id="laptop-1",
        position=0,
        price=999.99,
        budget=1200
    )
    print(f"   ✅ Click tracked: {result}")
    
    # 3. User adds to cart
    print("\n3️⃣ Simulating cart add...")
    time.sleep(0.3)
    
    result = track_cart_add(
        session_id=session_id,
        product_id="laptop-1",
        price=999.99,
        budget=1200,
        is_recommended=True
    )
    print(f"   ✅ Cart add tracked: {result}")
    
    # End session
    indicators.end_session(session_id)
    
    # Print dashboard
    print("\n4️⃣ Generating dashboard...")
    indicators.print_dashboard(hours=1)
    
    print("\n✅ Success Indicators test complete!")
