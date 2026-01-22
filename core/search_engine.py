"""
FinBundle Search Engine
Main orchestrator integrating all components
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Core imports
from core.afig import AFIG
from core.router import QueryRouter
from core.embeddings import EmbeddingService

# Retrieval imports
from retrieval.qdrant_search import QdrantSearch
from retrieval.cache import PostgreSQLCache

# Optimization imports
from optimization.feasibility import FeasibilityGate
from optimization.bundle_optimizer import BundleOptimizer, Product

# Agent imports
from agent.budget_agent import BudgetPathfinderAgent

# Explanation imports
from explanation.llm_explainer import LLMExplainer


@dataclass
class SearchMetrics:
    """Search performance metrics."""
    total_latency_ms: float
    path_used: str
    cache_hit: bool
    qdrant_latency_ms: float = 0
    optimizer_latency_ms: float = 0
    agent_latency_ms: float = 0
    explainer_latency_ms: float = 0


class FinBundleEngine:
    """
    Main search engine orchestrating all FinBundle components.
    Implements three-path architecture for optimal latency.
    """
    
    def __init__(self):
        # Initialize all components
        self.router = QueryRouter()
        self.embedder = EmbeddingService()
        self.qdrant = QdrantSearch()
        self.cache = PostgreSQLCache(table_name="search_cache")
        self.feasibility = FeasibilityGate()
        self.optimizer = BundleOptimizer()
        self.agent = BudgetPathfinderAgent()
        self.explainer = LLMExplainer()
        
        # Precomputed queries for fast path
        self._precomputed = {}
    
    async def search(self, query: str, user_id: str, 
                    budget: float, cart: List[Dict] = None) -> Dict[str, Any]:
        """
        Main search entry point.
        
        Args:
            query: User's search query
            user_id: User identifier for AFIG
            budget: User's budget
            cart: Current cart items (optional)
            
        Returns:
            Search results with path info and metrics
        """
        start_time = time.time()
        cart = cart or []
        
        # Load user AFIG
        afig = AFIG(user_id)
        afig_context = afig.reconcile()
        
        # Update situational context with budget
        afig.update_situational({
            'mission': query,
            'budget_override': budget
        })
        
        # Route query to appropriate path
        route_decision = self.router.analyze(query, budget, afig_context)
        path = route_decision.path.value
        
        # Execute path-specific logic
        if path == "fast":
            result = await self._fast_path(query, afig_context)
        elif path == "smart":
            result = await self._smart_path(query, budget, afig_context)
        else:  # deep
            result = await self._deep_path(query, budget, afig_context, user_id, cart)
        
        # Add metrics
        total_latency = (time.time() - start_time) * 1000
        result['metrics'] = {
            'total_latency_ms': round(total_latency, 2),
            'path_used': path,
            'route_confidence': route_decision.confidence,
            'route_reason': route_decision.reason
        }
        
        # Update behavioral signal
        afig.update_behavioral({
            'type': 'search',
            'query': query
        })
        
        afig.close()
        
        return result
    
    async def _fast_path(self, query: str, afig_context: Dict) -> Dict[str, Any]:
        """
        Fast path for precomputed/cached queries.
        Target: <100ms
        """
        cache_key = f"fast:{query.lower().strip()}"
        
        # Check cache
        cached = self.cache.get(cache_key)
        if cached:
            return {
                'path': 'fast',
                'results': cached.get('results', []),
                'count': cached.get('count', 0),
                'cache_hit': True
            }
        
        # For truly fast queries, use precomputed results
        # In production, these would be pre-indexed popular queries
        query_intent = self.router.get_query_intent(query)
        categories = query_intent.get('categories', [])
        
        if categories:
            # Quick category lookup
            results = self._get_category_popular(categories[0])
            
            self.cache.set(cache_key, {
                'results': results,
                'count': len(results)
            }, ttl=3600)  # 1 hour cache
            
            return {
                'path': 'fast',
                'results': results,
                'count': len(results),
                'cache_hit': False
            }
        
        # Fallback to smart path if no precomputed available
        return {
            'path': 'fast',
            'results': [],
            'count': 0,
            'cache_hit': False,
            'note': 'No precomputed results, try smart path'
        }
    
    async def _smart_path(self, query: str, budget: float,
                         afig_context: Dict) -> Dict[str, Any]:
        """
        Smart path with vector search and light filtering.
        Target: <300ms
        """
        start = time.time()
        
        # Check cache first
        cache_key = f"smart:{query.lower()}:{budget}"
        cached = self.cache.get(cache_key)
        if cached:
            return {
                'path': 'smart',
                'cache_hit': True,
                **cached
            }
        
        # Embed query
        query_vector = self.embedder.encode_query(query)
        
        # Search Qdrant with constraints
        qdrant_start = time.time()
        
        # Get query intent for filtering
        intent = self.router.get_query_intent(query)
        categories = intent.get('categories', None)
        brands = intent.get('brands', None)
        
        candidates = self.qdrant.search_with_constraints(
            query_vector=query_vector.tolist(),
            max_price=budget * 0.5 if intent.get('is_bundle') else budget,
            categories=categories if categories else None,
            brands=brands if brands else None,
            in_stock_only=True,
            min_rating=3.5,
            limit=30
        )
        
        qdrant_latency = (time.time() - qdrant_start) * 1000
        
        # Apply feasibility filter
        feasible = self.feasibility.filter_candidates(
            candidates, afig_context, budget
        )
        
        # Prepare results
        results = []
        for item in feasible[:15]:
            results.append({
                'product_id': item.get('product_id', ''),
                'name': item.get('name', ''),
                'price': item.get('price', 0),
                'category': item.get('category', ''),
                'brand': item.get('brand', ''),
                'rating': item.get('rating', 0),
                'score': item.get('score', 0),
                'utility': item.get('_feasibility', {}).get('adjusted_utility', 0)
            })
        
        result = {
            'path': 'smart',
            'results': results,
            'count': len(results),
            'qdrant_latency_ms': round(qdrant_latency, 2),
            'total_candidates': len(candidates),
            'cache_hit': False
        }
        
        # Cache results
        self.cache.set(cache_key, result, ttl=1800)  # 30 min cache
        
        return result
    
    async def _deep_path(self, query: str, budget: float,
                        afig_context: Dict, user_id: str,
                        cart: List[Dict]) -> Dict[str, Any]:
        """
        Deep path with full optimization and agent.
        Target: <1500ms
        """
        result = {
            'path': 'deep',
            'cache_hit': False
        }
        
        # Step 1: Get candidates (similar to smart path)
        query_vector = self.embedder.encode_query(query)
        
        qdrant_start = time.time()
        candidates = self.qdrant.search(
            query_vector=query_vector.tolist(),
            limit=50
        )
        result['qdrant_latency_ms'] = round((time.time() - qdrant_start) * 1000, 2)
        
        # Step 2: Feasibility filter
        feasible = self.feasibility.filter_candidates(
            candidates, afig_context, budget
        )
        
        # Step 3: Bundle optimization
        opt_start = time.time()
        
        # Get query intent for required categories
        intent = self.router.get_query_intent(query)
        required_categories = intent.get('categories', None)
        
        bundle_result = self.optimizer.optimize(
            products=feasible[:25],
            budget=budget,
            user_prefs=afig_context,
            required_categories=required_categories,
            max_items=8
        )
        
        result['optimizer_latency_ms'] = round((time.time() - opt_start) * 1000, 2)
        result['bundle'] = bundle_result.to_dict()
        
        # Step 4: Check if agent needed (budget gap)
        total_price = bundle_result.total_price
        gap = total_price - budget
        
        agent_result = None
        if gap > 50:  # Significant gap
            agent_start = time.time()
            
            # Create a synthetic "target product" representing the bundle
            bundle_product = {
                'name': f"Bundle: {query}",
                'price': total_price,
                'category': required_categories[0] if required_categories else 'bundle'
            }
            
            agent_result = await self.agent.find_affordability_paths(
                product=bundle_product,
                user_afig=afig_context,
                current_cart=cart,
                budget=budget
            )
            
            result['agent_latency_ms'] = round((time.time() - agent_start) * 1000, 2)
            result['agent_paths'] = agent_result
        else:
            result['agent_paths'] = None
        
        # Step 5: Generate explanations for top items
        explain_start = time.time()
        explanations = []
        
        for item in bundle_result.bundle[:3]:
            product_dict = {
                'product_id': item.id,
                'name': item.name,
                'price': item.price,
                'category': item.category,
                'rating': 4.5  # Default if not available
            }
            exp = await self.explainer.explain(product_dict, afig_context)
            explanations.append({
                'product_id': item.id,
                'explanation': exp
            })
        
        result['explainer_latency_ms'] = round((time.time() - explain_start) * 1000, 2)
        result['explanations'] = explanations
        
        # Bundle explanation
        if bundle_result.bundle:
            result['bundle_explanation'] = self.explainer.explain_bundle(
                bundle_result.bundle,
                bundle_result.total_price,
                afig_context
            )
        
        return result
    
    def _get_category_popular(self, category: str, limit: int = 10) -> List[Dict]:
        """Get popular products in a category (for fast path)."""
        # In production, this would query a precomputed table
        # For now, return placeholder
        return [
            {
                'product_id': f'popular_{category}_{i}',
                'name': f'Popular {category.title()} #{i+1}',
                'category': category,
                'price': 100 + i * 50,
                'rating': 4.5 - i * 0.1,
                'source': 'precomputed'
            }
            for i in range(min(limit, 5))
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            'cache_stats': self.cache.stats(),
            'qdrant_available': self.qdrant.is_available,
            'qdrant_info': self.qdrant.collection_info() if self.qdrant.is_available else {}
        }


# Async test
async def _test_engine():
    print("🧪 Testing FinBundle Search Engine...")
    
    engine = FinBundleEngine()
    
    # Test queries for each path
    test_cases = [
        ("laptop", "user_001", 500, "fast"),
        ("gaming mouse under $100", "user_001", 100, "smart"),
        ("complete gaming setup", "user_001", 1500, "deep"),
    ]
    
    for query, user_id, budget, expected_path in test_cases:
        print(f"\n📊 Query: \"{query}\" (budget: ${budget})")
        
        result = await engine.search(query, user_id, budget)
        
        print(f"   Path: {result['metrics']['path_used'].upper()}")
        print(f"   Latency: {result['metrics']['total_latency_ms']:.0f}ms")
        print(f"   Reason: {result['metrics']['route_reason']}")
        
        if 'results' in result:
            print(f"   Results: {len(result.get('results', []))} items")
        
        if 'bundle' in result:
            bundle = result['bundle']
            print(f"   Bundle: {len(bundle.get('bundle', []))} items, ${bundle.get('total_price', 0):.2f}")
        
        if result.get('agent_paths'):
            paths = result['agent_paths'].get('paths', [])
            print(f"   Agent paths: {len(paths)} found")
    
    print("\n📊 Engine stats:")
    stats = engine.get_stats()
    print(f"   Cache: {stats['cache_stats']}")
    print(f"   Qdrant available: {stats['qdrant_available']}")
    
    print("\n✅ Search engine test complete!")


if __name__ == "__main__":
    asyncio.run(_test_engine())
