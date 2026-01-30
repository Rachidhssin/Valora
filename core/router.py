"""
Query Router - Hybrid LLM + Regex Routing
Uses Groq LLM for intelligent routing with regex fallback.
"""
import os
import re
import json
import hashlib
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


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
    routing_method: str = "regex"  # "llm" or "regex"


class QueryRouter:
    """
    Hybrid router combining LLM intelligence with regex speed.
    
    Strategy:
    1. Check regex for obvious fast-path queries (simple lookups)
    2. Use LLM for ambiguous queries that need semantic understanding
    3. Fall back to regex if LLM fails or is unavailable
    
    Paths:
    - FAST: Precomputed/Cached (<100ms) - popular, trending, simple category
    - SMART: Vector Search (<300ms) - specific product searches
    - DEEP: Optimization + Agent (<1000ms) - bundles, comparisons, complex needs
    """
    
    # LLM System Prompt for routing decisions
    LLM_SYSTEM_PROMPT = """You are a query router for a product search engine. Analyze the user's search query and decide the best processing path.

PATHS:
- FAST: Use for simple generic lookups like "popular laptops", "trending phones", "bestsellers", "top rated monitors". These don't need semantic understanding.
- SMART: Use for specific product searches with attributes like "gaming laptop under $1000", "wireless noise-cancelling headphones", "4K monitor for photo editing". These need semantic/vector search.
- DEEP: Use for complex multi-item requests like "complete gaming setup", "home office bundle", "streaming kit with camera and microphone", or comparison queries like "laptop vs desktop for gaming". These need optimization and bundling.

Respond with ONLY valid JSON (no markdown):
{"path": "fast|smart|deep", "reason": "brief 5-10 word explanation", "confidence": 0.0-1.0}"""

    # Keywords for regex-based fast detection
    FAST_KEYWORDS = {
        'popular', 'trending', 'bestseller', 'best seller', 'top rated',
        'recommended', 'featured', 'new arrivals', 'deals', 'sale',
        'top 10', 'best selling', 'hot', 'most popular'
    }
    
    # Keywords triggering deep path (bundles, complex)
    DEEP_KEYWORDS = {
        'setup', 'bundle', 'complete', 'build', 'workstation',
        'gaming rig', 'home office', 'studio', 'kit', 'combo',
        'all-in-one', 'package', 'together', 'compatible', 
        'vs', 'versus', 'compare', 'comparison', 'difference',
        'everything for', 'full set', 'starter kit'
    }
    
    # Product attribute keywords (needs smart/semantic search)
    PRODUCT_KEYWORDS = {
        'gaming', 'professional', 'budget', 'cheap', 'best', 'good',
        'lightweight', 'portable', 'powerful', 'fast', 'slim', 'thin',
        'wireless', 'mechanical', 'rgb', 'ergonomic', '4k', 'hd', '1080p',
        'bluetooth', 'usb-c', 'thunderbolt', 'quiet', 'silent', 'loud',
        'waterproof', 'durable', 'premium', 'entry-level', 'high-end'
    }
    
    # Common product categories - direct to SMART with high confidence
    PRODUCT_CATEGORIES = {
        'laptop', 'laptops', 'notebook', 'computer', 'pc', 'desktop',
        'monitor', 'monitors', 'display', 'screen', 'tv', 'tvs', 'television',
        'keyboard', 'keyboards', 'mouse', 'mice', 'trackpad',
        'headphones', 'headphone', 'earbuds', 'earphone', 'headset',
        'speaker', 'speakers', 'soundbar', 'audio',
        'webcam', 'camera', 'cameras', 'microphone', 'mic',
        'phone', 'smartphone', 'tablet', 'tablets', 'ipad',
        'printer', 'scanner', 'router', 'modem', 'wifi',
        'ssd', 'hdd', 'storage', 'drive', 'usb', 'hub',
        'charger', 'cable', 'cables', 'adapter', 'dock', 'stand',
        'gpu', 'graphics', 'ram', 'memory', 'cpu', 'processor'
    }
    
    BUDGET_PATTERNS = [
        r'\$\s*(\d+)',                    # $500
        r'(\d+)\s*dollars?',              # 500 dollars
        r'under\s*\$?\s*(\d+)',           # under $500
        r'budget\s*(?:of\s*)?\$?\s*(\d+)', # budget of $500
        r'max(?:imum)?\s*\$?\s*(\d+)',    # max $500
        r'up\s*to\s*\$?\s*(\d+)',         # up to $500
    ]
    
    def __init__(self, use_llm: bool = True, llm_timeout: float = 2.0):
        """
        Initialize the hybrid router.
        
        Args:
            use_llm: Whether to use LLM for routing (requires GROQ_API_KEY)
            llm_timeout: Max time to wait for LLM response before fallback
        """
        self.use_llm = use_llm
        self.llm_timeout = llm_timeout
        self._groq_client = None
        self._route_cache: Dict[str, RouteDecision] = {}  # In-memory cache
        self._budget_patterns = [re.compile(p, re.IGNORECASE) for p in self.BUDGET_PATTERNS]
        
        self._init_groq()
    
    def _init_groq(self):
        """Initialize Groq client if available."""
        if not self.use_llm:
            return
            
        if not GROQ_AVAILABLE:
            print("⚠️ groq package not installed, using regex-only routing")
            return
            
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("⚠️ GROQ_API_KEY not set, using regex-only routing")
            return
            
        try:
            self._groq_client = Groq(api_key=api_key)
            print("✅ Groq LLM router initialized")
        except Exception as e:
            print(f"⚠️ Groq init failed: {e}, using regex-only routing")

    def route(self, query: str, budget: Optional[float] = None, 
              user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Route a query to the appropriate processing path.
        
        Returns:
            Path name: "fast", "smart", or "deep"
        """
        decision = self.analyze(query, budget, user_context)
        return decision.path.value

    def analyze(self, query: str, budget: Optional[float] = None,
                user_context: Optional[Dict[str, Any]] = None) -> RouteDecision:
        """
        Analyze query using hybrid LLM + regex approach.
        
        Strategy:
        1. Check cache first
        2. If query is obviously simple (fast keywords), use regex
        3. If query is obviously complex (deep keywords), use regex
        4. For ambiguous queries, use LLM
        5. Fall back to regex if LLM fails
        """
        query_lower = query.lower().strip()
        
        # 1. Check cache
        cache_key = self._get_route_cache_key(query_lower, budget)
        if cache_key in self._route_cache:
            cached = self._route_cache[cache_key]
            return RouteDecision(
                path=cached.path,
                confidence=cached.confidence,
                reason=f"[cached] {cached.reason}",
                estimated_latency_ms=cached.estimated_latency_ms,
                complexity_score=cached.complexity_score,
                routing_method="cached"
            )
        
        # 2. Quick regex check for obvious cases
        regex_decision = self._regex_route(query_lower, budget)
        
        # If regex is highly confident (obvious fast or deep), use it directly
        if regex_decision.confidence >= 0.9:
            self._route_cache[cache_key] = regex_decision
            print(f"⚡ Regex routed '{query[:30]}' -> {regex_decision.path.value.upper()} ({regex_decision.reason})")
            return regex_decision
        
        # 3. For ambiguous queries, try LLM
        if self._groq_client:
            try:
                llm_decision = self._llm_route(query, budget)
                self._route_cache[cache_key] = llm_decision
                return llm_decision
            except Exception as e:
                print(f"⚠️ LLM routing failed: {e}, using regex fallback")
        
        # 4. Fall back to regex
        self._route_cache[cache_key] = regex_decision
        return regex_decision
    
    def _llm_route(self, query: str, budget: Optional[float]) -> RouteDecision:
        """
        Use Groq LLM for intelligent query routing.
        
        Uses llama-3.1-8b-instant for fast inference (~100-200ms).
        """
        start_time = time.time()
        
        # Build user message
        user_msg = f"Query: \"{query}\""
        if budget:
            user_msg += f"\nUser budget: ${budget}"
        
        response = self._groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": self.LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            temperature=0,
            max_tokens=100
        )
        
        # Parse LLM response
        content = response.choices[0].message.content.strip()
        
        # Handle potential markdown wrapping
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        result = json.loads(content)
        
        path_str = result.get("path", "smart").lower()
        path = RoutePath(path_str)
        confidence = float(result.get("confidence", 0.8))
        reason = result.get("reason", "LLM decision")
        
        latency_map = {"fast": 50, "smart": 250, "deep": 1000}
        complexity_map = {"fast": 0.2, "smart": 0.5, "deep": 0.85}
        
        llm_latency = (time.time() - start_time) * 1000
        print(f"🧠 LLM routed '{query[:30]}...' -> {path_str.upper()} ({llm_latency:.0f}ms)")
        
        return RouteDecision(
            path=path,
            confidence=confidence,
            reason=reason,
            estimated_latency_ms=latency_map.get(path_str, 250),
            complexity_score=complexity_map.get(path_str, 0.5),
            routing_method="llm"
        )
    
    def _regex_route(self, query_lower: str, budget: Optional[float]) -> RouteDecision:
        """
        Regex-based routing for fast fallback.
        
        Returns decision with confidence score indicating how certain we are.
        High confidence (>=0.9) means we skip LLM.
        """
        words = set(query_lower.split())
        
        # Check for obvious FAST path (simple lookups)
        fast_hits = sum(1 for kw in self.FAST_KEYWORDS if kw in query_lower)
        if fast_hits > 0 and len(words) <= 4:
            return RouteDecision(
                path=RoutePath.FAST,
                confidence=0.95,  # High confidence, skip LLM
                reason="Simple lookup query",
                estimated_latency_ms=50,
                complexity_score=0.15,
                routing_method="regex"
            )
        
        # Check if query contains a product category FIRST (high confidence)
        # This prevents "tvs" from matching "vs" in DEEP_KEYWORDS
        category_hits = sum(1 for cat in self.PRODUCT_CATEGORIES if cat in words)
        if category_hits > 0:
            return RouteDecision(
                path=RoutePath.SMART,
                confidence=0.95,  # High confidence, skip LLM
                reason="Product category search",
                estimated_latency_ms=250,
                complexity_score=0.5,
                routing_method="regex"
            )
        
        # Check for obvious DEEP path (bundles, complex)
        # Use word boundary matching to avoid "tvs" matching "vs"
        deep_hits = sum(1 for kw in self.DEEP_KEYWORDS if f' {kw} ' in f' {query_lower} ' or query_lower.startswith(f'{kw} ') or query_lower.endswith(f' {kw}') or query_lower == kw)
        has_multi_item = ' and ' in query_lower or ' with ' in query_lower
        if deep_hits > 0 or (has_multi_item and len(words) > 5):
            return RouteDecision(
                path=RoutePath.DEEP,
                confidence=0.9,  # High confidence
                reason="Complex/bundle query",
                estimated_latency_ms=1000,
                complexity_score=0.85,
                routing_method="regex"
            )
        
        # Check for SMART path (product attributes)
        product_hits = sum(1 for kw in self.PRODUCT_KEYWORDS if kw in query_lower)
        has_budget = budget is not None or self._extract_budget(query_lower) is not None
        
        if product_hits > 0 or has_budget:
            # Higher confidence when we have product attributes
            confidence = 0.85 + (product_hits * 0.05)  # Boost to 0.9+
            return RouteDecision(
                path=RoutePath.SMART,
                confidence=min(confidence, 0.95),
                reason="Specific product search",
                estimated_latency_ms=250,
                complexity_score=0.5,
                routing_method="regex"
            )
        
        # Default: ambiguous query, low confidence (will trigger LLM)
        return RouteDecision(
            path=RoutePath.SMART,
            confidence=0.5,  # Low confidence, use LLM if available
            reason="Ambiguous query",
            estimated_latency_ms=250,
            complexity_score=0.4,
            routing_method="regex"
        )
    
    def _get_route_cache_key(self, query: str, budget: Optional[float]) -> str:
        """Generate cache key for routing decisions."""
        budget_tier = int(round(budget / 500) * 500) if budget else 0
        return f"{query}:{budget_tier}"

    def get_cache_key(self, query: str, budget: float, archetype: str) -> str:
        """
        Generate deterministic cache key for Fast Path results.
        Format: fast:hash(query):budget_tier:archetype
        """
        q_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()[:8]
        budget_tier = int(round(budget / 100) * 100) if budget else 0
        return f"fast:{q_hash}:{budget_tier}:{archetype}"

    def get_query_intent(self, query: str) -> Dict[str, Any]:
        """Extract structured intent from query."""
        query_lower = query.lower()
        return {
            'raw_query': query,
            'budget': self._extract_budget(query_lower),
            'is_bundle': any(kw in query_lower for kw in self.DEEP_KEYWORDS),
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
            'webcam': 'webcams', 'speaker': 'speakers', 'desk': 'desks', 
            'chair': 'chairs', 'phone': 'phones', 'tablet': 'tablets',
            'camera': 'cameras', 'headphone': 'headphones'
        }
        found = set()
        for keyword, category in category_map.items():
            if keyword in query:
                found.add(category)
        return list(found)

    def _extract_brands(self, query: str) -> list:
        """Extract brand names from query."""
        brands = ['logitech', 'corsair', 'razer', 'dell', 'hp', 'asus', 'samsung', 
                  'lg', 'acer', 'msi', 'nvidia', 'amd', 'intel', 'apple', 'sony',
                  'bose', 'jbl', 'steelseries', 'hyperx', 'benq', 'lenovo']
        return [b.title() for b in brands if b in query]
    
    def clear_cache(self):
        """Clear the routing decision cache."""
        self._route_cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            "llm_available": self._groq_client is not None,
            "cache_size": len(self._route_cache),
            "use_llm": self.use_llm
        }


# Verification
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    router = QueryRouter()
    print("🧪 Testing Hybrid Router:")
    print(f"   LLM Available: {router._groq_client is not None}")
    print()
    
    test_cases = [
        ("popular laptops", None),           # FAST (regex confident)
        ("gaming laptop", 1500),             # SMART (product keyword)
        ("complete gaming setup", 2000),     # DEEP (bundle keyword)
        ("I need stuff for streaming", 1000), # Ambiguous -> LLM
        ("laptop vs desktop", None),         # DEEP (comparison)
        ("best seller monitors", None),      # FAST
    ]
    
    for query, budget in test_cases:
        decision = router.analyze(query, budget)
        print(f"Query: '{query}'")
        print(f"  -> {decision.path.value.upper()} (conf: {decision.confidence:.2f}, method: {decision.routing_method})")
        print(f"     Reason: {decision.reason}")
        print()
