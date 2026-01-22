"""
Demo Scenarios for FinBundle
Pre-defined scenarios for presentations and testing
"""
import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


DEMO_SCENARIOS = [
    {
        "name": "🎮 Gaming Setup",
        "description": "Complete gaming setup for an enthusiast with a decent budget",
        "query": "complete gaming setup with laptop monitor and accessories",
        "user_id": "demo_gamer",
        "budget": 2000,
        "expected_path": "deep",
        "talking_points": [
            "Shows bundle optimization with multiple categories",
            "Demonstrates MILP optimizer selecting complementary items",
            "Agent finds alternatives if over budget"
        ]
    },
    {
        "name": "💼 Budget Laptop",
        "description": "Student looking for an affordable laptop",
        "query": "cheap laptop for students under 600",
        "user_id": "demo_student",
        "budget": 600,
        "expected_path": "smart",
        "talking_points": [
            "Quick smart path for single-item search",
            "Feasibility gate filters to budget",
            "Shows budget-conscious archetype matching"
        ]
    },
    {
        "name": "🏠 Home Office",
        "description": "Remote worker setting up a home office",
        "query": "home office desk chair and monitor",
        "user_id": "demo_remote",
        "budget": 1200,
        "expected_path": "deep",
        "talking_points": [
            "Multi-category bundle optimization",
            "Ergonomic category gets proper weighting",
            "Shows value-balanced archetype"
        ]
    },
    {
        "name": "⚡ Quick Search",
        "description": "Simple category browse",
        "query": "keyboards",
        "user_id": "demo_quick",
        "budget": 500,
        "expected_path": "fast",
        "talking_points": [
            "Demonstrates fast path (<100ms target)",
            "Precomputed/cached results",
            "Good for showing three-path routing decision"
        ]
    },
    {
        "name": "🎯 Budget Stretch",
        "description": "User wants expensive item but limited budget - showcases agent",
        "query": "RTX 4080 gaming laptop",
        "user_id": "demo_stretch",
        "budget": 1000,
        "expected_path": "deep",
        "talking_points": [
            "Price typically $1500+, triggers agent",
            "Agent suggests refurbished, financing, wait for sale",
            "Best demo for Budget Pathfinder Agent"
        ]
    }
]


async def run_scenario(scenario: dict, engine=None):
    """Run a single demo scenario."""
    print("\n" + "=" * 60)
    print(f"📍 {scenario['name']}")
    print("=" * 60)
    print(f"Description: {scenario['description']}")
    print(f"Query: \"{scenario['query']}\"")
    print(f"Budget: ${scenario['budget']}")
    print(f"Expected Path: {scenario['expected_path'].upper()}")
    print("-" * 60)
    
    if engine is None:
        print("⚠️ No engine provided, skipping execution")
        return None
    
    # Execute search
    result = await engine.search(
        query=scenario['query'],
        user_id=scenario['user_id'],
        budget=scenario['budget']
    )
    
    metrics = result.get('metrics', {})
    path = metrics.get('path_used', 'unknown')
    latency = metrics.get('total_latency_ms', 0)
    
    print(f"\n📊 Results:")
    print(f"   Path: {path.upper()}")
    print(f"   Latency: {latency:.0f}ms")
    print(f"   Reason: {metrics.get('route_reason', 'N/A')}")
    
    # Path matched?
    if path == scenario['expected_path']:
        print(f"   ✓ Path matched expected")
    else:
        print(f"   ⚠️ Path mismatch (expected {scenario['expected_path']})")
    
    # Path-specific output
    if path == 'smart':
        results = result.get('results', [])
        print(f"\n   📦 Found {len(results)} products:")
        for i, item in enumerate(results[:3], 1):
            print(f"      {i}. {item.get('name', 'Unknown')[:40]} - ${item.get('price', 0):.2f}")
    
    elif path == 'deep':
        bundle = result.get('bundle', {})
        bundle_items = bundle.get('bundle', [])
        
        print(f"\n   📦 Bundle ({len(bundle_items)} items):")
        print(f"      Total: ${bundle.get('total_price', 0):.2f}")
        print(f"      Method: {bundle.get('method', 'N/A')}")
        
        for item in bundle_items[:5]:
            print(f"      • {item.get('name', 'Unknown')[:35]} - ${item.get('price', 0):.2f}")
        
        # Agent paths
        agent = result.get('agent_paths')
        if agent and agent.get('paths'):
            print(f"\n   🤖 Agent found {len(agent['paths'])} affordability paths:")
            for i, p in enumerate(agent['paths'][:3], 1):
                print(f"      {i}. [{p.get('path_type', '')}] {p.get('summary', '')[:50]}")
    
    # Talking points
    print(f"\n📢 Talking Points:")
    for point in scenario['talking_points']:
        print(f"   • {point}")
    
    return result


async def run_all_demos():
    """Run all demo scenarios."""
    print("\n" + "=" * 60)
    print("🎬 FINBUNDLE DEMO SCENARIOS")
    print("=" * 60)
    
    # Try to load engine
    engine = None
    try:
        from core.search_engine import FinBundleEngine
        engine = FinBundleEngine()
        print("✓ Engine loaded successfully")
    except Exception as e:
        print(f"⚠️ Could not load engine: {e}")
        print("   Running in dry-run mode (no actual searches)")
    
    # Run scenarios
    results = []
    for scenario in DEMO_SCENARIOS:
        try:
            result = await run_scenario(scenario, engine)
            results.append({
                'name': scenario['name'],
                'success': result is not None,
                'path_matched': result and result.get('metrics', {}).get('path_used') == scenario['expected_path']
            })
        except Exception as e:
            print(f"\n❌ Scenario failed: {e}")
            results.append({
                'name': scenario['name'],
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DEMO SUMMARY")
    print("=" * 60)
    
    for r in results:
        status = "✓" if r.get('success') else "✗"
        match = "✓" if r.get('path_matched') else "⚠️" if r.get('success') else "✗"
        print(f"   {status} {r['name']} [path: {match}]")
    
    success_count = sum(1 for r in results if r.get('success'))
    print(f"\n   Total: {success_count}/{len(results)} scenarios completed")
    
    print("\n✅ Demo sequence complete!")


def print_scenario_guide():
    """Print a guide for running demos."""
    print("\n" + "=" * 60)
    print("📖 FINBUNDLE DEMO GUIDE")
    print("=" * 60)
    
    for i, scenario in enumerate(DEMO_SCENARIOS, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   {scenario['description']}")
        print(f"   Query: \"{scenario['query']}\"")
        print(f"   Budget: ${scenario['budget']}")
        print(f"   Path: {scenario['expected_path'].upper()}")
        print(f"   Key points:")
        for point in scenario['talking_points']:
            print(f"      - {point}")
    
    print("\n" + "-" * 60)
    print("💡 Tips for Demo:")
    print("   1. Start with 'Quick Search' to show fast path routing")
    print("   2. Use 'Budget Laptop' to demo smart path filtering")
    print("   3. Show 'Gaming Setup' for full bundle optimization")
    print("   4. End with 'Budget Stretch' to highlight agent capabilities")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FinBundle Demo Runner")
    parser.add_argument("--guide", action="store_true", help="Print demo guide without running")
    parser.add_argument("--scenario", type=int, help="Run specific scenario (1-5)")
    args = parser.parse_args()
    
    if args.guide:
        print_scenario_guide()
    elif args.scenario:
        if 1 <= args.scenario <= len(DEMO_SCENARIOS):
            asyncio.run(run_scenario(DEMO_SCENARIOS[args.scenario - 1]))
        else:
            print(f"Invalid scenario number. Choose 1-{len(DEMO_SCENARIOS)}")
    else:
        asyncio.run(run_all_demos())
