"""
FinBundle Search Engine
Main orchestrator integrating all components with Three-Path Architecture
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Core imports
from core.afig import AFIG
from core.router import QueryRouter
from core.embeddings import EmbeddingService
from db.products import get_popular_products_by_category

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


class FinBundleEngine:
    """
    Main search engine orchestrating FinBundle components.
    Implements Three-Path Architecture with strict timeouts.
    """
    
    def __init__(self):
        self.router = QueryRouter()
        self.embedder = EmbeddingService()
        self.qdrant = QdrantSearch()
        self.cache = PostgreSQLCache(table_name="search_cache")
        self.feasibility = FeasibilityGate()
        self.optimizer = BundleOptimizer()
        self.agent = BudgetPathfinderAgent()
        self.explainer = LLMExplainer()
        
    async def search(self, query: str, user_id: str, 
                    budget: float, cart: List[Dict] = None,
                    skip_explanations: bool = False) -> Dict[str, Any]:
        """
        Main search entry point.
        """
        start_time = time.time()
        cart = cart or []
        afig = None
        
        try:
            # 1. Load User Context
            afig = AFIG(user_id)
            afig_context = afig.reconcile()
            afig.update_situational({'mission': query, 'budget_override': budget})
        
            # 2. Route Query
            path = self.router.route(query, budget, afig_context)
            
            # 3. Execute Path Logic with Timeouts
            try:
                if path == "fast":
                    result = await self._fast_path(query, budget, afig_context)
                elif path == "smart":
                    result = await asyncio.wait_for(
                        self._smart_path(query, budget, afig_context), 
                        timeout=0.5
                    )
                else:  # deep
                    result = await asyncio.wait_for(
                        self._deep_path(query, budget, afig_context, user_id, cart, skip_explanations),
                        timeout=5.0
                    )
            except asyncio.TimeoutError:
                print(f"⚠️ Path {path} timed out! Falling back to fast/smart path.")
                # Fallback logic
                if path == "deep":
                     result = await self._smart_path(query, budget, afig_context)
                else:
                     result = await self._fast_path(query, budget, afig_context)
                result['metrics'] = {'note': 'Fallback due to timeout'}
                
            # 4. Metrics & Logging
            total_latency = (time.time() - start_time) * 1000
            if 'metrics' not in result:
                 result['metrics'] = {}
                 
            result['metrics'].update({
                'total_latency_ms': round(total_latency, 2),
                'path_used': path,
                'user_id': user_id
            })
            
            afig.update_behavioral({'type': 'search', 'query': query})
            
            return result
        finally:
            if afig:
                afig.close()

    async def _fast_path(self, query: str, budget: float, afig_context: Dict) -> Dict:
        """Fast Path: Cache-first serving (<100ms)"""
        start = time.time()
        archetype = afig_context.get('archetype', 'default')
        cache_key = self.router.get_cache_key(query, budget, archetype)
        
        # Check Cache
        cached = self.cache.get(cache_key)
        if cached:
            return {
                'path': 'fast',
                'cache_hit': True,
                'results': cached.get('results', []),
                'latency_ms': (time.time() - start) * 1000
            }
            
        # Miss -> Use Precomputed/Popular
        intent = self.router.get_query_intent(query)
        categories = intent.get('categories', [])
        
        if categories:
            # Query PostgreSQL for popular products in category
            results = get_popular_products_by_category(categories[0], limit=10)
            if results:
                # Apply budget filter
                if budget:
                    results = [r for r in results if r.get('price', 0) <= budget]
                
                if results:
                    # Cache for longer duration
                    self.cache.set(cache_key, {'results': results}, ttl=3600)
                    return {
                        'path': 'fast',
                        'cache_hit': False,
                        'results': results,
                        'latency_ms': (time.time() - start) * 1000
                    }
        
        # Fast path has no results - fall back to smart path
        print(f"⚡ Fast path found no results for '{query}', falling back to smart path")
        return await self._smart_path(query, budget, afig_context)

    async def _smart_path(self, query: str, budget: float, afig_context: Dict) -> Dict:
        """Smart Path: Vector Search + Feasibility (<300ms)"""
        start = time.time()
        
        # Encode
        query_vec = self.embedder.encode_query(query)
        
        # Search Qdrant - use plain search first, then filter in Python
        # This avoids issues with missing payload indexes in Qdrant
        results = self.qdrant.search(query_vec.tolist(), limit=50)
            
        # Enrich with full DB data (description, specs, etc.)
        results = self.qdrant.enrich_results(results)
        
        # Apply price filter in Python
        if budget:
            results = [r for r in results if r.price <= budget]
            
        # Feasibility Filter
        feasible = self.feasibility.filter_candidates(results, afig_context, budget)
        
        # Format Results
        formatted = []
        for p in feasible[:15]:
            formatted.append({
                'product_id': p.get('product_id', ''),
                'name': p.get('name', ''),
                'price': p.get('price', 0),
                'category': p.get('category', ''),
                'brand': p.get('brand', 'Generic'),
                'rating': p.get('rating', 0),
                'rating_count': p.get('rating_count', 0),
                'image_url': p.get('image_url', ''),
                'description': p.get('description', ''),
                'score': p.get('score', 0.75),
                'utility': p.get('_feasibility', {}).get('adjusted_utility', 0),
                'in_stock': p.get('in_stock', True),
                'condition': p.get('condition', 'new')
            })
            
        return {
            'path': 'smart',
            'results': formatted,
            'count': len(formatted),
            'latency_ms': (time.time() - start) * 1000
        }

    async def _deep_path(self, query: str, budget: float, afig_context: Dict, 
                        user_id: str, cart: List, skip_explanations: bool) -> Dict:
        """Deep Path: Optimization + Agent + Explanations (<1000ms)"""
        start = time.time()
        
        # 1. Broad Retrieval
        query_vec = self.embedder.encode_query(query)
        candidates = self.qdrant.search(query_vec.tolist(), limit=50)
        
        # Enrich with full DB data first
        candidates = self.qdrant.enrich_results(candidates)
        
        # 2. Feasibility
        feasible = self.feasibility.filter_candidates(candidates, afig_context, budget)
        
        # 3. Bundle Optimization
        intent = self.router.get_query_intent(query)
        bundle_result = self.optimizer.optimize(
            products=feasible,
            budget=budget,
            user_prefs=afig_context,
            required_categories=intent.get('categories', []),
            max_items=8
        )
        
        # 4. Agent Activation (if gap exists)
        gap = bundle_result.total_price - budget
        agent_paths = None
        if gap > 50:  # Activate agent when $50+ over budget
            bundle_product = {
                'name': f"Bundle: {query}", 
                'price': bundle_result.total_price,
                'category': intent.get('categories', ['electronics'])[0] if intent.get('categories') else 'electronics'
            }
            agent_result = await self.agent.find_affordability_paths(
                product=bundle_product,
                user_afig=afig_context,
                current_cart=cart,
                budget=budget
            )
            # Convert AgentResult to dict for JSON serialization
            if agent_result:
                agent_paths = agent_result.to_dict() if hasattr(agent_result, 'to_dict') else agent_result

        # 5. Explanations
        explanations = []
        if not skip_explanations:
            # Parallelize explanation generation
            items = bundle_result.bundle[:3]
            tasks = []
            for item in items:
                p_dict = {'name': item.name, 'price': item.price, 'category': item.category}
                tasks.append(self.explainer.explain(p_dict, afig_context))
            
            explanation_results = await asyncio.gather(*tasks)
            
            for item, exp in zip(items, explanation_results):
                explanations.append({'product_id': item.id, 'explanation': exp})
                 
        return {
            'path': 'deep',
            'bundle': bundle_result.to_dict(),
            'agent_paths': agent_paths,
            'explanations': explanations,
            'latency_ms': (time.time() - start) * 1000
        }



    def get_stats(self) -> Dict:
        return {
            'cache': self.cache.stats(),
            'qdrant': self.qdrant.is_available
        }

if __name__ == "__main__":
    asyncio.run(FinBundleEngine().search("laptop", "test", 1000))
