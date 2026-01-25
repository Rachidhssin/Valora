"""
Query Router - Three-Path Routing for Optimal Latency
Routes queries to fast/smart/deep paths based on complexity and intent.
"""
import re
import hashlib
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
    complexity_score: float


class QueryRouter:
    """
    Routes queries to appropriate processing path based on complexity:
    - FAST (<0.3): Precomputed/Cached (<100ms)
    - SMART (<0.7): Standard Vector Search (<300ms)
    - DEEP (>=0.7): Optimization + Agent (<1000ms)
    """
    
    # Keywords triggering complexity
    COMPLEX_KEYWORDS = {
        'setup', 'bundle', 'complete', 'build', 'workstation',
        'gaming rig', 'home office', 'studio', 'kit', 'combo',
        'all-in-one', 'package', 'together', 'compatible', 
        'vs', 'versus', 'compare', 'difference'
    }
    
    # Keywords implying simple lookups
    SIMPLE_KEYWORDS = {
        'popular', 'trending', 'bestseller', 'best seller', 'top rated',
        'recommended', 'featured', 'new arrivals', 'deals', 'sale',
        'price', 'cost'
    }
    
    BUDGET_PATTERNS = [
        r'\$\s*(\d+)',                    # $500
        r'(\d+)\s*dollars?',              # 500 dollars
        r'under\s*\$?\s*(\d+)',           # under $500
        r'budget\s*(?:of\s*)?\$?\s*(\d+)', # budget of $500
        r'max(?:imum)?\s*\$?\s*(\d+)',    # max $500
        r'up\s*to\s*\$?\s*(\d+)',         # up to $500
    ]
    
    def __init__(self):
        # Compile regex patterns
        self._budget_patterns = [re.compile(p, re.IGNORECASE) for p in self.BUDGET_PATTERNS]

    def route(self, query: str, budget: Optional[float] = None, 
              user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Route a query to the appropriate processing path.
        """
        decision = self.analyze(query, budget, user_context)
        return decision.path.value

    def analyze(self, query: str, budget: Optional[float] = None,
                user_context: Optional[Dict[str, Any]] = None) -> RouteDecision:
        """
        Analyze query and return detailed routing decision with complexity score.
        """
        complexity = self.estimate_complexity(query, budget)
        
        # Decide path based on complexity thresholds
        if complexity < 0.3:
            return RouteDecision(
                path=RoutePath.FAST,
                confidence=0.9,
                reason="Low complexity query",
                estimated_latency_ms=50,
                complexity_score=complexity
            )
        elif complexity < 0.7:
             return RouteDecision(
                path=RoutePath.SMART,
                confidence=0.8,
                reason="Standard complexity query",
                estimated_latency_ms=250,
                complexity_score=complexity
            )
        else:
            return RouteDecision(
                path=RoutePath.DEEP,
                confidence=0.85,
                reason="High complexity/Mult-intent query",
                estimated_latency_ms=1000,
                complexity_score=complexity
            )

    def estimate_complexity(self, query: str, budget: Optional[float] = None) -> float:
        """
        Estimate query complexity score (0.0 to 1.0).
        
        Factors:
        - Length: Longer queries -> higher complexity
        - Keywords: "bundle", "setup" -> high complexity
        - Specificity: more entity types -> higher complexity
        - Budget: Explicit budget -> medium complexity increase
        """
        query_lower = query.lower().strip()
        score = 0.0
        
        # 1. Base complexity from length (words)
        words = query_lower.split()
        if len(words) <= 2:
            score += 0.1
        elif len(words) <= 5:
            score += 0.3
        else:
            score += 0.5
            
        # 2. Keyword analysis
        complex_hits = sum(1 for w in words if w in self.COMPLEX_KEYWORDS)
        simple_hits = sum(1 for w in words if w in self.SIMPLE_KEYWORDS)
        
        score += (complex_hits * 0.2)
        score -= (simple_hits * 0.1)
        
        # 3. Budget presence
        extracted_budget = self._extract_budget(query_lower)
        if budget or extracted_budget:
            score += 0.15
            
        # 4. Entity density (approximate)
        # Check for multi-item connectors
        if ' and ' in query_lower or ' with ' in query_lower:
            score += 0.15
            
        # Clamp score 0.0 to 1.0
        return max(0.0, min(1.0, score))

    def get_cache_key(self, query: str, budget: float, archetype: str) -> str:
        """
        Generate deterministic cache key for Fast Path.
        Format: fast:hash(query):budget_tier:archetype
        """
        # Normalize inputs
        q_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()[:8]
        
        # Bucket budget to reduce sparsity (e.g. 100, 200, 300...)
        budget_tier = int(round(budget / 100) * 100) if budget else 0
        
        return f"fast:{q_hash}:{budget_tier}:{archetype}"

    def get_query_intent(self, query: str) -> Dict[str, Any]:
        """Extract structured intent from query."""
        query_lower = query.lower()
        return {
            'raw_query': query,
            'budget': self._extract_budget(query_lower),
            'is_bundle': any(kw in query_lower for kw in self.COMPLEX_KEYWORDS),
            'categories': self._extract_categories(query_lower),
            'brands': self._extract_brands(query_lower)
        }

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

    def _extract_categories(self, query: str) -> list:
        """Extract product categories from query."""
        category_map = {
            'laptop': 'laptops', 'monitor': 'monitors', 'keyboard': 'keyboards',
            'mouse': 'mice', 'headset': 'headsets', 'gpu': 'gpus', 
            'webcam': 'webcams', 'speaker': 'speakers', 'desk': 'desks', 'chair': 'chairs'
        }
        found = set()
        for keyword, category in category_map.items():
            if keyword in query:
                found.add(category)
        return list(found)

    def _extract_brands(self, query: str) -> list:
        brands = ['logitech', 'corsair', 'razer', 'dell', 'hp', 'asus', 'samsung', 
                  'lg', 'acer', 'msi', 'nvidia', 'amd', 'intel', 'apple']
        return [b.title() for b in brands if b in query]

# Verification
if __name__ == "__main__":
    router = QueryRouter()
    print("🧪 Testing Router Complexity Estimation:")
    
    cases = [
        ("laptop", 1000),                # Simple -> Fast
        ("gaming mouse", 50),            # Standard -> Smart
        ("gaming setup under $1500", 1500), # Complex -> Deep
        ("complete home office bundle", 2000) # Complex -> Deep
    ]
    
    for q, b in cases:
        decision = router.analyze(q, b)
        print(f"Query: '{q}' | Score: {decision.complexity_score:.2f} | Path: {decision.path.value.upper()}")
