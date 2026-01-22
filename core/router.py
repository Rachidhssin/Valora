"""
Query Router - Three-Path Routing for Optimal Latency
Routes queries to fast/smart/deep paths based on complexity and intent
"""
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class RoutePath(Enum):
    FAST = "fast"
    SMART = "smart"
    DEEP = "deep"


@dataclass
class RouteDecision:
    path: RoutePath
    confidence: float
    reason: str
    estimated_latency_ms: int


class QueryRouter:
    """
    Routes queries to appropriate processing path:
    - FAST: Precomputed, cached results (<100ms)
    - SMART: Vector search + light filtering (<300ms)
    - DEEP: Full optimization + agent (<1500ms)
    """
    
    # Keywords triggering different paths
    FAST_KEYWORDS = {
        'popular', 'trending', 'bestseller', 'best seller', 'top rated',
        'recommended', 'featured', 'new arrivals', 'deals', 'sale'
    }
    
    DEEP_KEYWORDS = {
        'setup', 'bundle', 'complete', 'build', 'workstation',
        'gaming rig', 'home office', 'studio', 'kit', 'combo',
        'all-in-one', 'package', 'together', 'compatible'
    }
    
    BUDGET_PATTERNS = [
        r'\$\s*(\d+)',                    # $500
        r'(\d+)\s*dollars?',              # 500 dollars
        r'under\s*\$?\s*(\d+)',           # under $500
        r'budget\s*(?:of\s*)?\$?\s*(\d+)', # budget of $500
        r'max(?:imum)?\s*\$?\s*(\d+)',    # max $500
        r'up\s*to\s*\$?\s*(\d+)',         # up to $500
        r'around\s*\$?\s*(\d+)',          # around $500
        r'about\s*\$?\s*(\d+)',           # about $500
        r'(\d+)\s*budget',                # 500 budget
    ]
    
    PRICE_KEYWORDS = {'cheap', 'affordable', 'budget', 'inexpensive', 'low cost', 'value'}
    QUALITY_KEYWORDS = {'best', 'premium', 'professional', 'high-end', 'quality', 'top'}
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self._budget_patterns = [re.compile(p, re.IGNORECASE) for p in self.BUDGET_PATTERNS]
    
    def route(self, query: str, budget: Optional[float] = None, 
              user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Route a query to the appropriate processing path.
        
        Args:
            query: User's search query
            budget: Optional explicit budget
            user_context: Optional AFIG-reconciled context
        
        Returns:
            Path name: "fast", "smart", or "deep"
        """
        decision = self.analyze(query, budget, user_context)
        return decision.path.value
    
    def analyze(self, query: str, budget: Optional[float] = None,
                user_context: Optional[Dict[str, Any]] = None) -> RouteDecision:
        """
        Analyze query and return detailed routing decision.
        """
        query_lower = query.lower().strip()
        
        # Check for fast path (precomputed queries)
        if self._is_fast_query(query_lower):
            return RouteDecision(
                path=RoutePath.FAST,
                confidence=0.9,
                reason="Matches precomputed query pattern",
                estimated_latency_ms=50
            )
        
        # Check for deep path triggers
        deep_score = self._compute_deep_score(query_lower, budget, user_context)
        
        if deep_score >= 0.7:
            return RouteDecision(
                path=RoutePath.DEEP,
                confidence=deep_score,
                reason=f"Bundle/setup query with budget constraints",
                estimated_latency_ms=1200
            )
        
        # Check for extracted budget in query
        extracted_budget = self._extract_budget(query_lower)
        if extracted_budget and extracted_budget > 500:
            return RouteDecision(
                path=RoutePath.DEEP,
                confidence=0.75,
                reason=f"High budget query (${extracted_budget})",
                estimated_latency_ms=1000
            )
        
        # Default to smart path
        return RouteDecision(
            path=RoutePath.SMART,
            confidence=0.8,
            reason="Standard product search",
            estimated_latency_ms=250
        )
    
    def _is_fast_query(self, query: str) -> bool:
        """Check if query matches fast/precomputed patterns."""
        for keyword in self.FAST_KEYWORDS:
            if keyword in query:
                return True
        
        # Very short, generic queries
        words = query.split()
        if len(words) <= 2 and not self._extract_budget(query):
            # Single category queries
            categories = {'laptop', 'laptops', 'monitor', 'monitors', 'keyboard', 
                         'keyboards', 'mouse', 'mice', 'headset', 'headsets',
                         'gpu', 'gpus', 'graphics card', 'chair', 'chairs', 
                         'desk', 'desks', 'webcam', 'webcams', 'speaker', 'speakers'}
            if any(cat in query for cat in categories):
                return True
        
        return False
    
    def _compute_deep_score(self, query: str, budget: Optional[float],
                           user_context: Optional[Dict[str, Any]]) -> float:
        """Compute likelihood that query needs deep processing."""
        score = 0.0
        
        # Check for bundle/setup keywords
        deep_keyword_count = sum(1 for kw in self.DEEP_KEYWORDS if kw in query)
        score += min(0.5, deep_keyword_count * 0.15)
        
        # Check for explicit budget
        if budget and budget > 300:
            score += 0.2
        
        extracted_budget = self._extract_budget(query)
        if extracted_budget and extracted_budget > 300:
            score += 0.2
        
        # Check for multi-item signals
        multi_item_patterns = [
            r'and\s+a?\s*\w+',      # "laptop and monitor"
            r'with\s+a?\s*\w+',     # "desk with chair"
            r'plus\s+a?\s*\w+',     # "keyboard plus mouse"
            r',\s*\w+',              # "laptop, mouse, keyboard"
        ]
        for pattern in multi_item_patterns:
            if re.search(pattern, query):
                score += 0.15
                break
        
        # User context signals
        if user_context:
            if user_context.get('mission'):
                score += 0.1
            if user_context.get('archetype') in ['budget_conscious', 'value_balanced']:
                score += 0.1  # These users benefit most from optimization
        
        return min(1.0, score)
    
    def _extract_budget(self, query: str) -> Optional[float]:
        """Extract budget amount from query."""
        for pattern in self._budget_patterns:
            match = pattern.search(query)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
        return None
    
    def get_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Extract structured intent from query.
        Useful for downstream processing.
        """
        query_lower = query.lower()
        
        intent = {
            'raw_query': query,
            'budget': self._extract_budget(query_lower),
            'is_bundle': any(kw in query_lower for kw in self.DEEP_KEYWORDS),
            'price_sensitive': any(kw in query_lower for kw in self.PRICE_KEYWORDS),
            'quality_focused': any(kw in query_lower for kw in self.QUALITY_KEYWORDS),
            'categories': self._extract_categories(query_lower),
            'brands': self._extract_brands(query_lower)
        }
        
        return intent
    
    def _extract_categories(self, query: str) -> list:
        """Extract product categories from query."""
        category_map = {
            'laptop': 'laptops', 'notebook': 'laptops', 'ultrabook': 'laptops',
            'monitor': 'monitors', 'display': 'monitors', 'screen': 'monitors',
            'keyboard': 'keyboards', 'keeb': 'keyboards',
            'mouse': 'mice', 'mice': 'mice',
            'headset': 'headsets', 'headphone': 'headsets',
            'gpu': 'gpus', 'graphics card': 'gpus', 'video card': 'gpus',
            'webcam': 'webcams', 'camera': 'webcams',
            'speaker': 'speakers',
            'desk': 'desks', 'table': 'desks',
            'chair': 'chairs', 'seat': 'chairs'
        }
        
        found = set()
        for keyword, category in category_map.items():
            if keyword in query:
                found.add(category)
        
        return list(found)
    
    def _extract_brands(self, query: str) -> list:
        """Extract brand names from query."""
        brands = [
            'logitech', 'corsair', 'razer', 'dell', 'hp', 'asus', 'samsung',
            'lg', 'acer', 'msi', 'steelseries', 'hyperx', 'nvidia', 'amd',
            'intel', 'apple', 'lenovo', 'benq', 'zowie', 'secretlab',
            'herman miller', 'keychron', 'ducky', 'glorious', 'elgato'
        ]
        
        found = []
        for brand in brands:
            if brand in query:
                found.append(brand.title())
        
        return found


# Test the router
if __name__ == "__main__":
    router = QueryRouter()
    
    test_queries = [
        ("laptop", None),
        ("trending monitors", None),
        ("gaming setup $1500", 1500),
        ("cheap keyboard", None),
        ("complete home office with desk chair and monitor budget of $800", 800),
        ("rtx 4070 graphics card", None),
        ("best professional headset for streaming", None),
    ]
    
    print("🧪 Query Router Test Results:\n")
    for query, budget in test_queries:
        decision = router.analyze(query, budget)
        print(f"Query: \"{query}\"")
        print(f"  → Path: {decision.path.value.upper()}")
        print(f"  → Confidence: {decision.confidence:.2f}")
        print(f"  → Reason: {decision.reason}")
        print(f"  → Est. Latency: {decision.estimated_latency_ms}ms")
        print()
