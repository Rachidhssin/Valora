"""
FinBundle Search Engine
Main orchestrator integrating all components with Three-Path Architecture
"""
import time
import asyncio
import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Core imports
from core.afig import AFIG
from core.router import QueryRouter
from core.embeddings import EmbeddingService
from core.taxonomy import disambiguate_search, CategoryTaxonomy
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
                    result = await self._fast_path(query, budget, afig_context, cart)
                elif path == "smart":
                    result = await asyncio.wait_for(
                        self._smart_path(query, budget, afig_context, cart), 
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
                     result = await self._smart_path(query, budget, afig_context, cart)
                else:
                     result = await self._fast_path(query, budget, afig_context, cart)
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

    async def _fast_path(self, query: str, budget: float, afig_context: Dict, cart: List[Dict] = None) -> Dict:
        """Fast Path: Cache-first serving (<100ms)"""
        start = time.time()
        archetype = afig_context.get('archetype', 'default')
        cache_key = self.router.get_cache_key(query, budget, archetype)
        
        # Get cart product IDs for filtering
        cart = cart or []
        cart_ids = {item.get('product_id') for item in cart if item.get('product_id')}
        
        # Check Cache
        cached = self.cache.get(cache_key)
        if cached:
            results = cached.get('results', [])
            # Filter out cart items
            if cart_ids:
                results = [r for r in results if r.get('product_id') not in cart_ids]
            return {
                'path': 'fast',
                'cache_hit': True,
                'results': results,
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
                
                # Filter out cart items
                if cart_ids:
                    results = [r for r in results if r.get('product_id') not in cart_ids]
                
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
        return await self._smart_path(query, budget, afig_context, cart)

    async def _smart_path(self, query: str, budget: float, afig_context: Dict, cart: List[Dict] = None) -> Dict:
        """
        Smart Path: Vector Search + LearnedProductScorer + Feasibility (<300ms)
        
        With 500K products, Qdrant provides excellent coverage so we:
        1. Use native Qdrant filters (price, category) for server-side filtering
        2. Keep disambiguation as optional enhancement, not critical
        3. Use Qdrant similarity scores directly for ranking
        """
        start = time.time()
        
        # Get cart product IDs for filtering
        cart = cart or []
        cart_ids = {item.get('product_id') for item in cart if item.get('product_id')}
        
        # Import scorer
        from core.scorer import get_scorer
        scorer = get_scorer()
        
        # Encode query and L2 normalize for dot product similarity
        query_vec = self.embedder.encode_query(query)
        query_vec_normalized = query_vec / np.linalg.norm(query_vec)
        
        # === OPTIONAL DISAMBIGUATION (helps but not critical with 500K products) ===
        disambiguation = disambiguate_search(query)
        target_category = disambiguation.get('primary_category')
        boost_categories = disambiguation.get('boost_categories', [])
        exclude_categories = disambiguation.get('exclude_categories', [])
        is_ambiguous = disambiguation.get('is_ambiguous', False)
        
        # === QDRANT SEARCH WITH NATIVE FILTERS ===
        # Strategy: Combine semantic search with keyword match for better relevance
        
        # Extract main product keyword from query (e.g., "4k monitors" -> "monitor")
        main_keyword = self._extract_main_product_keyword(query)
        
        # First: Try text search for products with the keyword in name
        text_results = []
        if main_keyword:
            text_results = self.qdrant.search_with_constraints(
                query_vector=query_vec.tolist(),
                max_price=budget * 1.2 if budget else None,
                text_query=main_keyword,  # Text search in product name
                limit=50,
                use_acorn=True
            )
        
        # Second: Semantic search for broader matches
        semantic_results = self.qdrant.search_with_constraints(
            query_vector=query_vec.tolist(),
            max_price=budget * 1.2 if budget else None,
            categories=boost_categories if boost_categories else None,
            limit=100,
            use_acorn=True
        )
        
        # Combine results: text matches first (more relevant), then semantic
        seen_ids = set()
        results = []
        
        # Boost text matches by putting them first
        for r in text_results:
            if r.product_id not in seen_ids:
                r.score = min(r.score * 1.15, 1.0)  # Boost text matches
                results.append(r)
                seen_ids.add(r.product_id)
        
        # Add remaining semantic results
        for r in semantic_results:
            if r.product_id not in seen_ids:
                results.append(r)
                seen_ids.add(r.product_id)
            
        # Enrich with full DB data (description, specs, etc.)
        results = self.qdrant.enrich_results(results)
        
        # === ACCESSORY FILTER ===
        # When searching for main products, filter out accessories (cables, mounts, etc.)
        results = self._filter_accessories(query, results)
        
        # === LIGHT EXCLUSION FILTER (only for ambiguous queries) ===
        # With good category coverage, this is less critical but still helpful
        if exclude_categories and is_ambiguous:
            original_count = len(results)
            results = [
                r for r in results 
                if not CategoryTaxonomy.should_filter_result(r.category, exclude_categories, r.name)
            ]
            # Log if significant filtering happened
            if len(results) < original_count * 0.5:
                print(f"⚠️ Exclusion filter removed {original_count - len(results)} results")
        
        # === MINIMUM SIMILARITY THRESHOLD ===
        # With 500K products, we can enforce quality - remove low-relevance results
        MIN_SIMILARITY = 0.40
        results = [r for r in results if r.score >= MIN_SIMILARITY]
        
        # Convert to dicts for scoring, preserve Qdrant similarity score
        result_dicts = []
        for r in results:
            if hasattr(r, 'to_dict'):
                d = r.to_dict()
                d['_qdrant_score'] = r.score
                result_dicts.append(d)
            else:
                result_dicts.append(r)
        
        # Re-rank using LearnedProductScorer with AFIG-aware weights
        reranked = scorer.rerank_results(
            results=result_dicts,
            query_vec=query_vec_normalized,
            budget=budget,
            user_afig=afig_context,
            embedder=self.embedder,
            boost_categories=boost_categories,
            is_ambiguous=is_ambiguous
        )
        
        # === QUALITY-TIERED RESULTS ===
        # Separate high-confidence matches from related products
        HIGH_SIMILARITY = 0.50
        
        # Filter out cart items before formatting
        if cart_ids:
            reranked = [p for p in reranked if p.get('product_id') not in cart_ids]
        
        primary_count = sum(1 for p in reranked[:30] if p.get('_qdrant_score', 0) >= HIGH_SIMILARITY)
        
        # Format Results - return top 30 sorted by score
        formatted = []
        for p in reranked[:30]:
            scoring = p.get('_scoring', {})
            qdrant_score = p.get('_qdrant_score', 0.5)
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
                'utility': scoring.get('final_score', p.get('score', 0)),
                'in_stock': p.get('in_stock', True),
                'condition': p.get('condition', 'new'),
                'match_tier': 'primary' if qdrant_score >= HIGH_SIMILARITY else 'related',
                '_scoring': scoring
            })
        
        latency = (time.time() - start) * 1000
            
        return {
            'path': 'smart',
            'results': formatted,
            'count': len(formatted),
            'primary_matches': primary_count,
            'latency_ms': latency,
            'acorn_enabled': True,
            'scoring_enabled': True,
            'disambiguation': {
                'applied': is_ambiguous,
                'target_category': target_category,
                'boost_categories': boost_categories,
                'excluded_categories': exclude_categories,
                'detected_terms': disambiguation.get('detected_terms', [])
            }
        }

    async def _deep_path(self, query: str, budget: float, afig_context: Dict, 
                        user_id: str, cart: List, skip_explanations: bool) -> Dict:
        """Deep Path: Optimization + Agent + Explanations (<1000ms)"""
        start = time.time()
        
        # 1. Parse query intent to get target categories
        intent = self.router.get_query_intent(query)
        target_categories = self._infer_bundle_categories(query)
        
        # Extract context keywords from original query (e.g., "gaming", "professional", "budget")
        context_keywords = self._extract_query_context(query)
        print(f"🔍 Query context: {context_keywords}")
        
        # 2. Multi-Category Retrieval - search for each category WITH CONTEXT
        all_candidates = []
        budget_per_category = budget / max(len(target_categories), 1)
        
        for category in target_categories:
            # IMPORTANT: Include original query context for better relevance
            # E.g., "gaming laptop" instead of just "laptop"
            category_query = f"{context_keywords} {category}".strip()
            query_vec = self.embedder.encode_query(category_query)
            
            # Allow higher budget per item for quality - up to 60% of total budget
            # This ensures we get premium products, not just cheap ones
            max_price_per_item = min(budget * 0.6, budget_per_category * 2)
            
            # Get more candidates for this category
            candidates = self.qdrant.search_with_constraints(
                query_vector=query_vec.tolist(),
                max_price=max_price_per_item,
                text_query=category,  # Must contain category keyword
                limit=40  # Get more candidates for better quality selection
            )
            
            # Tag with target category and query context
            for c in candidates:
                c._bundle_category = category
                c._query_context = context_keywords
            all_candidates.extend(candidates)
        
        # Enrich with full DB data
        all_candidates = self.qdrant.enrich_results(all_candidates)
        
        # Filter out accessories for main product categories
        all_candidates = [c for c in all_candidates if not self._is_accessory_for_bundle(c)]
        
        # Convert to Product objects for optimizer, using bundle category
        from optimization.bundle_optimizer import Product
        bundle_products = []
        
        for c in all_candidates:
            # Get bundle category (what we searched for) or fall back to product category
            bundle_cat = getattr(c, '_bundle_category', None) or c.category
            
            # Calculate utility: PRIORITIZE QUALITY for bundle purchases
            # Users with higher budget want BETTER products, not just more products
            rating_score = (c.rating / 5.0) if c.rating else 0.5
            relevance_score = c.score if c.score else 0.5
            
            # Price scoring: prefer products that use the budget well
            # Don't penalize expensive items - users WANT quality within their budget
            price_ratio = c.price / budget if budget > 0 else 0.5
            
            # Quality tier bonus: reward mid-to-high price products (20-50% of budget per item)
            # This ensures "gaming laptops" not "basic laptops" when user has budget
            if price_ratio >= 0.15 and price_ratio <= 0.5:
                quality_tier_bonus = 0.2  # Good value range
            elif price_ratio > 0.5 and price_ratio <= 0.7:
                quality_tier_bonus = 0.1  # Premium but acceptable
            else:
                quality_tier_bonus = 0.0  # Too cheap or too expensive
            
            # Weight: 40% rating, 35% relevance, 15% quality tier, 10% rating count boost
            rating_count = getattr(c, 'rating_count', 0) or 0
            popularity_score = min(1.0, rating_count / 500) * 0.5 + 0.5  # Boost popular items
            
            utility = (
                (rating_score * 0.4) + 
                (relevance_score * 0.35) + 
                (quality_tier_bonus) +
                (popularity_score * 0.1)
            )
            
            bundle_products.append(Product(
                id=c.product_id,
                name=c.name,
                price=c.price,
                category=bundle_cat,  # Use the bundle category for matching
                utility=utility,
                image_url=c.image_url if hasattr(c, 'image_url') else '',
                brand=c.brand if hasattr(c, 'brand') else '',
                rating=c.rating if hasattr(c, 'rating') else 0
            ))
        
        print(f"🎯 Bundle candidates: {len(bundle_products)} products across {len(target_categories)} categories")
        
        # Show category distribution
        cat_counts = {}
        for p in bundle_products:
            cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
        print(f"   Categories: {dict(cat_counts)}")
        
        # 3. Sort products by utility within each category (best first)
        bundle_products.sort(key=lambda p: (-p.utility, -p.rating, p.price))
        
        # 4. Select TOP 6-8 BEST products per category (curated selection)
        # Show more options so users have real choice, but still curated quality
        MAX_PRODUCTS_PER_CATEGORY = 8
        curated_by_category = {}
        for p in bundle_products:
            if p.category not in curated_by_category:
                curated_by_category[p.category] = []
            # Keep top N per category (already sorted by utility/rating)
            if len(curated_by_category[p.category]) < MAX_PRODUCTS_PER_CATEGORY:
                curated_by_category[p.category].append(p)
        
        # 5. Run optimization on the curated set to mark "AI recommended"
        curated_flat = [p for products in curated_by_category.values() for p in products]
        bundle_result = self.optimizer.optimize(
            products=curated_flat,
            budget=budget,
            user_prefs=afig_context,
            required_categories=target_categories,
            max_items=len(target_categories) + 2
        )
        
        # Mark which items are AI recommended
        recommended_ids = {p.id for p in bundle_result.bundle}
        
        # 6. Convert to serializable format with recommendation flag
        curated_products = {}
        for cat, products in curated_by_category.items():
            curated_products[cat] = [
                {
                    'id': p.id, 'name': p.name, 'price': p.price,
                    'category': p.category, 'utility': p.utility,
                    'image_url': p.image_url, 'brand': p.brand, 'rating': p.rating,
                    'is_recommended': p.id in recommended_ids
                }
                for p in products
            ]
        
        # 7. Agent Activation (if gap exists)
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

        # 8. Generate AI explanations for ALL recommended products
        explanations = []
        if not skip_explanations:
            # Get all recommended products (the AI picks)
            recommended_products = [p for p in curated_flat if p.id in recommended_ids]
            
            # Generate explanations in parallel (limit to 6 for performance)
            items_to_explain = recommended_products[:6]
            tasks = []
            for item in items_to_explain:
                p_dict = {
                    'name': item.name, 
                    'price': item.price, 
                    'category': item.category,
                    'brand': item.brand,
                    'rating': item.rating,
                    'query_context': context_keywords  # Pass the original query context
                }
                tasks.append(self._generate_product_explanation(p_dict, afig_context, query))
            
            explanation_results = await asyncio.gather(*tasks)
            
            for item, exp in zip(items_to_explain, explanation_results):
                explanations.append({'product_id': item.id, 'explanation': exp})
                 
        return {
            'path': 'deep',
            'bundle': bundle_result.to_dict(),
            'curated_products': curated_products,  # Top products per category with is_recommended flag
            'agent_paths': agent_paths,
            'explanations': explanations,
            'query_context': context_keywords,  # Return the detected context
            'latency_ms': (time.time() - start) * 1000
        }
    
    async def _generate_product_explanation(self, product: Dict, afig_context: Dict, original_query: str) -> str:
        """Generate a personalized explanation for why this product was recommended."""
        try:
            # Use the explainer but with enhanced context
            explanation = await self.explainer.explain(product, afig_context)
            return explanation
        except Exception as e:
            # Fallback explanation based on product attributes
            brand = product.get('brand', 'This product')
            rating = product.get('rating', 0)
            category = product.get('category', 'item')
            
            if rating >= 4.5:
                return f"Top-rated {category} with {rating}★ rating - excellent quality and reliability."
            elif rating >= 4.0:
                return f"Highly rated {category} from {brand} - great balance of quality and value."
            else:
                return f"Solid choice for your {category} needs - good value within your budget."
    
    def _extract_query_context(self, query: str) -> str:
        """
        Extract context keywords from query to improve category searches.
        E.g., "gaming setup for streaming" -> "gaming streaming"
        """
        query_lower = query.lower()
        
        # Context keywords that should be passed to category searches
        context_keywords = []
        
        # Quality/Use-case modifiers
        quality_modifiers = [
            'gaming', 'professional', 'pro', 'budget', 'premium', 'high-end', 'entry-level',
            'beginner', 'advanced', 'studio', 'creator', 'content', 'streaming', 'esports',
            'competitive', 'casual', 'portable', 'desktop', 'wireless', 'wired', 'rgb',
            'mechanical', 'ergonomic', 'ultrawide', '4k', '1080p', '144hz', '240hz',
            'noise-cancelling', 'open-back', 'closed-back', 'condenser', 'dynamic',
            'mirrorless', 'dslr', 'compact', 'full-frame', 'aps-c'
        ]
        
        for modifier in quality_modifiers:
            if modifier in query_lower:
                context_keywords.append(modifier)
        
        # Brand preferences
        brand_keywords = [
            'apple', 'samsung', 'sony', 'lg', 'asus', 'msi', 'razer', 'logitech', 
            'corsair', 'steelseries', 'hyperx', 'dell', 'hp', 'lenovo', 'acer',
            'bose', 'sennheiser', 'audio-technica', 'shure', 'blue', 'elgato'
        ]
        
        for brand in brand_keywords:
            if brand in query_lower:
                context_keywords.append(brand)
        
        return ' '.join(context_keywords) if context_keywords else ''

    # === ACCESSORY FILTER ===
    # Keywords that indicate a product is an accessory, not a main product
    ACCESSORY_KEYWORDS = {
        'cable', 'cables', 'cord', 'cords',
        'adapter', 'adapters', 'converter', 'converters',
        'mount', 'mounts', 'stand', 'stands', 'bracket', 'brackets',
        'hub', 'dock', 'docking',
        'charger', 'chargers', 'charging',
        'case', 'cover', 'sleeve', 'bag', 'pouch',
        'protector', 'film', 'guard',
        'cleaner', 'cleaning', 'wipe', 'wipes',
        'replacement', 'spare',
        'extension', 'extender', 'splitter',
        'kvm', 'switch',  # KVM switches are accessories
    }
    
    # Main product categories that should NOT show accessories by default
    MAIN_PRODUCT_SEARCHES = {
        'monitor', 'monitors', 'laptop', 'laptops', 'phone', 'phones', 'smartphone',
        'tv', 'television', 'tablet', 'tablets', 'camera', 'cameras',
        'headphones', 'headphone', 'earbuds', 'speaker', 'speakers',
        'keyboard', 'keyboards', 'mouse', 'mice',
        'printer', 'printers', 'router', 'routers', 'webcam', 'webcams',
        # Note: cables, adapters, chargers etc. are NOT here - they ARE accessories
    }
    
    def _filter_accessories(self, query: str, results: list) -> list:
        """
        Filter out accessories when searching for main products.
        
        E.g., "4k monitors" should not return "4K HDMI cable for monitors"
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Check if this is a main product search (not explicitly asking for accessories)
        is_main_product_search = any(term in query_words for term in self.MAIN_PRODUCT_SEARCHES)
        explicitly_wants_accessory = any(acc in query_lower for acc in [
            'cable', 'cables', 'adapter', 'adapters', 'mount', 'mounts', 
            'stand', 'stands', 'charger', 'chargers', 'case', 'cases', 
            'hub', 'hubs', 'dock', 'docks', 'bracket', 'cover', 'sleeve'
        ])
        
        # If not a main product search or explicitly wants accessories, don't filter
        if not is_main_product_search or explicitly_wants_accessory:
            return results
        
        # Filter out products whose names contain accessory keywords
        filtered = []
        removed_count = 0
        
        for r in results:
            name_lower = r.name.lower() if hasattr(r, 'name') else r.get('name', '').lower()
            
            # Check if product name contains accessory keywords
            is_accessory = any(acc in name_lower for acc in self.ACCESSORY_KEYWORDS)
            
            if is_accessory:
                removed_count += 1
            else:
                filtered.append(r)
        
        # Log filtering
        if removed_count > 0:
            print(f"🧹 Filtered {removed_count} accessories from '{query}' results")
        
        # If we filtered too aggressively, return some results
        if len(filtered) < 5 and len(results) > 5:
            print(f"⚠️ Too aggressive filtering, keeping top results")
            return results[:30]
        
        return filtered

    # Map of search terms to product keywords (singularized)
    PRODUCT_KEYWORD_MAP = {
        'monitors': 'monitor', 'monitor': 'monitor',
        'laptops': 'laptop', 'laptop': 'laptop', 'notebook': 'laptop',
        'phones': 'phone', 'phone': 'phone', 'smartphone': 'phone',
        'tablets': 'tablet', 'tablet': 'tablet', 'ipad': 'ipad',
        'cameras': 'camera', 'camera': 'camera',
        'headphones': 'headphone', 'headphone': 'headphone', 'earbuds': 'earbuds',
        'speakers': 'speaker', 'speaker': 'speaker',
        'keyboards': 'keyboard', 'keyboard': 'keyboard',
        'mice': 'mouse', 'mouse': 'mouse',
        'tvs': 'tv', 'tv': 'tv', 'television': 'tv',
        'printers': 'printer', 'printer': 'printer',
        'routers': 'router', 'router': 'router',
        'webcams': 'webcam', 'webcam': 'webcam',
    }
    
    def _extract_main_product_keyword(self, query: str) -> str:
        """
        Extract the main product keyword from a query for text matching.
        
        E.g., "4k gaming monitors" -> "monitor"
              "wireless mouse" -> "mouse"
        """
        query_lower = query.lower()
        words = query_lower.split()
        
        # Check each word against our product keyword map
        for word in words:
            if word in self.PRODUCT_KEYWORD_MAP:
                return self.PRODUCT_KEYWORD_MAP[word]
        
        return None

    # Bundle category mappings for common bundle queries - GENERAL PURPOSE
    # Maps query patterns to relevant product categories
    BUNDLE_CATEGORY_MAP = {
        # Gaming & Entertainment
        'gaming setup': ['monitor', 'keyboard', 'mouse', 'headphones', 'laptop', 'webcam'],
        'gaming rig': ['laptop', 'monitor', 'keyboard', 'mouse', 'headphones'],
        'gaming': ['laptop', 'monitor', 'keyboard', 'mouse', 'headphones'],
        'pc build': ['monitor', 'keyboard', 'mouse', 'headphones', 'webcam'],
        'entertainment': ['tv', 'speaker', 'headphones', 'tablet'],
        
        # Work & Office
        'home office': ['monitor', 'keyboard', 'mouse', 'webcam', 'headphones', 'laptop'],
        'office setup': ['monitor', 'keyboard', 'mouse', 'webcam', 'printer'],
        'office': ['monitor', 'keyboard', 'mouse', 'laptop', 'webcam'],
        'work from home': ['laptop', 'monitor', 'keyboard', 'mouse', 'webcam', 'headphones'],
        'remote work': ['laptop', 'webcam', 'headphones', 'monitor', 'keyboard'],
        'productivity': ['laptop', 'monitor', 'keyboard', 'mouse', 'tablet'],
        
        # Content Creation
        'streaming': ['webcam', 'microphone', 'headphones', 'monitor', 'keyboard', 'lighting'],
        'streaming kit': ['webcam', 'microphone', 'headphones', 'lighting'],
        'content creation': ['camera', 'microphone', 'headphones', 'monitor', 'tablet'],
        'studio': ['microphone', 'headphones', 'webcam', 'monitor', 'lighting'],
        'podcast': ['microphone', 'headphones', 'webcam'],
        'video editing': ['monitor', 'laptop', 'mouse', 'keyboard', 'tablet'],
        
        # Music & Audio
        'music production': ['headphones', 'microphone', 'speaker', 'keyboard', 'monitor'],
        'audio setup': ['headphones', 'speaker', 'microphone'],
        'dj setup': ['headphones', 'speaker', 'laptop', 'monitor'],
        
        # Photography
        'photography': ['camera', 'lens', 'tripod', 'memory card', 'monitor'],
        'photo editing': ['monitor', 'tablet', 'mouse', 'laptop'],
        
        # Travel & Mobile
        'travel': ['laptop', 'tablet', 'headphones', 'power bank', 'camera'],
        'mobile setup': ['phone', 'tablet', 'headphones', 'power bank'],
        
        # Education & Learning  
        'student': ['laptop', 'tablet', 'headphones', 'keyboard', 'mouse'],
        'education': ['laptop', 'tablet', 'headphones', 'monitor'],
        'school': ['laptop', 'tablet', 'headphones', 'printer'],
        
        # Smart Home
        'smart home': ['speaker', 'camera', 'tablet', 'router'],
        'home automation': ['speaker', 'camera', 'tablet'],
    }
    
    def _infer_bundle_categories(self, query: str) -> List[str]:
        """
        Infer target categories for a bundle query.
        Uses keyword matching and semantic understanding to identify relevant product categories.
        """
        query_lower = query.lower()
        
        # Check known bundle patterns (longest match first for accuracy)
        matched_categories = []
        for pattern, categories in sorted(self.BUNDLE_CATEGORY_MAP.items(), key=lambda x: -len(x[0])):
            if pattern in query_lower:
                matched_categories = categories
                break
        
        if matched_categories:
            return matched_categories[:8]  # Return up to 8 categories
        
        # Extract individual keywords and map to categories
        keyword_to_category = {
            'gaming': ['laptop', 'monitor', 'keyboard', 'mouse', 'headphones'],
            'office': ['monitor', 'keyboard', 'mouse', 'laptop', 'webcam'],
            'stream': ['webcam', 'microphone', 'headphones', 'monitor'],
            'music': ['headphones', 'speaker', 'microphone'],
            'photo': ['camera', 'lens', 'tripod', 'monitor'],
            'video': ['camera', 'monitor', 'laptop', 'microphone'],
            'work': ['laptop', 'monitor', 'keyboard', 'mouse'],
            'travel': ['laptop', 'headphones', 'power bank', 'tablet'],
            'student': ['laptop', 'tablet', 'headphones'],
            'creative': ['tablet', 'monitor', 'mouse', 'keyboard'],
            'developer': ['monitor', 'keyboard', 'laptop', 'mouse'],
            'programmer': ['monitor', 'keyboard', 'laptop', 'mouse'],
        }
        
        for keyword, categories in keyword_to_category.items():
            if keyword in query_lower:
                return categories
        
        # Fallback: diverse general electronics bundle
        return ['laptop', 'monitor', 'keyboard', 'mouse', 'headphones', 'tablet']
    
    def _is_accessory_for_bundle(self, product) -> bool:
        """Check if a product is an accessory (cables, adapters, etc.) for bundle purposes."""
        name = product.name.lower() if hasattr(product, 'name') else product.get('name', '').lower()
        
        accessory_keywords = ['cable', 'adapter', 'mount', 'stand', 'charger', 'case', 
                             'cover', 'sleeve', 'hub', 'dock', 'splitter', 'extension']
        return any(kw in name for kw in accessory_keywords)

    def get_stats(self) -> Dict:
        return {
            'cache': self.cache.stats(),
            'qdrant': self.qdrant.is_available
        }

if __name__ == "__main__":
    asyncio.run(FinBundleEngine().search("laptop", "test", 1000))
