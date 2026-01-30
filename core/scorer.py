"""
Learned Product Scorer
Multi-signal scoring with AFIG-aware weights for personalized ranking
"""
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ScoringWeights:
    """Learned weights for multi-signal fusion."""
    semantic: float = 0.4
    price_fit: float = 0.3
    quality: float = 0.2
    afig_alignment: float = 0.1
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'semantic': self.semantic,
            'price_fit': self.price_fit,
            'quality': self.quality,
            'afig_alignment': self.afig_alignment
        }


# Premium brands by category
PREMIUM_BRANDS = {
    'default': ['Apple', 'Samsung', 'Sony', 'Dell', 'Logitech', 'ASUS', 'LG', 'Bose'],
    'laptops': ['Apple', 'Dell', 'ASUS', 'Lenovo', 'HP', 'MSI', 'Razer'],
    'computers': ['Apple', 'Dell', 'ASUS', 'Lenovo', 'HP', 'MSI', 'Razer'],
    'monitors': ['LG', 'Samsung', 'Dell', 'ASUS', 'BenQ', 'Acer'],
    'keyboards': ['Logitech', 'Corsair', 'Razer', 'SteelSeries', 'Keychron'],
    'mice': ['Logitech', 'Razer', 'SteelSeries', 'Corsair', 'Zowie'],
    'headsets': ['Sony', 'Bose', 'SteelSeries', 'HyperX', 'Sennheiser'],
    'all electronics': ['Apple', 'Samsung', 'Sony', 'Dell', 'Logitech', 'ASUS', 'LG'],
}


class LearnedProductScorer:
    """
    Production-grade scorer combining:
    1. Vector similarity (semantic matching)
    2. Price fitness (budget-aware non-linear scoring)
    3. Quality signals (rating, brand)
    4. User preference alignment (AFIG)
    
    Weights are adapted per user archetype.
    """
    
    def __init__(self):
        # Archetype-specific weights (learned from conversion data)
        self.archetype_weights = {
            "budget_conscious": ScoringWeights(
                semantic=0.25,
                price_fit=0.50,  # Price matters most
                quality=0.15,
                afig_alignment=0.10
            ),
            "quality_seeker": ScoringWeights(
                semantic=0.30,
                price_fit=0.10,
                quality=0.45,  # Quality matters most
                afig_alignment=0.15
            ),
            "deal_hunter": ScoringWeights(
                semantic=0.35,
                price_fit=0.35,
                quality=0.20,
                afig_alignment=0.10
            ),
            "impulse_buyer": ScoringWeights(
                semantic=0.45,  # Match matters most
                price_fit=0.20,
                quality=0.25,
                afig_alignment=0.10
            ),
            "researcher": ScoringWeights(
                semantic=0.35,
                price_fit=0.20,
                quality=0.35,  # Quality & match balanced
                afig_alignment=0.10
            ),
            "default": ScoringWeights()
        }
    
    def get_weights(self, archetype: str) -> ScoringWeights:
        """Get scoring weights for archetype."""
        return self.archetype_weights.get(archetype, self.archetype_weights["default"])
    
    def score_product(
        self,
        product: Dict[str, Any],
        query_vec: np.ndarray,
        product_vec: np.ndarray,
        budget: float,
        user_afig: Dict[str, Any],
        qdrant_score: float = None
    ) -> Dict[str, Any]:
        """
        Compute multi-signal score for a product.
        
        Args:
            product: Product dict with price, rating, brand, category
            query_vec: Query embedding (384-dim, L2-normalized)
            product_vec: Product embedding (384-dim, L2-normalized)
            budget: User's budget
            user_afig: AFIG context dict
            qdrant_score: Pre-computed similarity from Qdrant (0-1 range)
            
        Returns:
            Dict with final_score and component scores
        """
        archetype = user_afig.get("archetype", "default")
        weights = self.get_weights(archetype)
        
        # Signal 1: Semantic similarity
        # Use Qdrant's pre-computed score if available (more accurate & faster)
        if qdrant_score is not None:
            # Qdrant cosine similarity for text embeddings typically ranges 0.3-0.7
            # A score of 0.6+ is an excellent match, 0.5 is good, 0.4 is okay
            # Normalize so: 0.35 → 0%, 0.45 → 50%, 0.55 → 75%, 0.65+ → 95%+
            # Using a curve that rewards high similarity more
            normalized = (qdrant_score - 0.35) / 0.35  # 0.35→0, 0.7→1
            # Apply slight boost curve to make good matches score higher
            semantic_score = max(0, min(1, normalized ** 0.7))  # Power < 1 boosts mid-range
        else:
            semantic_score = self._compute_semantic_score(query_vec, product_vec)
        
        # Signal 2: Price fit (non-linear budget-aware scoring)
        price_score = self._compute_price_fit(
            product.get("price", 0),
            budget,
            user_afig.get("risk_tolerance", 0.5)
        )
        
        # Signal 3: Quality score (rating + brand)
        quality_score = self._compute_quality_score(
            product.get("rating", 3.5),
            product.get("brand", ""),
            product.get("category", "default"),
            user_afig.get("brand_sensitivity", 0.5)
        )
        
        # Signal 4: AFIG alignment (preference fit)
        afig_score = self._compute_afig_alignment(product, user_afig)
        
        # Weighted fusion
        final_score = (
            weights.semantic * semantic_score +
            weights.price_fit * price_score +
            weights.quality * quality_score +
            weights.afig_alignment * afig_score
        )
        
        return {
            'final_score': round(final_score, 4),
            'semantic_score': round(semantic_score, 4),
            'price_score': round(price_score, 4),
            'quality_score': round(quality_score, 4),
            'afig_score': round(afig_score, 4),
            'weights_used': weights.to_dict(),
            'archetype': archetype
        }
    
    def score_products_batch(
        self,
        products: List[Dict[str, Any]],
        query_vec: np.ndarray,
        product_vecs: List[np.ndarray],
        budget: float,
        user_afig: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Score multiple products efficiently.
        
        Returns products with scores, sorted by final_score descending.
        """
        scored = []
        
        for product, product_vec in zip(products, product_vecs):
            scores = self.score_product(
                product, query_vec, product_vec, budget, user_afig
            )
            scored.append({
                **product,
                **scores
            })
        
        # Sort by final score
        scored.sort(key=lambda x: x['final_score'], reverse=True)
        
        return scored
    
    def _compute_semantic_score(
        self,
        query_vec: np.ndarray,
        product_vec: np.ndarray
    ) -> float:
        """
        Compute semantic similarity using dot product.
        
        Assumes vectors are L2-normalized, so dot product = cosine similarity.
        Range: [-1, 1] → rescaled to [0, 1]
        """
        if query_vec is None or product_vec is None:
            return 0.5  # Neutral score
        
        # Ensure vectors are numpy arrays
        query_vec = np.asarray(query_vec).flatten()
        product_vec = np.asarray(product_vec).flatten()
        
        # Handle dimension mismatch
        if len(query_vec) != len(product_vec):
            return 0.5
        
        # Dot product (for normalized vectors, this equals cosine similarity)
        similarity = float(np.dot(query_vec, product_vec))
        
        # Rescale from [-1, 1] to [0, 1]
        return (similarity + 1) / 2
    
    def _compute_price_fit(
        self,
        price: float,
        budget: float,
        risk_tolerance: float = 0.5
    ) -> float:
        """
        Non-linear price fitness scoring.
        
        Sweet spot: 50-90% of budget (get good value without underspending)
        Penalty above budget (risk-aware)
        Slight penalty below 50% (might be low quality)
        
        Args:
            price: Product price
            budget: User's budget
            risk_tolerance: 0-1, higher = more tolerant of over-budget
            
        Returns:
            Score in [0, 1]
        """
        if budget <= 0:
            return 0.5
        
        if price <= 0:
            return 0.3  # Free items suspicious
        
        ratio = price / budget
        
        if ratio <= 0.3:
            # Very cheap - might be low quality
            return 0.5 + 0.3 * (ratio / 0.3)
        
        elif ratio <= 0.5:
            # Cheap but reasonable
            return 0.8 + 0.2 * ((ratio - 0.3) / 0.2)
        
        elif ratio <= 0.9:
            # Sweet spot: 50-90% of budget
            return 1.0
        
        elif ratio <= 1.0:
            # Approaching budget limit (90-100%)
            return 1.0 - 0.2 * ((ratio - 0.9) / 0.1)
        
        elif ratio <= 1.2:
            # Slightly over budget (100-120%)
            # Risk-tolerant users penalized less
            overage = ratio - 1.0
            penalty = overage * (1.5 - risk_tolerance)
            return max(0.4, 0.8 - penalty)
        
        else:
            # Way over budget (>120%)
            return max(0.1, 0.4 - (ratio - 1.2) * 0.5)
    
    def _compute_quality_score(
        self,
        rating: float,
        brand: str,
        category: str,
        brand_sensitivity: float = 0.5
    ) -> float:
        """
        Quality scoring based on rating and brand.
        
        Args:
            rating: Product rating (1-5 stars)
            brand: Product brand name
            category: Product category
            brand_sensitivity: 0-1, how much user cares about brand
            
        Returns:
            Score in [0, 1]
        """
        # Base score from rating (normalize 1-5 to 0-1)
        if rating is None or rating < 1:
            rating_score = 0.5  # Neutral for missing
        else:
            # Map 1-5 stars to 0-1, with 3 stars = 0.5
            rating_score = max(0, min(1, (rating - 1) / 4))
        
        # Brand premium
        cat_key = category.lower() if category else 'default'
        premium_brands = PREMIUM_BRANDS.get(cat_key, PREMIUM_BRANDS['default'])
        
        brand_boost = 0.15 if brand and brand in premium_brands else 0
        
        # Weighted combination
        quality = rating_score + (brand_boost * brand_sensitivity)
        
        return min(1.0, quality)
    
    def _compute_afig_alignment(
        self,
        product: Dict[str, Any],
        user_afig: Dict[str, Any]
    ) -> float:
        """
        Compute how well product aligns with user's stable preferences.
        
        Args:
            product: Product dict
            user_afig: AFIG context
            
        Returns:
            Score in [0, 1]
        """
        score = 0.5  # Neutral baseline
        
        # Check category preference (from behavioral layer)
        behavioral = user_afig.get("behavioral", {})
        recent_categories = behavioral.get("recent_categories", [])
        product_category = product.get("category", "").lower()
        
        if any(cat.lower() in product_category or product_category in cat.lower() 
               for cat in recent_categories):
            score += 0.2
        
        # Check brand preference (from stable layer)
        stable = user_afig.get("stable", {})
        preferred_brands = stable.get("preferred_brands", [])
        product_brand = product.get("brand", "")
        
        if product_brand and product_brand in preferred_brands:
            score += 0.25
        
        # Check condition preference
        promo_sensitivity = stable.get("promo_sensitivity", 0.5)
        product_condition = product.get("condition", "new")
        
        if product_condition in ["refurbished", "open-box", "renewed"]:
            # Deal hunters like refurbished
            score += 0.1 * promo_sensitivity
        elif product_condition == "new":
            # Quality seekers prefer new
            score += 0.05 * (1 - promo_sensitivity)
        
        return min(1.0, score)
    
    def rerank_results(
        self,
        results: List[Dict[str, Any]],
        query_vec: np.ndarray,
        budget: float,
        user_afig: Dict[str, Any],
        embedder=None,
        boost_categories: List[str] = None,
        is_ambiguous: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Re-rank search results using multi-signal scoring.
        
        This is the main entry point for integrating with search engine.
        
        Args:
            results: List of product dicts from initial retrieval
            query_vec: Query embedding
            budget: User budget
            user_afig: AFIG context
            embedder: EmbeddingService for encoding product text (optional)
            boost_categories: Categories to boost from query disambiguation
            is_ambiguous: Whether query contains ambiguous terms
            
        Returns:
            Re-ranked results with scores
        """
        if not results:
            return []
        
        boost_categories = boost_categories or []
        
        # L2 normalize query vector
        if query_vec is not None:
            query_vec = np.asarray(query_vec)
            norm = np.linalg.norm(query_vec)
            if norm > 0:
                query_vec = query_vec / norm
        
        reranked = []
        
        for product in results:
            # Use pre-computed Qdrant similarity score if available (faster & more accurate)
            qdrant_score = product.get('_qdrant_score')
            product_vec = product.get('_vector')
            
            # If we have Qdrant score, use it directly for semantic similarity
            if qdrant_score is not None:
                # Qdrant score is already the cosine similarity, use it directly
                product_vec = None  # Skip embedding computation
            elif product_vec is None and embedder is not None:
                # Encode product text on-the-fly (slower fallback)
                product_text = f"{product.get('name', '')} {product.get('category', '')} {product.get('brand', '')}"
                product_vec = embedder.encode_query(product_text)
                # L2 normalize
                norm = np.linalg.norm(product_vec)
                if norm > 0:
                    product_vec = product_vec / norm
            
            # Score the product (pass qdrant_score for direct semantic scoring)
            scores = self.score_product(
                product=product,
                query_vec=query_vec,
                product_vec=product_vec,
                budget=budget,
                user_afig=user_afig,
                qdrant_score=qdrant_score  # Pass pre-computed similarity
            )
            
            # === CATEGORY BOOST/PENALTY FOR DISAMBIGUATION ===
            final_score = scores['final_score']
            category_adjustment = 0.0
            
            if boost_categories and is_ambiguous:
                product_category = product.get('category', '').lower()
                # Check if product matches any boost category
                category_match = any(
                    boost_cat.lower() in product_category or product_category in boost_cat.lower()
                    for boost_cat in boost_categories
                )
                if category_match:
                    # 15% boost for matching target category
                    category_adjustment = 0.15
                else:
                    # 15% penalty for non-matching when query is ambiguous
                    category_adjustment = -0.15
                
                final_score = max(0.0, min(1.0, final_score + category_adjustment))
                scores['category_adjustment'] = category_adjustment
                scores['final_score'] = round(final_score, 4)
            
            reranked.append({
                **product,
                'score': final_score,  # Override original score
                '_scoring': scores
            })
        
        # Sort by final score
        reranked.sort(key=lambda x: x['score'], reverse=True)
        
        return reranked


# Singleton instance
_scorer = None


def get_scorer() -> LearnedProductScorer:
    """Get singleton scorer instance."""
    global _scorer
    if _scorer is None:
        _scorer = LearnedProductScorer()
    return _scorer


if __name__ == "__main__":
    print("🧪 Testing LearnedProductScorer...")
    
    scorer = LearnedProductScorer()
    
    # Mock data
    product = {
        'name': 'ASUS ROG Gaming Laptop',
        'price': 1299,
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
        'risk_tolerance': 0.3,
        'brand_sensitivity': 0.8,
        'behavioral': {'recent_categories': ['laptops', 'monitors']},
        'stable': {'preferred_brands': ['ASUS', 'Dell']}
    }
    
    # Test scoring
    result = scorer.score_product(
        product, query_vec, product_vec, budget=1500, user_afig=user_afig
    )
    
    print(f"\n📊 Product: {product['name']}")
    print(f"   Final Score: {result['final_score']}")
    print(f"   Semantic: {result['semantic_score']}")
    print(f"   Price Fit: {result['price_score']}")
    print(f"   Quality: {result['quality_score']}")
    print(f"   AFIG: {result['afig_score']}")
    print(f"   Archetype: {result['archetype']}")
    print(f"   Weights: {result['weights_used']}")
    
    print("\n✅ LearnedProductScorer test complete!")
