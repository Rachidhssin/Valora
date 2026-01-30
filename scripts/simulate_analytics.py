"""
Simulate User Sessions for Analytics Testing
=============================================

This script simulates realistic user behavior to populate the
success indicators with test data.

Usage:
    python scripts/simulate_analytics.py --sessions 50
"""

import argparse
import random
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.success_indicators import (
    SuccessIndicators, generate_session_id, track_search,
    track_click, track_cart_add
)


def simulate_user_session(indicators: SuccessIndicators, 
                          session_num: int,
                          realistic: bool = True):
    """
    Simulate a single user session with realistic behavior.
    
    Realistic patterns:
    - 60% of users click at least one product
    - 30% of clickers add to cart
    - Users prefer products within budget
    - Time to click varies (faster for relevant results)
    """
    session_id = generate_session_id()
    user_id = f"simulated_user_{session_num}"
    
    # Random budget between $100 and $5000
    budget = random.choice([500, 1000, 1500, 2000, 3000, 5000])
    
    # Random query
    queries = [
        "gaming laptop",
        "wireless headphones",
        "4k monitor",
        "mechanical keyboard",
        "gaming mouse",
        "rtx 4080 graphics card",
        "standing desk",
        "ergonomic chair",
        "webcam 1080p",
        "usb-c hub",
        "ssd 1tb",
        "gaming setup bundle"
    ]
    query = random.choice(queries)
    
    # Random search path
    paths = ["fast", "smart", "deep"]
    path_weights = [0.2, 0.6, 0.2]  # Smart path most common
    path = random.choices(paths, weights=path_weights)[0]
    
    # Random latency based on path
    latencies = {"fast": 50, "smart": 180, "deep": 600}
    latency = latencies[path] + random.randint(-20, 50)
    
    # Generate mock products
    num_products = random.randint(5, 20)
    products = []
    
    for i in range(num_products):
        # Mix of within and over budget
        if random.random() < 0.85:  # 85% within budget
            price = random.uniform(budget * 0.3, budget * 0.95)
        else:
            price = random.uniform(budget * 1.05, budget * 1.5)
        
        products.append({
            "product_id": f"product_{session_num}_{i}",
            "price": round(price, 2),
            "name": f"Product {i} for {query}"
        })
    
    # Track impressions
    track_search(
        session_id=session_id,
        user_id=user_id,
        query=query,
        budget=budget,
        results=products,
        path=path,
        latency_ms=latency
    )
    
    # Simulate user behavior
    will_click = random.random() < 0.60  # 60% click rate
    
    if will_click:
        # Simulate time thinking (0.5s - 10s)
        time.sleep(random.uniform(0.01, 0.1))  # Shortened for simulation
        
        # Click 1-3 products
        num_clicks = random.randint(1, min(3, len(products)))
        
        # Users prefer clicking top results and within-budget items
        click_weights = []
        for i, p in enumerate(products):
            weight = 1 / (i + 1)  # Position bias
            if p["price"] <= budget:
                weight *= 2  # Prefer within-budget
            click_weights.append(weight)
        
        # Normalize weights
        total_weight = sum(click_weights)
        click_probs = [w / total_weight for w in click_weights]
        
        clicked_indices = set()
        for _ in range(num_clicks):
            idx = random.choices(range(len(products)), weights=click_probs)[0]
            if idx not in clicked_indices:
                clicked_indices.add(idx)
                product = products[idx]
                
                track_click(
                    session_id=session_id,
                    product_id=product["product_id"],
                    position=idx,
                    price=product["price"],
                    budget=budget
                )
        
        # Some clickers add to cart
        will_cart = random.random() < 0.30  # 30% of clickers add to cart
        
        if will_cart and clicked_indices:
            time.sleep(random.uniform(0.01, 0.05))  # Thinking time
            
            # Usually add the first clicked product
            cart_idx = list(clicked_indices)[0]
            product = products[cart_idx]
            
            track_cart_add(
                session_id=session_id,
                product_id=product["product_id"],
                price=product["price"],
                budget=budget,
                is_recommended=True
            )
    
    # End session
    indicators.end_session(session_id)
    
    return {
        "session_id": session_id,
        "clicked": will_click,
        "carted": will_click and will_cart,
        "budget": budget,
        "query": query
    }


def main():
    parser = argparse.ArgumentParser(description="Simulate analytics data")
    parser.add_argument("--sessions", type=int, default=50, 
                        help="Number of sessions to simulate")
    parser.add_argument("--fast", action="store_true",
                        help="Skip sleep delays for faster simulation")
    args = parser.parse_args()
    
    print("📊 Analytics Simulation")
    print("=" * 50)
    print(f"Simulating {args.sessions} user sessions...")
    
    indicators = SuccessIndicators()
    
    stats = {
        "total": 0,
        "clicked": 0,
        "carted": 0
    }
    
    for i in range(args.sessions):
        result = simulate_user_session(indicators, i)
        stats["total"] += 1
        if result["clicked"]:
            stats["clicked"] += 1
        if result["carted"]:
            stats["carted"] += 1
        
        # Progress indicator
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{args.sessions} sessions")
    
    print("\n" + "=" * 50)
    print("✅ Simulation Complete!")
    print(f"  Sessions: {stats['total']}")
    print(f"  Sessions with clicks: {stats['clicked']} ({stats['clicked']/stats['total']*100:.1f}%)")
    print(f"  Sessions with carts: {stats['carted']} ({stats['carted']/stats['total']*100:.1f}%)")
    
    # Show dashboard
    print("\n" + "=" * 50)
    print("📈 Generated Dashboard:")
    indicators.print_dashboard(hours=1)


if __name__ == "__main__":
    main()
