"""
Query Router - Hybrid LLM + Regex Routing
Uses Groq LLM for intelligent routing with regex fallback.

TWO-STAGE QUERY PROCESSING:
1. Stage 1 (Fast Path Detection): Regex-based pattern matching - NO LLM required
2. Stage 2 (Smart/Deep Routing): LLM-based intelligent analysis - ONLY for complex queries
"""
import os
import re
import json
import hashlib
import time
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
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
class ExtractedConstraints:
    """Extracted constraints from query for ACORN filtering."""
    categories: List[str] = field(default_factory=list)
    primary_category: str = ""
    specifications: Dict[str, Any] = field(default_factory=dict)
    budget: Dict[str, Any] = field(default_factory=dict)
    features: List[str] = field(default_factory=list)
    use_case: str = ""
    quality_tier: str = ""
    brands: List[str] = field(default_factory=list)


@dataclass
class RouteDecision:
    path: RoutePath
    confidence: float
    reason: str
    estimated_latency_ms: int
    complexity_score: float
    routing_method: str = "regex"  # "llm" or "regex"
    constraints: ExtractedConstraints = field(default_factory=ExtractedConstraints)


class QueryRouter:
    """
    Hybrid router combining LLM intelligence with regex speed.
    
    TWO-STAGE PROCESSING:
    - Stage 1 (Fast Path): Regex-based, bypasses LLM for simple 1-3 word queries
    - Stage 2 (Smart/Deep): LLM-based for complex queries with specs/constraints
    
    ROUTING RULES:
    - FAST: Simple queries (1-3 words, no specs) - cached PostgreSQL lookup
    - SMART: Single product category with specs/constraints (plurals = STILL Smart)
    - DEEP: Multiple DISTINCT categories OR bundle keywords
    
    CRITICAL: Plurals of ONE category = Smart Path, NOT Deep Path
    - "mouses" → Smart (1 category)
    - "laptop and monitor" → Deep (2 categories)
    """
    
    # LLM System Prompt for Smart/Deep routing decisions
    LLM_SYSTEM_PROMPT = """You are analyzing user search queries to determine routing and extract constraints.

**CONTEXT:**
- This query has already bypassed Fast Path (simple cache lookup)
- It contains complexity: specifications, constraints, or multiple products
- Your task: Decide between SMART PATH (single product) or DEEP PATH (bundle/multi-product)

## SMART PATH (Complexity Score: 31-70)
Use Smart Path when:
- User wants ONE type of product
- Query contains specifications, features, or constraints
- Technical requirements mentioned (RAM, processor, screen size, etc.)
- Plural forms of ONE category = STILL Smart Path ("mouses", "laptops", "monitors")

## DEEP PATH (Complexity Score: 71-100)
Use Deep Path when:
- Multiple DISTINCT product categories mentioned
- Bundle keywords: "setup", "kit", "bundle", "complete", "build", "system"
- Conjunctions connecting different products: "laptop AND monitor"

## CRITICAL RULES:
- Plurals ≠ Bundles: "mouses" = 1 category = Smart Path
- Only multi-CATEGORY (not multi-quantity) triggers Deep Path
- Extract ALL constraints: operators (>=, <=), specs, features, budget

## CONSTRAINT EXTRACTION:
- "more than 8gb" → ram: {"operator": ">=", "value": 8, "unit": "GB"}
- "under $500" → budget: {"max": 500}
- "with colors" / "rgb" → features: ["rgb_lighting"]
- "i5 intel" → processor: {"brand": "Intel", "tier": "i5"}

Respond with ONLY valid JSON (no markdown):
{
  "path": "smart|deep",
  "complexity_score": 31-100,
  "reason": "brief explanation",
  "confidence": 0.0-1.0,
  "categories": ["list of distinct product categories"],
  "constraints": {
    "processor": {},
    "ram": {},
    "storage": {},
    "display": {},
    "features": [],
    "budget": {"min": null, "max": null}
  },
  "use_case": "",
  "quality_tier": ""
}"""

    # Bundle/Deep keywords - trigger Deep Path
    # Note: 'studio' is only deep when standalone or with prefix (home/music/podcast/etc)
    # 'studio headphones' = Smart (single category), 'home studio' = Deep (bundle)
    DEEP_KEYWORDS = {
        'setup', 'bundle', 'complete', 'build', 'workstation',
        'gaming rig', 'home office', 'home studio', 'music studio', 'podcast studio',
        'streaming studio', 'recording studio', 'kit', 'combo', 'rig',
        'all-in-one', 'package', 'together', 'full set', 'starter kit',
        'entire', 'whole', 'system', 'streaming kit'
    }
    
    # Product categories - normalized to singular form
    CATEGORY_MAP = {
        # Laptops/Computers
        'laptop': 'laptop', 'laptops': 'laptop', 'notebook': 'laptop', 'notebooks': 'laptop',
        'computer': 'computer', 'computers': 'computer', 'pc': 'computer', 'pcs': 'computer',
        'desktop': 'desktop', 'desktops': 'desktop',
        # Monitors/Displays
        'monitor': 'monitor', 'monitors': 'monitor', 'display': 'monitor', 'displays': 'monitor',
        'screen': 'monitor', 'screens': 'monitor',
        'tv': 'tv', 'tvs': 'tv', 'television': 'tv', 'televisions': 'tv',
        # Peripherals
        'keyboard': 'keyboard', 'keyboards': 'keyboard',
        'mouse': 'mouse', 'mice': 'mouse', 'mouses': 'mouse',
        'headphones': 'headphones', 'headphone': 'headphones', 'earbuds': 'headphones',
        'headset': 'headset', 'headsets': 'headset',
        'speaker': 'speaker', 'speakers': 'speaker', 'soundbar': 'speaker', 'soundbars': 'speaker',
        'webcam': 'webcam', 'webcams': 'webcam', 'camera': 'camera', 'cameras': 'camera',
        'microphone': 'microphone', 'microphones': 'microphone', 'mic': 'microphone', 'mics': 'microphone',
        # Mobile
        'phone': 'phone', 'phones': 'phone', 'smartphone': 'phone', 'smartphones': 'phone',
        'tablet': 'tablet', 'tablets': 'tablet', 'ipad': 'tablet', 'ipads': 'tablet',
        # Components
        'gpu': 'gpu', 'gpus': 'gpu', 'graphics': 'gpu', 'graphics card': 'gpu', 'graphics cards': 'gpu',
        'cpu': 'cpu', 'cpus': 'cpu', 'processor': 'cpu', 'processors': 'cpu',
        'ram': 'ram', 'memory': 'ram',
        'ssd': 'storage', 'ssds': 'storage', 'hdd': 'storage', 'hard drive': 'storage',
        'storage': 'storage', 'drive': 'storage',
        # Accessories
        'charger': 'charger', 'chargers': 'charger',
        'cable': 'cable', 'cables': 'cable', 'cord': 'cable', 'cords': 'cable',
        'adapter': 'adapter', 'adapters': 'adapter',
        'hub': 'hub', 'hubs': 'hub', 'dock': 'dock', 'docks': 'dock',
        'stand': 'stand', 'stands': 'stand',
        'chair': 'chair', 'chairs': 'chair',
        'desk': 'desk', 'desks': 'desk',
        # Networking
        'router': 'router', 'routers': 'router',
        'modem': 'modem', 'modems': 'modem',
        'wifi': 'router',
    }
    
    # Simple quality words (can be used with Fast Path)
    SIMPLE_QUALITY_WORDS = {'good', 'best', 'cheap', 'nice', 'great', 'top', 'quality'}
    
    # Modifier words (intensifiers that don't change path)
    MODIFIER_WORDS = {'really', 'very', 'super', 'extremely', 'quite', 'pretty', 'fairly', 'so'}
    
    # Feature keywords (need Smart Path for filtering)
    FEATURE_KEYWORDS = {
        'wireless': 'wireless', 'wired': 'wired',
        'mechanical': 'mechanical', 'membrane': 'membrane',
        'rgb': 'rgb_lighting', 'colorful': 'rgb_lighting', 'with colors': 'rgb_lighting',
        'backlit': 'backlit', 'illuminated': 'backlit',
        'noise cancelling': 'noise_cancelling', 'noise-cancelling': 'noise_cancelling',
        'anc': 'noise_cancelling', 'active noise': 'noise_cancelling',
        'bluetooth': 'bluetooth', 'bt': 'bluetooth',
        'usb-c': 'usb_c', 'usb c': 'usb_c', 'type-c': 'usb_c', 'type c': 'usb_c',
        'thunderbolt': 'thunderbolt',
        '4k': '4k', 'uhd': '4k', '2160p': '4k',
        '1440p': '1440p', 'qhd': '1440p', 'wqhd': '1440p',
        '1080p': '1080p', 'fhd': '1080p', 'full hd': '1080p',
        'hdr': 'hdr', 'hdr10': 'hdr',
        'curved': 'curved',
        'ultrawide': 'ultrawide',
        'ergonomic': 'ergonomic',
        'adjustable': 'adjustable',
        'portable': 'portable', 'lightweight': 'portable',
        'waterproof': 'waterproof', 'water resistant': 'waterproof',
        'quiet': 'quiet', 'silent': 'quiet',
    }
    
    # Use case keywords
    USE_CASE_KEYWORDS = {
        'gaming': 'gaming', 'gamer': 'gaming', 'game': 'gaming',
        'programming': 'programming', 'coding': 'programming', 'developer': 'programming',
        'video editing': 'video_editing', 'editing': 'video_editing', 'content creation': 'video_editing',
        'streaming': 'streaming', 'streamer': 'streaming',
        'office': 'office', 'work': 'office', 'business': 'office', 'productivity': 'office',
        'school': 'education', 'student': 'education', 'study': 'education',
        'photo editing': 'photo_editing', 'photography': 'photo_editing',
        'music production': 'music_production', 'audio': 'music_production',
    }
    
    # Budget/price patterns with operators
    BUDGET_PATTERNS = [
        (r'under\s*\$?\s*(\d+)', 'max'),
        (r'less than\s*\$?\s*(\d+)', 'max'),
        (r'below\s*\$?\s*(\d+)', 'max'),
        (r'up to\s*\$?\s*(\d+)', 'max'),
        (r'max(?:imum)?\s*\$?\s*(\d+)', 'max'),
        (r'over\s*\$?\s*(\d+)', 'min'),
        (r'more than\s*\$?\s*(\d+)', 'min'),
        (r'above\s*\$?\s*(\d+)', 'min'),
        (r'at least\s*\$?\s*(\d+)', 'min'),
        (r'min(?:imum)?\s*\$?\s*(\d+)', 'min'),
        (r'\$\s*(\d+)\s*[-–]\s*\$?\s*(\d+)', 'range'),  # $500-$1000
        (r'between\s*\$?\s*(\d+)\s*and\s*\$?\s*(\d+)', 'range'),
        (r'around\s*\$?\s*(\d+)', 'around'),
        (r'about\s*\$?\s*(\d+)', 'around'),
        (r'\$\s*(\d+)', 'exact'),  # $500
        (r'(\d+)\s*dollars?', 'exact'),
        (r'budget\s*(?:of\s*)?\$?\s*(\d+)', 'max'),
    ]
    
    # Spec patterns for extraction
    SPEC_PATTERNS = {
        'ram': [
            (r'(\d+)\s*gb\s*(?:ddr[45]?\s*)?(?:ram|memory)', 'exact'),
            (r'(?:ram|memory)[:\s]*(\d+)\s*gb', 'exact'),
            (r'more than\s*(\d+)\s*gb\s*(?:ram)?', '>='),
            (r'at least\s*(\d+)\s*gb\s*(?:ram)?', '>='),
            (r'(\d+)\s*gb\s*or more', '>='),
            (r'(\d+)\s*[-–]\s*(\d+)\s*gb', 'range'),
        ],
        'storage': [
            (r'(\d+)\s*gb\s*(?:nvme\s*)?ssd', 'ssd'),
            (r'(\d+)\s*tb\s*(?:nvme\s*)?ssd', 'ssd_tb'),
            (r'(\d+)\s*tb\s*hdd', 'hdd'),
            (r'(\d+)\s*gb\s*hdd', 'hdd'),
        ],
        'display': [
            (r'(\d{2,3})\s*hz', 'refresh_rate'),
            (r'(\d{1,2}(?:\.\d)?)["\s]*(?:inch|in\b)', 'screen_size'),
        ],
        'processor': [
            (r'(?:intel\s+)?(?:core\s+)?(i[3579])[- ]?(\d{4,5}[a-z]*)?', 'intel'),
            (r'ryzen\s*([3579])\s*(\d{4}[a-z]*)?', 'amd'),
            (r'\b(m[123])\s*(pro|max|ultra)?', 'apple'),
        ],
    }
    
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
        self._route_cache: Dict[str, RouteDecision] = {}
        self._budget_patterns = [(re.compile(p, re.IGNORECASE), t) for p, t in self.BUDGET_PATTERNS]
        self._spec_patterns = {k: [(re.compile(p, re.IGNORECASE), t) for p, t in v] 
                               for k, v in self.SPEC_PATTERNS.items()}
        
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
        TWO-STAGE query analysis:
        
        Stage 1 (Fast Path Detection): Regex-based
        - Simple 1-3 word queries without specs
        - NO LLM required, direct cache lookup
        
        Stage 2 (Smart/Deep Routing): LLM-based
        - Complex queries with specs/constraints
        - Smart: Single category with specs
        - Deep: Multiple categories OR bundle keywords
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
                routing_method="cached",
                constraints=cached.constraints
            )
        
        # 2. STAGE 1: Fast Path Detection (Regex-based)
        fast_decision = self._check_fast_path(query_lower)
        if fast_decision:
            self._route_cache[cache_key] = fast_decision
            print(f"⚡ Fast Path: '{query[:30]}' → FAST ({fast_decision.reason})")
            return fast_decision
        
        # 3. Extract constraints for Smart/Deep routing
        constraints = self._extract_constraints(query_lower, budget)
        
        # 4. STAGE 2: Check for obvious Deep Path (bundle keywords or multi-category)
        deep_decision = self._check_deep_path(query_lower, constraints)
        if deep_decision:
            deep_decision.constraints = constraints
            self._route_cache[cache_key] = deep_decision
            print(f"🔧 Deep Path: '{query[:30]}' → DEEP ({deep_decision.reason})")
            return deep_decision
        
        # 5. For complex single-category queries, use LLM or Smart regex
        if self._groq_client and self._needs_llm_routing(query_lower, constraints):
            try:
                llm_decision = self._llm_route(query, budget, constraints)
                # Validate LLM decision (enforce single-category = Smart)
                llm_decision = self._validate_llm_decision(llm_decision, constraints)
                self._route_cache[cache_key] = llm_decision
                return llm_decision
            except Exception as e:
                print(f"⚠️ LLM routing failed: {e}, using Smart Path fallback")
        
        # 6. Default to Smart Path for single-category queries with specs
        smart_decision = self._create_smart_decision(query_lower, constraints)
        self._route_cache[cache_key] = smart_decision
        print(f"🧠 Smart Path: '{query[:30]}' → SMART ({smart_decision.reason})")
        return smart_decision
    
    def _check_fast_path(self, query_lower: str) -> Optional[RouteDecision]:
        """
        STAGE 1: Fast Path Detection (Regex-based)
        
        Triggers Fast Path when:
        - 1-4 words total (allows modifiers like "really good laptop")
        - Matches a product category
        - No numerical values (specs, prices)
        - No feature keywords
        - No use case keywords (gaming, streaming, etc. need filtering)
        - Only simple quality words + modifiers allowed
        """
        # Clean query: remove special characters for matching
        cleaned_query = re.sub(r'[^\w\s]', '', query_lower).strip()
        words = cleaned_query.split()
        word_count = len(words)
        
        # Fast Path: 1-4 words only (allows "really good laptop")
        if word_count > 4:
            return None
        
        # Check for numerical values (specs, prices)
        if re.search(r'\d', cleaned_query):
            return None
        
        # Check for feature keywords (need Smart Path filtering)
        for feature in self.FEATURE_KEYWORDS:
            if feature in cleaned_query:
                return None
        
        # Check for use case keywords (need Smart Path filtering)
        for use_case in self.USE_CASE_KEYWORDS:
            if use_case in cleaned_query:
                return None
        
        # Extract categories from cleaned query
        categories = self._extract_categories_from_query(cleaned_query)
        
        # Must have exactly 1 category for Fast Path
        if len(categories) != 1:
            return None
        
        # Remove category words, quality words, and modifiers - check what's left
        remaining_words = set(words)
        for word in words:
            if word in self.CATEGORY_MAP or word in self.SIMPLE_QUALITY_WORDS or word in self.MODIFIER_WORDS:
                remaining_words.discard(word)
        
        # If there are unknown words left, need Smart Path
        if remaining_words:
            return None
        
        primary_category = categories[0]
        
        return RouteDecision(
            path=RoutePath.FAST,
            confidence=0.95,
            reason=f"Simple {primary_category} lookup",
            estimated_latency_ms=50,
            complexity_score=0.15,
            routing_method="regex",
            constraints=ExtractedConstraints(
                categories=[primary_category],
                primary_category=primary_category
            )
        )
    
    def _check_deep_path(self, query_lower: str, constraints: ExtractedConstraints) -> Optional[RouteDecision]:
        """
        Check if query should go to Deep Path.
        
        Triggers Deep Path when:
        - Bundle keywords present: "setup", "kit", "bundle", etc.
        - Multiple DISTINCT product categories
        - Conjunctions connecting different products: "laptop AND monitor"
        - Comma-separated categories: "laptop, mouse"
        
        CRITICAL: Plurals of ONE category = NOT Deep Path
        """
        # Check for bundle keywords
        for keyword in self.DEEP_KEYWORDS:
            if keyword in query_lower:
                return RouteDecision(
                    path=RoutePath.DEEP,
                    confidence=0.95,
                    reason=f"Bundle keyword: '{keyword}'",
                    estimated_latency_ms=1000,
                    complexity_score=0.85,
                    routing_method="regex"
                )
        
        # Check for multiple DISTINCT categories
        if len(constraints.categories) >= 2:
            return RouteDecision(
                path=RoutePath.DEEP,
                confidence=0.9,
                reason=f"Multiple categories: {', '.join(constraints.categories)}",
                estimated_latency_ms=1000,
                complexity_score=0.8,
                routing_method="regex"
            )
        
        # Check for "X and Y" pattern with different product types
        and_match = re.search(r'(\w+)\s+and\s+(\w+)', query_lower)
        if and_match:
            word1, word2 = and_match.groups()
            cat1 = self.CATEGORY_MAP.get(word1)
            cat2 = self.CATEGORY_MAP.get(word2)
            if cat1 and cat2 and cat1 != cat2:
                return RouteDecision(
                    path=RoutePath.DEEP,
                    confidence=0.9,
                    reason=f"Multi-category: {cat1} and {cat2}",
                    estimated_latency_ms=1000,
                    complexity_score=0.8,
                    routing_method="regex"
                )
        
        # Check for comma-separated categories: "laptop, mouse"
        if ',' in query_lower:
            parts = [p.strip() for p in query_lower.split(',')]
            comma_categories = set()
            for part in parts:
                for word in part.split():
                    if word in self.CATEGORY_MAP:
                        comma_categories.add(self.CATEGORY_MAP[word])
            if len(comma_categories) >= 2:
                return RouteDecision(
                    path=RoutePath.DEEP,
                    confidence=0.9,
                    reason=f"Comma-separated categories: {', '.join(comma_categories)}",
                    estimated_latency_ms=1000,
                    complexity_score=0.8,
                    routing_method="regex"
                )
        
        return None
    
    def _needs_llm_routing(self, query_lower: str, constraints: ExtractedConstraints) -> bool:
        """Determine if query is complex enough to need LLM routing."""
        # Use LLM for queries with multiple specs or ambiguous intent
        has_specs = bool(constraints.specifications)
        has_features = len(constraints.features) > 1
        has_use_case = bool(constraints.use_case)
        word_count = len(query_lower.split())
        
        # LLM for complex single-category queries (5+ words with specs)
        return word_count >= 5 and (has_specs or has_features or has_use_case)
    
    def _create_smart_decision(self, query_lower: str, constraints: ExtractedConstraints) -> RouteDecision:
        """Create Smart Path decision for single-category queries with specs."""
        # Calculate complexity score (31-70 for Smart Path)
        complexity = 35
        if constraints.specifications:
            complexity += 10
        if constraints.features:
            complexity += len(constraints.features) * 3
        if constraints.budget.get('max') or constraints.budget.get('min'):
            complexity += 5
        if constraints.use_case:
            complexity += 5
        
        complexity = min(70, max(31, complexity))
        
        reason = f"Single category: {constraints.primary_category or 'product'}"
        if constraints.features:
            reason += f" + {len(constraints.features)} features"
        if constraints.specifications:
            reason += " + specs"
        
        return RouteDecision(
            path=RoutePath.SMART,
            confidence=0.85,
            reason=reason,
            estimated_latency_ms=250,
            complexity_score=complexity / 100,
            routing_method="regex",
            constraints=constraints
        )
    
    def _validate_llm_decision(self, decision: RouteDecision, constraints: ExtractedConstraints) -> RouteDecision:
        """
        Validate LLM routing decision.
        
        CRITICAL RULE: Single category = Smart Path, regardless of LLM output.
        """
        # If only 1 category detected, force Smart Path
        if len(constraints.categories) <= 1 and decision.path == RoutePath.DEEP:
            print(f"⚠️ Overriding LLM: Single category → Smart Path")
            return RouteDecision(
                path=RoutePath.SMART,
                confidence=decision.confidence,
                reason=f"[corrected] Single category: {constraints.primary_category}",
                estimated_latency_ms=250,
                complexity_score=min(0.7, decision.complexity_score),
                routing_method="llm_corrected",
                constraints=constraints
            )
        return decision
    
    def _llm_route(self, query: str, budget: Optional[float], constraints: ExtractedConstraints) -> RouteDecision:
        """
        Use Groq LLM for intelligent query routing (Stage 2).
        
        Only called for complex queries that passed Fast Path detection.
        """
        start_time = time.time()
        
        # Build user message with extracted constraints
        user_msg = f"Query: \"{query}\""
        if budget:
            user_msg += f"\nUser budget: ${budget}"
        if constraints.categories:
            user_msg += f"\nDetected categories: {', '.join(constraints.categories)}"
        
        response = self._groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": self.LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            temperature=0,
            max_tokens=500
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
        complexity = float(result.get("complexity_score", 50))
        
        # Update constraints from LLM if provided
        if "constraints" in result:
            llm_constraints = result["constraints"]
            if llm_constraints.get("features"):
                constraints.features.extend(llm_constraints["features"])
            if llm_constraints.get("budget"):
                constraints.budget.update(llm_constraints["budget"])
        
        if "categories" in result:
            constraints.categories = result["categories"]
            if constraints.categories:
                constraints.primary_category = constraints.categories[0]
        
        if "use_case" in result:
            constraints.use_case = result["use_case"]
        
        latency_map = {"fast": 50, "smart": 250, "deep": 1000}
        
        llm_latency = (time.time() - start_time) * 1000
        print(f"🧠 LLM routed '{query[:30]}...' → {path_str.upper()} (score: {complexity}, {llm_latency:.0f}ms)")
        
        return RouteDecision(
            path=path,
            confidence=confidence,
            reason=reason,
            estimated_latency_ms=latency_map.get(path_str, 250),
            complexity_score=complexity / 100,
            routing_method="llm",
            constraints=constraints
        )
    
    def _extract_constraints(self, query_lower: str, budget: Optional[float]) -> ExtractedConstraints:
        """
        Extract ALL constraints from query for ACORN filtering.
        
        Extracts:
        - Categories (normalized to singular)
        - Specifications (RAM, storage, display, processor)
        - Features (wireless, RGB, etc.)
        - Budget (with operators)
        - Use case
        - Quality tier
        - Brands
        """
        constraints = ExtractedConstraints()
        
        # 1. Extract categories
        constraints.categories = self._extract_categories_from_query(query_lower)
        if constraints.categories:
            constraints.primary_category = constraints.categories[0]
        
        # 2. Extract features
        for pattern, feature_name in self.FEATURE_KEYWORDS.items():
            if pattern in query_lower:
                if feature_name not in constraints.features:
                    constraints.features.append(feature_name)
        
        # 3. Extract use case
        for pattern, use_case in self.USE_CASE_KEYWORDS.items():
            if pattern in query_lower:
                constraints.use_case = use_case
                break
        
        # 4. Extract budget
        constraints.budget = self._extract_budget_with_operator(query_lower, budget)
        
        # 5. Extract specifications
        constraints.specifications = self._extract_specs(query_lower)
        
        # 6. Extract quality tier
        if any(w in query_lower for w in ['cheap', 'budget', 'affordable', 'inexpensive']):
            constraints.quality_tier = 'budget'
        elif any(w in query_lower for w in ['premium', 'high-end', 'expensive', 'luxury', 'best']):
            constraints.quality_tier = 'premium'
        elif any(w in query_lower for w in ['good', 'decent', 'quality']):
            constraints.quality_tier = 'mid_range'
        
        # 7. Extract brands
        constraints.brands = self._extract_brands(query_lower)
        
        return constraints
    
    def _extract_categories_from_query(self, query_lower: str) -> List[str]:
        """
        Extract normalized product categories from query.
        
        IMPORTANT: Distinguishes between component-as-product vs component-as-spec:
        - "ram" alone or "buy ram" = product category
        - "16gb ram laptop" = specification for laptop, NOT a separate product
        """
        categories = set()
        words = query_lower.split()
        
        # Components that are usually specs when preceded by size values
        SPEC_COMPONENTS = {'ram', 'memory', 'storage', 'ssd', 'hdd', 'drive'}
        
        # Check for spec patterns that would make component words into specs
        spec_contexts = set()
        if re.search(r'\d+\s*(gb|tb|mb)\s*(ram|memory|storage|ssd|hdd)', query_lower):
            # Found pattern like "16gb ram" - these are specs, not products
            for comp in SPEC_COMPONENTS:
                if comp in query_lower:
                    spec_contexts.add(comp)
        
        for i, word in enumerate(words):
            if word in self.CATEGORY_MAP:
                normalized = self.CATEGORY_MAP[word]
                
                # Skip if this is a spec context (e.g., "16gb ram" where ram is a spec, not product)
                if normalized in spec_contexts:
                    continue
                    
                # Skip storage/ram if they appear with a size prefix in context
                if normalized in ('ram', 'storage'):
                    # Check if preceded by a number like "16gb"
                    if i > 0 and re.search(r'\d+\s*(gb|tb|mb)?$', words[i-1]):
                        continue
                
                categories.add(normalized)
        
        # Also check for multi-word categories
        for phrase in ['graphics card', 'hard drive', 'gaming rig']:
            if phrase in query_lower and phrase in self.CATEGORY_MAP:
                categories.add(self.CATEGORY_MAP[phrase])
        
        return list(categories)
    
    def _extract_budget_with_operator(self, query_lower: str, explicit_budget: Optional[float]) -> Dict[str, Any]:
        """Extract budget with operator (min, max, range, around)."""
        budget_info = {"currency": "USD"}
        
        if explicit_budget:
            budget_info["max"] = explicit_budget
        
        for pattern, op_type in self._budget_patterns:
            match = pattern.search(query_lower)
            if match:
                try:
                    if op_type == 'range':
                        budget_info["min"] = float(match.group(1))
                        budget_info["max"] = float(match.group(2))
                    elif op_type == 'around':
                        value = float(match.group(1))
                        budget_info["target"] = value
                        budget_info["min"] = value * 0.9
                        budget_info["max"] = value * 1.1
                    elif op_type == 'min':
                        budget_info["min"] = float(match.group(1))
                    elif op_type in ('max', 'exact'):
                        budget_info["max"] = float(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
        
        return budget_info
    
    def _extract_specs(self, query_lower: str) -> Dict[str, Any]:
        """Extract technical specifications from query."""
        specs = {}
        
        # RAM extraction
        for pattern, op_type in self._spec_patterns.get('ram', []):
            match = pattern.search(query_lower)
            if match:
                if op_type == 'range':
                    specs['ram'] = {
                        'min': int(match.group(1)),
                        'max': int(match.group(2)),
                        'unit': 'GB'
                    }
                elif op_type == '>=':
                    specs['ram'] = {
                        'operator': '>=',
                        'value': int(match.group(1)),
                        'unit': 'GB'
                    }
                else:
                    specs['ram'] = {
                        'value': int(match.group(1)),
                        'unit': 'GB'
                    }
                break
        
        # Storage extraction
        for pattern, op_type in self._spec_patterns.get('storage', []):
            match = pattern.search(query_lower)
            if match:
                value = int(match.group(1))
                if 'tb' in op_type:
                    value *= 1000  # Convert to GB
                specs['storage'] = {
                    'value': value,
                    'unit': 'GB',
                    'type': 'SSD' if 'ssd' in op_type else 'HDD'
                }
                break
        
        # Display extraction
        for pattern, spec_type in self._spec_patterns.get('display', []):
            match = pattern.search(query_lower)
            if match:
                if spec_type == 'refresh_rate':
                    specs['refresh_rate'] = {'value': int(match.group(1)), 'unit': 'Hz'}
                elif spec_type == 'screen_size':
                    specs['screen_size'] = {'value': float(match.group(1)), 'unit': 'inches'}
        
        # Processor extraction
        for pattern, brand in self._spec_patterns.get('processor', []):
            match = pattern.search(query_lower)
            if match:
                if brand == 'intel':
                    specs['processor'] = {
                        'brand': 'Intel',
                        'tier': match.group(1).upper(),
                        'model': match.group(2) if match.group(2) else None
                    }
                elif brand == 'amd':
                    specs['processor'] = {
                        'brand': 'AMD',
                        'tier': f"Ryzen {match.group(1)}",
                        'model': match.group(2) if match.group(2) else None
                    }
                elif brand == 'apple':
                    specs['processor'] = {
                        'brand': 'Apple',
                        'tier': match.group(1).upper(),
                        'variant': match.group(2).title() if match.group(2) else None
                    }
                break
        
        return specs
    
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
        """Extract structured intent from query (legacy method, use analyze() for full info)."""
        query_lower = query.lower()
        constraints = self._extract_constraints(query_lower, None)
        return {
            'raw_query': query,
            'budget': constraints.budget,
            'is_bundle': any(kw in query_lower for kw in self.DEEP_KEYWORDS),
            'categories': constraints.categories,
            'brands': constraints.brands,
            'features': constraints.features,
            'specifications': constraints.specifications,
            'use_case': constraints.use_case
        }

    def _extract_budget(self, query: str) -> Optional[float]:
        """Extract budget amount from query (legacy method)."""
        budget_info = self._extract_budget_with_operator(query, None)
        return budget_info.get('max') or budget_info.get('target') or budget_info.get('min')

    def _extract_categories(self, query: str) -> list:
        """Extract product categories from query (legacy method)."""
        return self._extract_categories_from_query(query.lower())

    def _extract_brands(self, query: str) -> list:
        """Extract brand names from query."""
        brands = ['logitech', 'corsair', 'razer', 'dell', 'hp', 'asus', 'samsung', 
                  'lg', 'acer', 'msi', 'nvidia', 'amd', 'intel', 'apple', 'sony',
                  'bose', 'jbl', 'steelseries', 'hyperx', 'benq', 'lenovo', 'microsoft',
                  'google', 'xiaomi', 'oneplus', 'realme', 'anker', 'belkin', 'sennheiser',
                  'audio-technica', 'beyerdynamic', 'shure', 'blue', 'elgato', 'rode']
        return [b.title() for b in brands if b in query.lower()]
    
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


# Verification - matches SYSTEM ARCHITECTURE specification
if __name__ == "__main__":
    from dotenv import load_dotenv
    import time
    load_dotenv()
    
    router = QueryRouter()
    print("🧪 Testing Two-Stage Hybrid Router (100+ test cases):")
    print(f"   LLM Available: {router._groq_client is not None}")
    print()
    
    # Comprehensive test suite - 100+ test cases
    # Format: (query, budget, expected_path, expected_score_range)
    test_cases = [
        # ============================================================
        # FAST PATH TESTS (Simple category lookups, 1-3 words, no specs)
        # ============================================================
        # Single word categories
        ("laptop", None, "fast", (10, 30)),
        ("laptops", None, "fast", (10, 30)),
        ("monitor", None, "fast", (10, 30)),
        ("monitors", None, "fast", (10, 30)),
        ("keyboard", None, "fast", (10, 30)),
        ("keyboards", None, "fast", (10, 30)),
        ("mouse", None, "fast", (10, 30)),
        ("mice", None, "fast", (10, 30)),
        ("headphones", None, "fast", (10, 30)),
        ("headset", None, "fast", (10, 30)),
        ("webcam", None, "fast", (10, 30)),
        ("speaker", None, "fast", (10, 30)),
        ("speakers", None, "fast", (10, 30)),
        ("phone", None, "fast", (10, 30)),
        ("phones", None, "fast", (10, 30)),
        ("tablet", None, "fast", (10, 30)),
        ("tablets", None, "fast", (10, 30)),
        ("desk", None, "fast", (10, 30)),
        ("chair", None, "fast", (10, 30)),
        ("router", None, "fast", (10, 30)),
        ("charger", None, "fast", (10, 30)),
        ("cable", None, "fast", (10, 30)),
        ("hub", None, "fast", (10, 30)),
        ("dock", None, "fast", (10, 30)),
        
        # Category + quality words (still FAST)
        ("good laptop", None, "fast", (10, 30)),
        ("best monitor", None, "fast", (10, 30)),
        ("cheap keyboard", None, "fast", (10, 30)),
        ("nice mouse", None, "fast", (10, 30)),
        ("great headphones", None, "fast", (10, 30)),
        ("top speakers", None, "fast", (10, 30)),
        ("quality webcam", None, "fast", (10, 30)),
        ("best laptops", None, "fast", (10, 30)),
        ("cheap tablets", None, "fast", (10, 30)),
        ("good phones", None, "fast", (10, 30)),
        
        # ============================================================
        # SMART PATH TESTS (Single category + features/specs/use cases)
        # ============================================================
        # Use case keywords → SMART (need ACORN filtering)
        ("gaming laptop", None, "smart", (30, 60)),
        ("best gaming laptop", None, "smart", (30, 60)),
        ("gaming mouse", None, "smart", (30, 60)),
        ("gaming keyboard", None, "smart", (30, 60)),
        ("gaming headset", None, "smart", (30, 60)),
        ("gaming monitor", None, "smart", (30, 60)),
        ("office laptop", None, "smart", (30, 60)),
        ("office chair", None, "smart", (30, 60)),
        ("streaming mic", None, "smart", (30, 60)),
        ("streaming webcam", None, "smart", (30, 60)),
        ("work laptop", None, "smart", (30, 60)),
        ("school laptop", None, "smart", (30, 60)),
        ("travel laptop", None, "smart", (30, 60)),
        ("coding laptop", None, "smart", (30, 60)),
        ("video editing laptop", None, "smart", (30, 60)),
        ("music production headphones", None, "smart", (30, 60)),
        
        # Feature keywords → SMART
        ("wireless mouse", None, "smart", (30, 60)),
        ("wireless keyboard", None, "smart", (30, 60)),
        ("wireless headphones", None, "smart", (30, 60)),
        ("bluetooth speaker", None, "smart", (30, 60)),
        ("bluetooth headphones", None, "smart", (30, 60)),
        ("mechanical keyboard", None, "smart", (30, 60)),
        ("rgb keyboard", None, "smart", (30, 60)),
        ("rgb mouse", None, "smart", (30, 60)),
        ("4k monitor", None, "smart", (30, 60)),
        ("curved monitor", None, "smart", (30, 60)),
        ("ultrawide monitor", None, "smart", (30, 60)),
        ("noise cancelling headphones", None, "smart", (30, 60)),
        ("ergonomic keyboard", None, "smart", (30, 60)),
        ("ergonomic mouse", None, "smart", (30, 60)),
        ("portable speaker", None, "smart", (30, 60)),
        ("waterproof speaker", None, "smart", (30, 60)),
        ("quiet keyboard", None, "smart", (30, 60)),
        ("backlit keyboard", None, "smart", (30, 60)),
        
        # Combined features + use case → SMART
        ("wireless gaming mouse", None, "smart", (30, 70)),
        ("mechanical gaming keyboard", None, "smart", (30, 70)),
        ("rgb mechanical keyboard", None, "smart", (30, 70)),
        ("wireless noise cancelling headphones", None, "smart", (30, 70)),
        ("4k gaming monitor", None, "smart", (30, 70)),
        ("ultrawide curved monitor", None, "smart", (30, 70)),
        
        # Specs → SMART
        ("16gb laptop", None, "smart", (30, 70)),
        ("32gb ram laptop", None, "smart", (30, 70)),
        ("512gb ssd laptop", None, "smart", (30, 70)),
        ("1tb storage laptop", None, "smart", (30, 70)),
        ("27 inch monitor", None, "smart", (30, 70)),
        ("144hz monitor", None, "smart", (30, 70)),
        ("240hz gaming monitor", None, "smart", (30, 70)),
        ("i7 laptop", None, "smart", (30, 70)),
        ("i5 laptop", None, "smart", (30, 70)),
        ("ryzen 7 laptop", None, "smart", (30, 70)),
        
        # Budget constraints → SMART
        ("laptop under $500", 500, "smart", (35, 70)),
        ("laptop under $1000", 1000, "smart", (35, 70)),
        ("monitor under $300", 300, "smart", (35, 70)),
        ("keyboard under $100", 100, "smart", (35, 70)),
        ("headphones under $200", 200, "smart", (35, 70)),
        ("cheap gaming laptop", None, "smart", (30, 60)),
        ("budget gaming mouse", None, "smart", (30, 60)),
        ("affordable monitor", None, "smart", (30, 60)),
        
        # Complex specs + budget → SMART  
        ("16gb ram laptop under $1000", 1000, "smart", (40, 75)),
        ("32gb ram laptop under $1500", 1500, "smart", (40, 75)),
        ("i7 laptop under $1200", 1200, "smart", (40, 75)),
        ("4k monitor under $500", 500, "smart", (40, 75)),
        ("144hz monitor under $400", 400, "smart", (40, 75)),
        ("wireless gaming mouse under $100", 100, "smart", (40, 75)),
        ("mechanical keyboard under $150", 150, "smart", (40, 75)),
        
        # Plural forms (STILL SMART, not Deep!)
        ("good mouses", None, "fast", (10, 30)),          # Simple plural, just like "mouses" 
        ("gaming mouses", None, "smart", (30, 60)),
        ("wireless mouses", None, "smart", (30, 60)),
        ("mechanical keyboards", None, "smart", (30, 60)),
        ("gaming keyboards", None, "smart", (30, 60)),
        ("4k monitors", None, "smart", (30, 60)),
        ("gaming laptops", None, "smart", (30, 60)),
        ("wireless headphones", None, "smart", (30, 60)),
        ("good mouse with colors", None, "smart", (30, 60)),
        ("good mouses with colors", None, "smart", (30, 60)),
        
        # Brand mentions → SMART
        ("logitech mouse", None, "smart", (30, 60)),
        ("corsair keyboard", None, "smart", (30, 60)),
        ("razer headset", None, "smart", (30, 60)),
        ("dell monitor", None, "smart", (30, 60)),
        ("samsung monitor", None, "smart", (30, 60)),
        ("apple laptop", None, "smart", (30, 60)),
        ("sony headphones", None, "smart", (30, 60)),
        ("bose headphones", None, "smart", (30, 60)),
        
        # ============================================================
        # DEEP PATH TESTS (Bundle keywords OR multiple categories)
        # ============================================================
        # Bundle keywords
        ("gaming setup", None, "deep", (70, 95)),
        ("gaming setup for $2000", 2000, "deep", (70, 95)),
        ("complete gaming setup", None, "deep", (70, 95)),
        ("streaming setup", None, "deep", (70, 95)),
        ("office setup", None, "deep", (70, 95)),
        ("home office setup", None, "deep", (70, 95)),
        ("work from home setup", None, "deep", (70, 95)),
        ("gaming bundle", None, "deep", (70, 95)),
        ("streaming bundle", None, "deep", (70, 95)),
        ("office bundle", None, "deep", (70, 95)),
        ("work from home bundle", None, "deep", (70, 95)),
        ("complete streaming kit", None, "deep", (70, 95)),
        ("gaming kit", None, "deep", (70, 95)),
        ("starter kit", None, "deep", (70, 95)),
        ("gaming rig", None, "deep", (70, 95)),
        ("complete gaming rig", None, "deep", (70, 95)),
        ("workstation setup", None, "deep", (70, 95)),
        ("studio setup", None, "deep", (70, 95)),
        ("podcast studio", None, "deep", (70, 95)),
        ("streaming studio", None, "deep", (70, 95)),
        ("home studio", None, "deep", (70, 95)),
        ("pc build", None, "deep", (70, 95)),
        ("gaming pc build", None, "deep", (70, 95)),
        ("custom pc build", None, "deep", (70, 95)),
        ("full set gaming", None, "deep", (70, 95)),
        ("complete system", None, "deep", (70, 95)),
        ("all-in-one package", None, "deep", (70, 95)),
        
        # Multiple distinct categories → DEEP
        ("laptop and monitor", None, "deep", (65, 90)),
        ("laptop and mouse", None, "deep", (65, 90)),
        ("laptop and keyboard", None, "deep", (65, 90)),
        ("monitor and keyboard", None, "deep", (65, 90)),
        ("keyboard and mouse", None, "deep", (65, 90)),
        ("headphones and microphone", None, "deep", (65, 90)),
        ("webcam and microphone", None, "deep", (65, 90)),
        ("desk and chair", None, "deep", (65, 90)),
        ("phone and tablet", None, "deep", (65, 90)),
        ("laptop monitor keyboard mouse", None, "deep", (70, 95)),
        ("gaming laptop with monitor", None, "deep", (65, 90)),
        ("laptop with external monitor", None, "deep", (65, 90)),
        
        # Comparisons → DEEP for cross-category, SMART for same-category variants
        ("laptop vs desktop", None, "deep", (65, 90)),
        ("laptop vs desktop for gaming", None, "deep", (65, 90)),
        ("laptop or desktop", None, "deep", (65, 90)),
        ("macbook vs windows laptop", None, "smart", (30, 60)),      # Same category (laptop variants)
        ("mechanical vs membrane keyboard", None, "smart", (30, 60)), # Same category (keyboard types)
        ("wired vs wireless mouse", None, "smart", (30, 60)),         # Same category (mouse variants)
        
        # Complex bundles with budget → DEEP
        ("gaming setup under $2000", 2000, "deep", (70, 95)),
        ("streaming setup under $1500", 1500, "deep", (70, 95)),
        ("office setup under $1000", 1000, "deep", (70, 95)),
        ("laptop and monitor under $1500", 1500, "deep", (70, 95)),
        ("complete home office for $2000", 2000, "deep", (70, 95)),
    ]
    
    print("=" * 80)
    print(f"Running {len(test_cases)} test cases...")
    print("=" * 80)
    
    passed = 0
    failed = 0
    failed_tests = []
    
    start_time = time.time()
    
    for i, (query, budget, expected_path, score_range) in enumerate(test_cases):
        # Clear cache between tests to ensure fresh routing
        router.clear_cache()
        
        decision = router.analyze(query, budget)
        actual_path = decision.path.value
        actual_score = int(decision.complexity_score * 100)
        
        path_ok = actual_path == expected_path
        
        if path_ok:
            passed += 1
        else:
            failed += 1
            failed_tests.append({
                'query': query,
                'budget': budget,
                'expected': expected_path,
                'actual': actual_path,
                'score': actual_score,
                'reason': decision.reason
            })
        
        # Progress indicator every 25 tests
        if (i + 1) % 25 == 0:
            print(f"   Progress: {i + 1}/{len(test_cases)} tests completed...")
    
    elapsed = time.time() - start_time
    
    print()
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print(f"Time: {elapsed:.2f}s ({elapsed/len(test_cases)*1000:.1f}ms per test)")
    print(f"Pass Rate: {passed/len(test_cases)*100:.1f}%")
    print("=" * 80)
    
    if failed > 0:
        print()
        print("❌ FAILED TESTS:")
        print("-" * 80)
        for ft in failed_tests:
            print(f"  Query: '{ft['query']}' (budget: {ft['budget']})")
            print(f"    Expected: {ft['expected'].upper()}")
            print(f"    Actual:   {ft['actual'].upper()} (score: {ft['score']})")
            print(f"    Reason:   {ft['reason']}")
            print()
    else:
        print()
        print("🎉 ALL TESTS PASSED! Router matches specification.")
        print()
        
    # Summary by path
    fast_tests = [t for t in test_cases if t[2] == "fast"]
    smart_tests = [t for t in test_cases if t[2] == "smart"]
    deep_tests = [t for t in test_cases if t[2] == "deep"]
    
    fast_failed = len([f for f in failed_tests if f['expected'] == 'fast'])
    smart_failed = len([f for f in failed_tests if f['expected'] == 'smart'])
    deep_failed = len([f for f in failed_tests if f['expected'] == 'deep'])
    
    print("PATH BREAKDOWN:")
    print(f"  FAST:  {len(fast_tests) - fast_failed}/{len(fast_tests)} passed")
    print(f"  SMART: {len(smart_tests) - smart_failed}/{len(smart_tests)} passed")
    print(f"  DEEP:  {len(deep_tests) - deep_failed}/{len(deep_tests)} passed")
