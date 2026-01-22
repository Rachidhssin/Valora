"""
Feasibility Gate
Filters candidates based on hard and soft constraints
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class FeasibilityResult:
    """Result of feasibility check."""
    is_feasible: bool
    violations: List[str]
    adjusted_utility: float
    penalty: float


class FeasibilityGate:
    """
    Filter products based on hard constraints (must satisfy)
    and soft constraints (prefer but allow violations with penalty).
    """
    
    # Hard constraint violation = product excluded
    HARD_CONSTRAINTS = ['budget', 'in_stock', 'category_match']
    
    # Soft constraint violation = utility penalty
    SOFT_CONSTRAINTS = {
        'brand_preference': 0.1,    # 10% utility penalty
        'rating_threshold': 0.15,   # 15% penalty
        'condition_preference': 0.2, # 20% penalty for non-preferred condition
        'shipping_time': 0.05       # 5% penalty per extra day
    }
    
    def __init__(self, 
                 default_min_rating: float = 3.5,
                 default_preferred_conditions: List[str] = None):
        self.default_min_rating = default_min_rating
        self.default_preferred_conditions = default_preferred_conditions or ['new', 'open-box']
    
    def filter_candidates(self, candidates: List[Dict], 
                         user_context: Dict[str, Any],
                         budget: float,
                         required_categories: Optional[List[str]] = None) -> List[Dict]:
        """
        Filter candidates through feasibility gate.
        
        Args:
            candidates: List of product dicts (from Qdrant search)
            user_context: AFIG reconciled context
            budget: User's budget
            required_categories: Categories that must be included (for bundles)
            
        Returns:
            Filtered and re-ranked list of feasible candidates
        """
        feasible = []
        
        for candidate in candidates:
            result = self.check_feasibility(candidate, user_context, budget)
            
            if result.is_feasible:
                # Attach feasibility metadata
                candidate_copy = candidate.copy() if isinstance(candidate, dict) else candidate.to_dict()
                candidate_copy['_feasibility'] = {
                    'adjusted_utility': result.adjusted_utility,
                    'penalty': result.penalty,
                    'violations': result.violations
                }
                feasible.append(candidate_copy)
        
        # Sort by adjusted utility
        feasible.sort(key=lambda x: x.get('_feasibility', {}).get('adjusted_utility', 0), reverse=True)
        
        return feasible
    
    def check_feasibility(self, product: Dict, 
                         user_context: Dict[str, Any],
                         budget: float) -> FeasibilityResult:
        """
        Check if a single product passes feasibility.
        
        Returns:
            FeasibilityResult with pass/fail and details
        """
        violations = []
        penalty = 0.0
        
        # Get product data (handle both dict and object)
        if hasattr(product, 'to_dict'):
            p = product.to_dict()
        elif hasattr(product, '__dict__'):
            p = product.__dict__
        else:
            p = product
        
        price = p.get('price', 0)
        in_stock = p.get('in_stock', True)
        rating = p.get('rating', 4.0)
        condition = p.get('condition', 'new')
        brand = p.get('brand', '')
        
        # === HARD CONSTRAINTS ===
        
        # Budget constraint (per-item check - allow items up to 50% of budget for bundles)
        max_single_item = budget * 0.5
        if price > budget:
            violations.append(f"HARD: Price ${price:.2f} exceeds budget ${budget:.2f}")
            return FeasibilityResult(
                is_feasible=False,
                violations=violations,
                adjusted_utility=0,
                penalty=1.0
            )
        
        # Stock constraint
        if not in_stock:
            violations.append("HARD: Product out of stock")
            return FeasibilityResult(
                is_feasible=False,
                violations=violations,
                adjusted_utility=0,
                penalty=1.0
            )
        
        # === SOFT CONSTRAINTS ===
        
        # Rating threshold
        min_rating = user_context.get('min_rating', self.default_min_rating)
        if rating < min_rating:
            violations.append(f"SOFT: Rating {rating} below threshold {min_rating}")
            penalty += self.SOFT_CONSTRAINTS['rating_threshold']
        
        # Condition preference
        preferred_conditions = user_context.get('preferred_conditions', self.default_preferred_conditions)
        if condition not in preferred_conditions:
            # Check if user is budget conscious (more accepting of refurb)
            if user_context.get('archetype') == 'budget_conscious' and condition == 'refurbished':
                # Reduced penalty for budget-conscious users
                penalty += self.SOFT_CONSTRAINTS['condition_preference'] * 0.5
            else:
                violations.append(f"SOFT: Condition '{condition}' not preferred")
                penalty += self.SOFT_CONSTRAINTS['condition_preference']
        
        # Brand preference
        brand_preferences = user_context.get('brand_preferences', {})
        if brand_preferences and brand in brand_preferences:
            brand_score = brand_preferences[brand]
            if brand_score < 0.5:
                violations.append(f"SOFT: Brand '{brand}' has low preference ({brand_score:.2f})")
                penalty += self.SOFT_CONSTRAINTS['brand_preference'] * (1 - brand_score)
        
        # Calculate base utility (composite score)
        base_utility = self._compute_base_utility(p, user_context)
        
        # Apply penalty
        adjusted_utility = base_utility * (1 - min(penalty, 0.5))  # Cap penalty at 50%
        
        return FeasibilityResult(
            is_feasible=True,
            violations=violations,
            adjusted_utility=round(adjusted_utility, 4),
            penalty=round(penalty, 4)
        )
    
    def _compute_base_utility(self, product: Dict, user_context: Dict) -> float:
        """
        Compute base utility score for a product.
        Considers relevance, rating, price efficiency, and user preferences.
        """
        score = product.get('score', 0.5)  # Similarity score from search
        rating = product.get('rating', 4.0)
        price = product.get('price', 100)
        category = product.get('category', '')
        
        # Normalize components
        relevance = score  # Already 0-1 from cosine similarity
        quality = rating / 5.0  # Normalize to 0-1
        
        # Price efficiency (lower price = higher efficiency, but don't reward too cheap)
        # Use sigmoid-like curve
        price_norm = min(1.0, max(0.2, 1 - (price / 2000)))
        
        # Category preference
        category_prefs = user_context.get('category_preferences', {})
        category_boost = category_prefs.get(category, 0.5)
        
        # Archetype adjustments
        archetype = user_context.get('archetype', 'value_balanced')
        
        if archetype == 'budget_conscious':
            # Weight price efficiency higher
            weights = {'relevance': 0.25, 'quality': 0.2, 'price': 0.4, 'category': 0.15}
        elif archetype == 'quality_seeker':
            # Weight quality higher
            weights = {'relevance': 0.3, 'quality': 0.4, 'price': 0.1, 'category': 0.2}
        else:
            # Balanced
            weights = {'relevance': 0.35, 'quality': 0.25, 'price': 0.25, 'category': 0.15}
        
        utility = (
            weights['relevance'] * relevance +
            weights['quality'] * quality +
            weights['price'] * price_norm +
            weights['category'] * category_boost
        )
        
        return min(1.0, max(0.0, utility))
    
    def get_category_budget_allocation(self, categories: List[str], 
                                       total_budget: float,
                                       user_context: Dict) -> Dict[str, float]:
        """
        Allocate budget across categories for bundle optimization.
        
        Returns:
            Dict mapping category to allocated budget
        """
        # Default allocation weights
        default_weights = {
            'laptops': 0.40,
            'gpus': 0.35,
            'monitors': 0.25,
            'keyboards': 0.08,
            'mice': 0.05,
            'headsets': 0.10,
            'webcams': 0.08,
            'speakers': 0.10,
            'desks': 0.20,
            'chairs': 0.25
        }
        
        # Adjust based on user preferences
        prefs = user_context.get('category_preferences', {})
        
        weights = {}
        for cat in categories:
            base = default_weights.get(cat, 0.1)
            pref_boost = prefs.get(cat, 0.5) - 0.5  # -0.5 to +0.5
            weights[cat] = max(0.05, base + pref_boost * 0.1)
        
        # Normalize
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # Convert to budget
        return {cat: total_budget * weight for cat, weight in weights.items()}


if __name__ == "__main__":
    print("🧪 Testing Feasibility Gate...")
    
    gate = FeasibilityGate()
    
    # Test products
    products = [
        {
            'product_id': 'prod_001',
            'name': 'Gaming Laptop RTX 4070',
            'category': 'laptops',
            'brand': 'ASUS',
            'price': 1299,
            'rating': 4.7,
            'score': 0.85,
            'condition': 'new',
            'in_stock': True
        },
        {
            'product_id': 'prod_002',
            'name': 'Budget Laptop',
            'category': 'laptops',
            'brand': 'Acer',
            'price': 499,
            'rating': 3.2,
            'score': 0.72,
            'condition': 'refurbished',
            'in_stock': True
        },
        {
            'product_id': 'prod_003',
            'name': 'Out of Stock Laptop',
            'category': 'laptops',
            'brand': 'Dell',
            'price': 899,
            'rating': 4.5,
            'score': 0.90,
            'condition': 'new',
            'in_stock': False
        }
    ]
    
    user_context = {
        'archetype': 'value_balanced',
        'category_preferences': {'laptops': 0.8},
        'brand_preferences': {'ASUS': 0.9, 'Acer': 0.4}
    }
    
    budget = 1500
    
    print(f"\n📊 Testing with budget ${budget}")
    for product in products:
        result = gate.check_feasibility(product, user_context, budget)
        print(f"\n{product['name']}:")
        print(f"   Feasible: {result.is_feasible}")
        print(f"   Adjusted Utility: {result.adjusted_utility}")
        print(f"   Penalty: {result.penalty}")
        if result.violations:
            print(f"   Violations: {result.violations}")
    
    # Test filter
    filtered = gate.filter_candidates(products, user_context, budget)
    print(f"\n📊 Filtered results: {len(filtered)} of {len(products)} products passed")
    
    print("\n✅ Feasibility gate test complete!")
