"""
Hybrid Query Router

This router combines fast regex-based rules with a fine-tuned ML model
for optimal performance:
- Stage 1: Fast deterministic rules (covers ~70-80% of queries, <1ms)
- Stage 2: ML model fallback for ambiguous cases (~20-30%, ~5-15ms)

Usage:
    from core.hybrid_router import HybridQueryRouter, RoutePath
    
    router = HybridQueryRouter()  # Uses rules only
    router = HybridQueryRouter(model_path="models/router_lstm")  # With ML fallback
    
    path = router.route("gaming laptop setup", budget=1500)
    # Returns: RoutePath.DEEP
"""

import json
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple, Any
import time


class RoutePath(Enum):
    """Query routing paths."""
    FAST = "fast"      # Direct category lookup
    SMART = "smart"    # Single-category with features/specs
    DEEP = "deep"      # Multi-category bundle optimization


@dataclass
class RouteResult:
    """Result of routing decision."""
    path: RoutePath
    confidence: float      # 0.0 - 1.0
    method: str           # "rules" or "model"
    latency_ms: float     # Time taken for routing
    categories: List[str] # Detected categories
    is_bundle: bool       # Whether bundle keywords detected
    budget: Optional[float] = None


class HybridQueryRouter:
    """
    Hybrid query router combining fast rules with ML model fallback.
    
    The router uses a two-stage approach:
    1. Fast deterministic rules for obvious cases
    2. ML model for ambiguous queries
    
    This provides the best of both worlds:
    - Fast response for simple queries (<1ms)
    - Accurate classification for complex queries
    - Explainable decisions when using rules
    """
    
    # ==================== FAST RULES DATA ====================
    
    # Categories that the router recognizes
    CATEGORIES = {
        'laptop', 'monitor', 'keyboard', 'mouse', 'headphones', 'headset',
        'webcam', 'speaker', 'phone', 'tablet', 'desk', 'chair', 'router',
        'charger', 'hub', 'dock', 'microphone', 'camera', 'gpu',
        'cpu', 'tv', 'stand', 'adapter', 'computer', 'pc', 'desktop',
        'earbuds', 'printer', 'scanner', 'projector'
    }
    
    # Component/spec categories that don't count as separate products
    # (these modify other categories, not standalone products for bundles)
    SPEC_CATEGORIES = {
        'ssd', 'hdd', 'ram', 'motherboard', 'case', 'psu', 'cooler', 'fan'
    }
    
    # Categories that can be modifiers (cable, stand can describe other products)
    # When appearing with another main category, these don't trigger multi-category
    MODIFIER_CATEGORIES = {'cable', 'stand', 'mount', 'holder', 'cover', 'sleeve'}
    
    # Plural forms -> singular mapping
    PLURALS = {
        'laptops': 'laptop', 'monitors': 'monitor', 'keyboards': 'keyboard',
        'mice': 'mouse', 'headphones': 'headphones', 'headsets': 'headset',
        'webcams': 'webcam', 'speakers': 'speaker', 'phones': 'phone',
        'tablets': 'tablet', 'desks': 'desk', 'chairs': 'chair',
        'routers': 'router', 'chargers': 'charger', 'cables': 'cable',
        'hubs': 'hub', 'docks': 'dock', 'microphones': 'microphone',
        'cameras': 'camera', 'gpus': 'gpu', 'cpus': 'cpu', 'tvs': 'tv',
        'stands': 'stand', 'adapters': 'adapter', 'computers': 'computer',
        'notebooks': 'laptop', 'displays': 'monitor', 'screens': 'monitor',
        'earbuds': 'headphones', 'mics': 'microphone', 'cams': 'camera',
        'processors': 'cpu', 'printers': 'printer', 'projectors': 'projector'
    }
    
    # Bundle keywords that trigger DEEP path
    BUNDLE_KEYWORDS = {
        'setup', 'kit', 'bundle', 'combo', 'package', 'build', 'workstation',
        'complete', 'entire', 'whole', 'full set', 'everything for',
        'all i need', 'starter', 'essentials'
    }
    
    # Multi-category connectors
    MULTI_CATEGORY_CONNECTORS = {
        ' and ', ' with ', ' plus ', ' + ', ' & ', ', '
    }
    
    # Quality words that keep query in FAST path
    FAST_QUALITY_WORDS = {
        'good', 'best', 'cheap', 'nice', 'great', 'top', 'quality',
        'affordable', 'budget', 'premium', 'excellent', 'perfect'
    }
    
    # Modifiers that can combine with quality words and stay FAST
    FAST_MODIFIERS = {
        'really', 'very', 'super', 'so', 'fairly', 'extremely', 
        'quite', 'pretty', 'incredibly', 'absolutely'
    }
    
    # Features that trigger SMART path (single category + specs)
    SMART_FEATURES = {
        'gaming', 'wireless', 'bluetooth', 'mechanical', 'ergonomic',
        'rgb', '4k', '1440p', '1080p', 'ultrawide', 'curved',
        '144hz', '165hz', '240hz', 'noise cancelling', 'usb-c',
        'thunderbolt', 'portable', 'lightweight', 'compact'
    }
    
    # Features that trigger DEEP path (typically multi-category related)
    DEEP_FEATURES = {
        'wifi', 'wifi 6', 'wifi 6e', 'premium build', '8k'
    }
    
    # ==================== INITIALIZATION ====================
    
    def __init__(
        self, 
        model_path: Optional[str] = None,
        use_onnx: bool = True,
        confidence_threshold: float = 0.7
    ):
        """
        Initialize the hybrid router.
        
        Args:
            model_path: Path to trained model directory. If None, only uses rules.
            use_onnx: Whether to use ONNX runtime for faster inference.
            confidence_threshold: Minimum confidence for rule-based decisions
                                 before falling back to model.
        """
        self.model_path = model_path
        self.use_onnx = use_onnx
        self.confidence_threshold = confidence_threshold
        
        # Model components (lazy loaded)
        self._model = None
        self._tokenizer = None
        self._model_type = None
        self._onnx_session = None
        self._model_config = None
        
        # Compile regex patterns for speed
        self._compile_patterns()
        
        # Statistics
        self.stats = {
            "total_queries": 0,
            "rules_used": 0,
            "model_used": 0,
            "avg_latency_ms": 0
        }
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for faster matching."""
        # Category pattern (include all category types)
        all_cats = self.CATEGORIES | self.SPEC_CATEGORIES | self.MODIFIER_CATEGORIES | set(self.PLURALS.keys())
        self._category_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(c) for c in sorted(all_cats, key=len, reverse=True)) + r')\b',
            re.IGNORECASE
        )
        
        # Bundle keyword pattern
        self._bundle_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(k) for k in self.BUNDLE_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        
        # Budget pattern
        self._budget_pattern = re.compile(
            r'(?:under|below|max|up to|less than|budget)?\s*'
            r'[\$£€]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*'
            r'(?:dollars?|usd|bucks?)?',
            re.IGNORECASE
        )
    
    # ==================== MODEL LOADING ====================
    
    def _load_model(self):
        """Lazy load the ML model."""
        if self.model_path is None:
            return
        
        model_dir = Path(self.model_path)
        
        # Check for ONNX model first
        onnx_path = model_dir / "model.onnx"
        if self.use_onnx and onnx_path.exists():
            self._load_onnx_model(onnx_path)
            return
        
        # Check for LSTM model
        lstm_path = model_dir / "model.pt"
        if lstm_path.exists():
            self._load_lstm_model(model_dir)
            return
        
        # Check for transformer model
        config_path = model_dir / "config.json"
        if config_path.exists():
            self._load_transformer_model(model_dir)
            return
        
        print(f"Warning: No model found in {model_dir}")
    
    def _load_onnx_model(self, onnx_path: Path):
        """Load ONNX model for fast inference."""
        try:
            import onnxruntime as ort
            
            self._onnx_session = ort.InferenceSession(
                str(onnx_path),
                providers=['CPUExecutionProvider']
            )
            self._model_type = "onnx"
            
            # Load tokenizer
            tokenizer_path = onnx_path.parent / "tokenizer.json"
            if tokenizer_path.exists():
                self._load_lstm_tokenizer(onnx_path.parent)
            else:
                from transformers import AutoTokenizer
                self._tokenizer = AutoTokenizer.from_pretrained(onnx_path.parent)
            
            print(f"Loaded ONNX model from {onnx_path}")
        except ImportError:
            print("ONNX Runtime not installed. Falling back to PyTorch.")
            self.use_onnx = False
            self._load_model()
    
    def _load_lstm_model(self, model_dir: Path):
        """Load LSTM model."""
        import torch
        from scripts.train_router_model import LSTMClassifier, LSTMTokenizer
        
        # Load config
        with open(model_dir / "config.json") as f:
            self._model_config = json.load(f)
        
        # Load model
        self._model = LSTMClassifier(
            vocab_size=self._model_config["vocab_size"],
            embedding_dim=self._model_config["embedding_dim"],
            hidden_dim=self._model_config["hidden_dim"],
            num_classes=self._model_config["num_classes"]
        )
        self._model.load_state_dict(torch.load(model_dir / "model.pt", map_location="cpu"))
        self._model.eval()
        
        # Load tokenizer
        self._tokenizer = LSTMTokenizer.load(model_dir / "tokenizer.json")
        self._model_type = "lstm"
        
        print(f"Loaded LSTM model from {model_dir}")
    
    def _load_lstm_tokenizer(self, model_dir: Path):
        """Load LSTM tokenizer for ONNX model."""
        from scripts.train_router_model import LSTMTokenizer
        self._tokenizer = LSTMTokenizer.load(model_dir / "tokenizer.json")
    
    def _load_transformer_model(self, model_dir: Path):
        """Load transformer model."""
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        
        self._tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self._model = AutoModelForSequenceClassification.from_pretrained(model_dir)
        self._model.eval()
        self._model_type = "transformer"
        
        print(f"Loaded transformer model from {model_dir}")
    
    # ==================== ROUTING LOGIC ====================
    
    def route(self, query: str, budget: Optional[float] = None, afig_context: Dict = None) -> str:
        """
        Route a query to the appropriate processing path.
        
        Args:
            query: The search query string.
            budget: Optional budget constraint.
            afig_context: Optional AFIG context (ignored, for compatibility).
        
        Returns:
            String path name: "fast", "smart", or "deep".
        """
        result = self.route_detailed(query, budget)
        return result.path.value
    
    def route_detailed(self, query: str, budget: Optional[float] = None) -> RouteResult:
        """
        Route a query with detailed information about the decision.
        
        Args:
            query: The search query string.
            budget: Optional budget constraint.
        
        Returns:
            RouteResult with path, confidence, and metadata.
        """
        start_time = time.perf_counter()
        
        query_lower = query.lower().strip()
        
        # Parse budget if present in query
        if budget is None:
            budget = self._extract_budget(query_lower)
        
        # Stage 1: Fast deterministic rules
        rule_result = self._apply_rules(query_lower, budget)
        
        if rule_result is not None and rule_result.confidence >= self.confidence_threshold:
            rule_result.latency_ms = (time.perf_counter() - start_time) * 1000
            self._update_stats(rule_result)
            return rule_result
        
        # Stage 2: Model fallback (if available)
        if self.model_path is not None:
            model_result = self._apply_model(query, budget)
            if model_result is not None:
                # Merge with rule insights
                if rule_result is not None:
                    model_result.categories = rule_result.categories
                    model_result.is_bundle = rule_result.is_bundle
                model_result.latency_ms = (time.perf_counter() - start_time) * 1000
                self._update_stats(model_result)
                return model_result
        
        # Fallback to rule result (even if low confidence) or default
        if rule_result is not None:
            rule_result.latency_ms = (time.perf_counter() - start_time) * 1000
            self._update_stats(rule_result)
            return rule_result
        
        # Default to SMART if nothing else matches
        default_result = RouteResult(
            path=RoutePath.SMART,
            confidence=0.5,
            method="default",
            latency_ms=(time.perf_counter() - start_time) * 1000,
            categories=[],
            is_bundle=False,
            budget=budget
        )
        self._update_stats(default_result)
        return default_result
    
    def _apply_rules(self, query: str, budget: Optional[float]) -> Optional[RouteResult]:
        """Apply fast deterministic rules."""
        
        # Normalize query - strip punctuation for matching
        import re
        normalized_query = re.sub(r'[!?.,;:\'"]+', '', query).lower().strip()
        
        # Detect categories (main categories and spec categories separately)
        categories, spec_categories = self._detect_categories(normalized_query)
        all_detected = categories + spec_categories
        
        # Detect bundle keywords
        is_bundle = bool(self._bundle_pattern.search(normalized_query))
        
        # Rule 1: Bundle keywords -> DEEP
        if is_bundle:
            return RouteResult(
                path=RoutePath.DEEP,
                confidence=0.95,
                method="rules",
                latency_ms=0,
                categories=all_detected,
                is_bundle=True,
                budget=budget
            )
        
        # Rule 2: Explicit multi-product connector with modifier category -> DEEP
        # e.g., "tablet & cable", "keyboard with cable" - user wants both products
        has_connector = any(conn in normalized_query for conn in self.MULTI_CATEGORY_CONNECTORS)
        if has_connector:
            # Re-check categories including modifiers as separate products
            matches = self._category_pattern.findall(normalized_query)
            all_category_words = []
            for match in matches:
                match_lower = match.lower()
                if match_lower in self.PLURALS:
                    all_category_words.append(self.PLURALS[match_lower])
                elif match_lower in self.CATEGORIES or match_lower in self.MODIFIER_CATEGORIES:
                    all_category_words.append(match_lower)
            
            # Remove duplicates but keep order
            unique_cats = list(dict.fromkeys(all_category_words))
            if len(unique_cats) >= 2:
                return RouteResult(
                    path=RoutePath.DEEP,
                    confidence=0.9,
                    method="rules",
                    latency_ms=0,
                    categories=unique_cats,
                    is_bundle=False,
                    budget=budget
                )
        
        # Rule 3: Multiple main categories -> DEEP
        # (spec categories like ram, ssd don't count as separate products)
        if len(categories) >= 2:
            return RouteResult(
                path=RoutePath.DEEP,
                confidence=0.9,
                method="rules",
                latency_ms=0,
                categories=all_detected,
                is_bundle=False,
                budget=budget
            )
        
        # Rule 4: Deep features (wifi, etc.) -> DEEP
        for feature in self.DEEP_FEATURES:
            if feature in normalized_query:
                return RouteResult(
                    path=RoutePath.DEEP,
                    confidence=0.85,
                    method="rules",
                    latency_ms=0,
                    categories=all_detected,
                    is_bundle=False,
                    budget=budget
                )
        
        # Rule 5: Single main category (with or without specs) -> FAST or SMART
        if len(categories) == 1:
            # Check if it's just the category word (with optional quality/modifier)
            words = set(normalized_query.split())
            category_word = categories[0]
            other_words = words - {category_word} - self.FAST_QUALITY_WORDS - self.FAST_MODIFIERS
            
            # Remove common filler words
            filler = {'a', 'an', 'the', 'for', 'my', 'me', 'i', 'need', 'want', 'looking'}
            other_words = other_words - filler
            
            # If there are spec categories or SMART features, go SMART
            has_specs = len(spec_categories) > 0
            has_smart_feature = any(f in normalized_query for f in self.SMART_FEATURES)
            
            if has_specs or has_smart_feature:
                return RouteResult(
                    path=RoutePath.SMART,
                    confidence=0.85,
                    method="rules",
                    latency_ms=0,
                    categories=all_detected,
                    is_bundle=False,
                    budget=budget
                )
            
            if len(other_words) == 0:
                return RouteResult(
                    path=RoutePath.FAST,
                    confidence=0.95,
                    method="rules",
                    latency_ms=0,
                    categories=all_detected,
                    is_bundle=False,
                    budget=budget
                )
            
            # Single category with some other words -> SMART
            return RouteResult(
                path=RoutePath.SMART,
                confidence=0.7,
                method="rules",
                latency_ms=0,
                categories=all_detected,
                is_bundle=False,
                budget=budget
            )
        
        # Spec categories only (no main category) -> SMART
        if len(spec_categories) > 0:
            return RouteResult(
                path=RoutePath.SMART,
                confidence=0.7,
                method="rules",
                latency_ms=0,
                categories=all_detected,
                is_bundle=False,
                budget=budget
            )
        
        # No clear category detected -> low confidence, might need model
        return RouteResult(
            path=RoutePath.SMART,
            confidence=0.4,
            method="rules",
            latency_ms=0,
            categories=all_detected,
            is_bundle=False,
            budget=budget
        )
    
    def _apply_model(self, query: str, budget: Optional[float]) -> Optional[RouteResult]:
        """Apply ML model for classification."""
        
        # Lazy load model
        if self._model is None and self._onnx_session is None:
            self._load_model()
        
        if self._model is None and self._onnx_session is None:
            return None
        
        try:
            import torch
            
            # Tokenize
            max_length = self._model_config.get("max_length", 64) if self._model_config else 64
            inputs = self._tokenizer(
                query, 
                truncation=True, 
                padding="max_length",
                max_length=max_length,
                return_tensors="pt"
            )
            
            # Inference
            if self._onnx_session is not None:
                # ONNX inference
                import numpy as np
                if isinstance(inputs["input_ids"], torch.Tensor):
                    input_ids = inputs["input_ids"].numpy()
                else:
                    input_ids = np.array([inputs["input_ids"]])
                
                ort_inputs = {"input_ids": input_ids}
                if "attention_mask" in inputs:
                    if isinstance(inputs["attention_mask"], torch.Tensor):
                        ort_inputs["attention_mask"] = inputs["attention_mask"].numpy()
                    else:
                        ort_inputs["attention_mask"] = np.array([inputs["attention_mask"]])
                
                logits = self._onnx_session.run(None, ort_inputs)[0]
                probs = self._softmax(logits[0])
                pred = int(np.argmax(probs))
                confidence = float(probs[pred])
            else:
                # PyTorch inference
                with torch.no_grad():
                    if self._model_type == "lstm":
                        logits = self._model(inputs["input_ids"])
                    else:
                        outputs = self._model(**inputs)
                        logits = outputs.logits
                    
                    probs = torch.softmax(logits, dim=-1)
                    pred = probs.argmax(-1).item()
                    confidence = probs[0, pred].item()
            
            # Map prediction to path
            path_map = {0: RoutePath.FAST, 1: RoutePath.SMART, 2: RoutePath.DEEP}
            
            return RouteResult(
                path=path_map[pred],
                confidence=confidence,
                method="model",
                latency_ms=0,
                categories=[],
                is_bundle=False,
                budget=budget
            )
        
        except Exception as e:
            print(f"Model inference error: {e}")
            return None
    
    def _softmax(self, x):
        """Compute softmax."""
        import numpy as np
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()
    
    # ==================== HELPER METHODS ====================
    
    def _detect_categories(self, query: str) -> List[str]:
        """Detect product categories in query."""
        matches = self._category_pattern.findall(query)
        
        # Normalize to singular form
        categories = set()
        spec_categories = set()
        modifier_categories = set()
        
        for match in matches:
            match_lower = match.lower()
            if match_lower in self.PLURALS:
                cat = self.PLURALS[match_lower]
                if cat in self.SPEC_CATEGORIES:
                    spec_categories.add(cat)
                elif cat in self.MODIFIER_CATEGORIES:
                    modifier_categories.add(cat)
                else:
                    categories.add(cat)
            elif match_lower in self.CATEGORIES:
                categories.add(match_lower)
            elif match_lower in self.SPEC_CATEGORIES:
                spec_categories.add(match_lower)
            elif match_lower in self.MODIFIER_CATEGORIES:
                modifier_categories.add(match_lower)
        
        # If we have main categories AND modifier categories, 
        # the modifiers are just describing the main category (e.g., "cable headphones")
        # Only count modifier categories as main categories if they're the ONLY category
        if len(categories) == 0 and len(modifier_categories) > 0:
            categories = modifier_categories
        
        # Return main categories (spec categories handled separately)
        return list(categories), list(spec_categories)
    
    def _extract_budget(self, query: str) -> Optional[float]:
        """Extract budget from query string."""
        match = self._budget_pattern.search(query)
        if match:
            try:
                value = match.group(1).replace(',', '')
                return float(value)
            except ValueError:
                pass
        return None
    
    def _update_stats(self, result: RouteResult):
        """Update routing statistics."""
        self.stats["total_queries"] += 1
        if result.method == "rules":
            self.stats["rules_used"] += 1
        else:
            self.stats["model_used"] += 1
        
        # Running average of latency
        n = self.stats["total_queries"]
        self.stats["avg_latency_ms"] = (
            (self.stats["avg_latency_ms"] * (n - 1) + result.latency_ms) / n
        )
    
    def get_stats(self) -> Dict:
        """Get routing statistics."""
        total = self.stats["total_queries"]
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            "rules_percentage": self.stats["rules_used"] / total * 100,
            "model_percentage": self.stats["model_used"] / total * 100
        }
    
    # ==================== COMPATIBILITY ====================
    
    def classify(self, query: str, budget: Optional[float] = None) -> Tuple[str, List[str]]:
        """
        Compatibility method matching the original QueryRouter interface.
        
        Returns:
            Tuple of (path_name, detected_categories)
        """
        result = self.route_detailed(query, budget)
        return result.path.value, result.categories
    
    def get_cache_key(self, query: str, budget: float, archetype: str) -> str:
        """
        Generate deterministic cache key for Fast Path results.
        Compatible with the original QueryRouter interface.
        """
        import hashlib
        q_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()[:8]
        budget_tier = int(round(budget / 100) * 100) if budget else 0
        return f"fast:{q_hash}:{budget_tier}:{archetype}"
    
    def get_query_intent(self, query: str) -> Dict[str, Any]:
        """
        Extract structured intent from query.
        Compatible with the original QueryRouter interface.
        """
        query_lower = query.lower().strip()
        
        # Normalize query for detection
        import re
        normalized = re.sub(r'[!?.,;:\'"]+', '', query_lower)
        
        # Detect categories
        categories, spec_categories = self._detect_categories(normalized)
        
        # Detect bundle
        is_bundle = bool(self._bundle_pattern.search(normalized))
        
        # Extract budget
        budget = self._extract_budget(query_lower)
        
        # Detect features
        features = []
        for feature in self.SMART_FEATURES | self.DEEP_FEATURES:
            if feature in normalized:
                features.append(feature)
        
        return {
            'raw_query': query,
            'budget': {'max': budget} if budget else {},
            'is_bundle': is_bundle,
            'categories': categories + spec_categories,
            'brands': [],  # Could be extended
            'features': features,
            'specifications': {},  # Could be extended
            'use_case': ''  # Could be extended
        }


# ==================== FACTORY FUNCTION ====================

def create_router(
    model_path: Optional[str] = None,
    prefer_speed: bool = True
) -> HybridQueryRouter:
    """
    Factory function to create an appropriate router.
    
    Args:
        model_path: Path to trained model. If None, uses rules only.
        prefer_speed: If True, uses ONNX when available for faster inference.
    
    Returns:
        Configured HybridQueryRouter instance.
    """
    return HybridQueryRouter(
        model_path=model_path,
        use_onnx=prefer_speed
    )


# ==================== MAIN (for testing) ====================

if __name__ == "__main__":
    # Test the router
    router = HybridQueryRouter()
    
    test_queries = [
        # FAST (single category)
        ("laptop", None),
        ("best keyboard", None),
        ("cheap mouse", None),
        
        # SMART (category + features)
        ("gaming laptop under $1000", 1000),
        ("wireless mechanical keyboard", None),
        ("4k monitor for video editing", None),
        
        # DEEP (multi-category or bundle)
        ("laptop and mouse", None),
        ("gaming setup", None),
        ("complete home office kit", None),
        ("laptop with monitor and keyboard", None),
    ]
    
    print("Testing HybridQueryRouter (rules only)\n")
    print(f"{'Query':<45} {'Path':<8} {'Conf':<6} {'Method':<8} {'Categories'}")
    print("-" * 90)
    
    for query, budget in test_queries:
        result = router.route_detailed(query, budget)
        cats = ", ".join(result.categories) if result.categories else "-"
        print(f"{query:<45} {result.path.value:<8} {result.confidence:.2f}   {result.method:<8} {cats}")
    
    print("\n" + "=" * 90)
    print(f"Stats: {router.get_stats()}")
