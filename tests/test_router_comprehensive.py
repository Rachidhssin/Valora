"""
Comprehensive Router Test Suite
================================
Generates 1000+ diverse test cases to validate the two-stage query routing system.

Test Categories:
1. Single-word category tests (FAST)
2. Quality word combinations (FAST)
3. Use case + category combinations (SMART)
4. Feature + category combinations (SMART)
5. Multi-feature combinations (SMART)
6. Specification patterns (SMART)
7. Budget patterns (SMART)
8. Brand + category combinations (SMART)
9. Bundle keyword patterns (DEEP)
10. Multi-category combinations (DEEP)
11. Cross-category comparisons (DEEP)
12. Complex bundle with specs (DEEP)
13. Edge cases and boundary conditions
14. Noise and typo resilience
15. Natural language variations
"""

import sys
import os
import time
import random
import itertools
from dataclasses import dataclass
from typing import List, Tuple, Optional
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.router import QueryRouter, RoutePath


@dataclass
class TestCase:
    query: str
    budget: Optional[float]
    expected_path: str
    category: str  # Test category for reporting
    
    def __hash__(self):
        return hash((self.query.lower(), self.budget, self.expected_path))


class RouterTestGenerator:
    """Generates comprehensive test cases for the query router."""
    
    # Product categories (singular forms)
    CATEGORIES = [
        'laptop', 'monitor', 'keyboard', 'mouse', 'headphones', 'headset',
        'webcam', 'speaker', 'phone', 'tablet', 'desk', 'chair', 'router',
        'charger', 'cable', 'hub', 'dock', 'microphone', 'camera', 'gpu',
        'cpu', 'tv', 'stand', 'adapter'
    ]
    
    # Plural forms
    PLURALS = {
        'laptop': ['laptops', 'notebooks'],
        'monitor': ['monitors', 'displays', 'screens'],
        'keyboard': ['keyboards'],
        'mouse': ['mice', 'mouses'],
        'headphones': ['headphones', 'earbuds'],
        'headset': ['headsets'],
        'webcam': ['webcams'],
        'speaker': ['speakers', 'soundbars'],
        'phone': ['phones', 'smartphones'],
        'tablet': ['tablets', 'ipads'],
        'desk': ['desks'],
        'chair': ['chairs'],
        'router': ['routers'],
        'charger': ['chargers'],
        'cable': ['cables', 'cords'],
        'hub': ['hubs'],
        'dock': ['docks'],
        'microphone': ['microphones', 'mics'],
        'camera': ['cameras'],
        'gpu': ['gpus', 'graphics cards'],
        'cpu': ['cpus', 'processors'],
        'tv': ['tvs', 'televisions'],
        'stand': ['stands'],
        'adapter': ['adapters']
    }
    
    # Quality words (allowed in FAST path)
    QUALITY_WORDS = ['good', 'best', 'cheap', 'nice', 'great', 'top', 'quality']
    
    # Use case keywords (trigger SMART path)
    USE_CASES = [
        'gaming', 'office', 'work', 'streaming', 'coding', 'programming',
        'video editing', 'music production', 'travel', 'school', 'business',
        'home', 'professional', 'studio', 'content creation', 'esports',
        'casual', 'competitive', 'productivity', 'creative'
    ]
    
    # Feature keywords (trigger SMART path)
    FEATURES = [
        'wireless', 'wired', 'bluetooth', 'mechanical', 'membrane',
        'rgb', 'backlit', 'noise cancelling', 'ergonomic', 'portable',
        '4k', '1440p', '1080p', 'curved', 'ultrawide', 'hdr',
        'usb-c', 'thunderbolt', 'waterproof', 'quiet', 'silent',
        'adjustable', 'foldable', 'compact', 'full-size', 'tenkeyless',
        'hot-swappable', 'programmable', 'macro', 'low-latency'
    ]
    
    # Brands
    BRANDS = [
        'logitech', 'corsair', 'razer', 'dell', 'hp', 'asus', 'samsung',
        'lg', 'acer', 'msi', 'nvidia', 'amd', 'intel', 'apple', 'sony',
        'bose', 'jbl', 'steelseries', 'hyperx', 'benq', 'lenovo', 'microsoft',
        'google', 'xiaomi', 'anker', 'sennheiser', 'audio-technica', 'elgato',
        'rode', 'shure', 'blue', 'kingston', 'crucial', 'seagate', 'western digital'
    ]
    
    # Bundle keywords (trigger DEEP path)
    BUNDLE_KEYWORDS = [
        'setup', 'bundle', 'kit', 'combo', 'package', 'build',
        'workstation', 'rig', 'system', 'complete', 'full set',
        'starter kit', 'all-in-one', 'entire', 'whole'
    ]
    
    # Bundle contexts
    BUNDLE_CONTEXTS = [
        'gaming', 'streaming', 'office', 'home office', 'work from home',
        'podcast', 'youtube', 'content creation', 'video production',
        'music production', 'pc', 'custom pc', 'esports', 'professional'
    ]
    
    # Specifications
    RAM_SPECS = ['4gb', '8gb', '16gb', '32gb', '64gb', '128gb']
    STORAGE_SPECS = ['128gb', '256gb', '512gb', '1tb', '2tb', '4tb']
    DISPLAY_SPECS = ['24 inch', '27 inch', '32 inch', '34 inch', '49 inch']
    REFRESH_SPECS = ['60hz', '75hz', '120hz', '144hz', '165hz', '240hz', '360hz']
    PROCESSOR_SPECS = ['i3', 'i5', 'i7', 'i9', 'ryzen 3', 'ryzen 5', 'ryzen 7', 'ryzen 9', 'm1', 'm2', 'm3']
    
    # Budget patterns
    BUDGET_PATTERNS = [
        ('under ${}', 'max'),
        ('below ${}', 'max'),
        ('less than ${}', 'max'),
        ('up to ${}', 'max'),
        ('for ${}', 'exact'),
        ('around ${}', 'around'),
        ('about ${}', 'around'),
        ('${} budget', 'exact'),
        ('over ${}', 'min'),
        ('more than ${}', 'min'),
        ('at least ${}', 'min'),
    ]
    
    BUDGET_VALUES = [50, 100, 150, 200, 250, 300, 400, 500, 750, 1000, 1200, 1500, 2000, 2500, 3000, 5000]
    
    def __init__(self):
        self.test_cases: List[TestCase] = []
        self.seen_queries = set()
    
    def _add_test(self, query: str, budget: Optional[float], expected: str, category: str):
        """Add a test case, avoiding duplicates."""
        key = (query.lower().strip(), budget)
        if key not in self.seen_queries:
            self.seen_queries.add(key)
            self.test_cases.append(TestCase(query, budget, expected, category))
    
    def generate_fast_path_tests(self):
        """Generate FAST path test cases - simple lookups."""
        
        # 1. Single word categories
        for cat in self.CATEGORIES:
            self._add_test(cat, None, "fast", "single_category")
        
        # 2. Plural forms (single-word only for FAST, multi-word go to SMART)
        for cat, plurals in self.PLURALS.items():
            for plural in plurals:
                # Multi-word plurals (like "graphics cards") go to SMART
                if ' ' in plural:
                    self._add_test(plural, None, "smart", "plural_category")
                else:
                    self._add_test(plural, None, "fast", "plural_category")
        
        # 3. Quality word + category (2 words)
        for quality in self.QUALITY_WORDS:
            for cat in random.sample(self.CATEGORIES, min(10, len(self.CATEGORIES))):
                self._add_test(f"{quality} {cat}", None, "fast", "quality_category")
        
        # 4. Quality word + plural
        for quality in self.QUALITY_WORDS:
            for cat in random.sample(list(self.PLURALS.keys()), 5):
                plural = random.choice(self.PLURALS[cat])
                self._add_test(f"{quality} {plural}", None, "fast", "quality_plural")
        
        # 5. Two quality words + category (3 words max)
        quality_pairs = [('really', 'good'), ('very', 'nice'), ('super', 'cheap')]
        for q1, q2 in quality_pairs:
            for cat in random.sample(self.CATEGORIES, 3):
                self._add_test(f"{q1} {q2} {cat}", None, "fast", "double_quality")
    
    def generate_smart_path_tests(self):
        """Generate SMART path test cases - single category with specs/features."""
        
        # 1. Use case + category
        for use_case in self.USE_CASES:
            for cat in random.sample(self.CATEGORIES, 8):
                self._add_test(f"{use_case} {cat}", None, "smart", "use_case_category")
        
        # 2. Feature + category
        for feature in self.FEATURES:
            for cat in random.sample(self.CATEGORIES, 5):
                self._add_test(f"{feature} {cat}", None, "smart", "feature_category")
        
        # 3. Quality + use case + category
        for quality in random.sample(self.QUALITY_WORDS, 3):
            for use_case in random.sample(self.USE_CASES, 5):
                for cat in random.sample(self.CATEGORIES, 3):
                    self._add_test(f"{quality} {use_case} {cat}", None, "smart", "quality_use_case")
        
        # 4. Feature + feature + category (multi-feature)
        feature_pairs = list(itertools.combinations(random.sample(self.FEATURES, 10), 2))
        for f1, f2 in random.sample(feature_pairs, min(30, len(feature_pairs))):
            cat = random.choice(self.CATEGORIES)
            self._add_test(f"{f1} {f2} {cat}", None, "smart", "multi_feature")
        
        # 5. Brand + category
        for brand in self.BRANDS:
            for cat in random.sample(self.CATEGORIES, 3):
                self._add_test(f"{brand} {cat}", None, "smart", "brand_category")
        
        # 6. Brand + feature + category
        for brand in random.sample(self.BRANDS, 15):
            feature = random.choice(self.FEATURES)
            cat = random.choice(self.CATEGORIES)
            self._add_test(f"{brand} {feature} {cat}", None, "smart", "brand_feature")
        
        # 7. RAM specs + laptop
        for ram in self.RAM_SPECS:
            self._add_test(f"{ram} laptop", None, "smart", "ram_spec")
            self._add_test(f"{ram} ram laptop", None, "smart", "ram_spec")
            self._add_test(f"laptop with {ram}", None, "smart", "ram_spec")
            self._add_test(f"laptop with {ram} ram", None, "smart", "ram_spec")
        
        # 8. Storage specs + laptop
        for storage in self.STORAGE_SPECS:
            self._add_test(f"{storage} ssd laptop", None, "smart", "storage_spec")
            self._add_test(f"laptop with {storage}", None, "smart", "storage_spec")
        
        # 9. Display specs + monitor
        for display in self.DISPLAY_SPECS:
            self._add_test(f"{display} monitor", None, "smart", "display_spec")
        
        # 10. Refresh rate specs + monitor
        for refresh in self.REFRESH_SPECS:
            self._add_test(f"{refresh} monitor", None, "smart", "refresh_spec")
            self._add_test(f"{refresh} gaming monitor", None, "smart", "refresh_spec")
        
        # 11. Processor specs + laptop
        for proc in self.PROCESSOR_SPECS:
            self._add_test(f"{proc} laptop", None, "smart", "processor_spec")
        
        # 12. Budget patterns + category
        for pattern, _ in self.BUDGET_PATTERNS:
            for value in random.sample(self.BUDGET_VALUES, 3):
                for cat in random.sample(self.CATEGORIES, 3):
                    query = f"{cat} {pattern.format(value)}"
                    self._add_test(query, float(value), "smart", "budget_category")
        
        # 13. Complex specs + budget
        for ram in random.sample(self.RAM_SPECS, 3):
            for value in random.sample(self.BUDGET_VALUES, 3):
                self._add_test(f"{ram} ram laptop under ${value}", float(value), "smart", "complex_spec")
        
        # 14. Use case + feature + category
        for use_case in random.sample(self.USE_CASES, 5):
            for feature in random.sample(self.FEATURES, 5):
                for cat in random.sample(self.CATEGORIES, 2):
                    self._add_test(f"{use_case} {feature} {cat}", None, "smart", "use_case_feature")
        
        # 15. Same-category comparisons (SMART, not Deep)
        same_cat_comparisons = [
            ("macbook vs windows laptop", "laptop"),
            ("mechanical vs membrane keyboard", "keyboard"),
            ("wired vs wireless mouse", "mouse"),
            ("over-ear vs in-ear headphones", "headphones"),
            ("ips vs va monitor", "monitor"),
            ("oled vs lcd tv", "tv"),
            ("condenser vs dynamic microphone", "microphone"),
            ("dslr vs mirrorless camera", "camera"),
            ("ssd vs hdd storage", "storage"),
            ("nvidia vs amd gpu", "gpu"),
            ("intel vs amd cpu", "cpu"),
            ("usb vs wireless webcam", "webcam"),
            ("bookshelf vs tower speakers", "speakers"),
            ("standing vs sitting desk", "desk"),
            ("mesh vs leather chair", "chair"),
        ]
        for query, _ in same_cat_comparisons:
            self._add_test(query, None, "smart", "same_category_comparison")
        
        # 16. Plural with features (SMART, not Deep)
        for feature in random.sample(self.FEATURES, 10):
            for cat in random.sample(list(self.PLURALS.keys()), 5):
                plural = random.choice(self.PLURALS[cat])
                self._add_test(f"{feature} {plural}", None, "smart", "feature_plural")
        
        # 17. Natural language queries
        natural_queries = [
            "i need a laptop for school",
            "looking for a gaming mouse",
            "want wireless headphones",
            "need a monitor for work",
            "searching for mechanical keyboard",
            "find me a good webcam",
            "show me gaming laptops",
            "recommend a 4k monitor",
            "suggest a quiet keyboard",
            "what's a good streaming mic",
        ]
        for query in natural_queries:
            self._add_test(query, None, "smart", "natural_language")
    
    def generate_deep_path_tests(self):
        """Generate DEEP path test cases - bundles and multi-category."""
        
        # 1. Bundle keywords alone
        for bundle in self.BUNDLE_KEYWORDS:
            self._add_test(bundle, None, "deep", "bundle_keyword")
        
        # 2. Context + bundle keyword
        for context in self.BUNDLE_CONTEXTS:
            for bundle in random.sample(self.BUNDLE_KEYWORDS, 5):
                self._add_test(f"{context} {bundle}", None, "deep", "context_bundle")
        
        # 3. "complete" + context + bundle
        for context in random.sample(self.BUNDLE_CONTEXTS, 8):
            self._add_test(f"complete {context} setup", None, "deep", "complete_bundle")
            self._add_test(f"full {context} kit", None, "deep", "complete_bundle")
        
        # 4. Multi-category with "and"
        cat_pairs = list(itertools.combinations(self.CATEGORIES, 2))
        for cat1, cat2 in random.sample(cat_pairs, min(80, len(cat_pairs))):
            self._add_test(f"{cat1} and {cat2}", None, "deep", "multi_category_and")
        
        # 5. Multi-category with "with"
        for cat1, cat2 in random.sample(cat_pairs, 30):
            self._add_test(f"{cat1} with {cat2}", None, "deep", "multi_category_with")
        
        # 6. Multi-category with comma
        for cat1, cat2 in random.sample(cat_pairs, 20):
            self._add_test(f"{cat1}, {cat2}", None, "deep", "multi_category_comma")
        
        # 7. Three categories
        cat_triples = list(itertools.combinations(random.sample(self.CATEGORIES, 12), 3))
        for cats in random.sample(cat_triples, min(30, len(cat_triples))):
            self._add_test(f"{cats[0]} {cats[1]} {cats[2]}", None, "deep", "three_categories")
            self._add_test(f"{cats[0]} and {cats[1]} and {cats[2]}", None, "deep", "three_categories")
        
        # 8. Cross-category comparisons
        cross_comparisons = [
            "laptop vs desktop",
            "laptop or desktop",
            "tablet vs laptop",
            "phone vs tablet",
            "monitor vs tv",
            "headphones vs speakers",
            "webcam vs camera",
            # Note: "keyboard vs controller" -> SMART because "controller" isn't a category
            "wired vs wireless setup",
        ]
        for query in cross_comparisons:
            self._add_test(query, None, "deep", "cross_category_comparison")
            self._add_test(f"{query} for gaming", None, "deep", "cross_category_comparison")
        
        # Add keyboard vs controller as Smart (controller not in categories)
        self._add_test("keyboard vs controller", None, "smart", "same_category_comparison")
        self._add_test("keyboard vs controller for gaming", None, "deep", "cross_category_comparison")  # LLM routes this
        
        # 9. Bundle with budget
        for context in random.sample(self.BUNDLE_CONTEXTS, 5):
            for value in random.sample(self.BUDGET_VALUES, 5):
                self._add_test(f"{context} setup under ${value}", float(value), "deep", "bundle_budget")
                self._add_test(f"{context} bundle for ${value}", float(value), "deep", "bundle_budget")
        
        # 10. Multi-category with budget
        for cat1, cat2 in random.sample(cat_pairs, 20):
            value = random.choice(self.BUDGET_VALUES)
            self._add_test(f"{cat1} and {cat2} under ${value}", float(value), "deep", "multi_category_budget")
        
        # 11. Specific bundle patterns (some will go Smart if no bundle keyword)
        specific_bundles = [
            ("desk setup with monitor and keyboard", None, "deep", "specific_bundle"),
            ("gaming station with pc and peripherals", None, "deep", "specific_bundle"),
            ("streaming essentials kit", None, "deep", "specific_bundle"),
            ("youtuber starter pack", None, "smart", "specific_bundle"),  # No bundle keyword
            ("podcast recording equipment", None, "smart", "specific_bundle"),  # No bundle keyword
            ("home studio gear", None, "deep", "specific_bundle"),  # studio = Deep
            ("remote work essentials", None, "smart", "specific_bundle"),  # No bundle keyword
            ("back to school tech bundle", None, "deep", "specific_bundle"),
            ("dorm room setup", None, "deep", "specific_bundle"),
            ("new apartment tech needs", None, "smart", "specific_bundle"),  # No bundle keyword
            ("upgrade my whole setup", None, "deep", "specific_bundle"),
            ("build a gaming pc", None, "deep", "specific_bundle"),
            ("put together a streaming setup", None, "deep", "specific_bundle"),
            ("need everything for gaming", None, "smart", "specific_bundle"),  # No bundle keyword
            ("starting fresh with new gear", None, "smart", "specific_bundle"),  # No bundle keyword
        ]
        for query, budget, expected, category in specific_bundles:
            self._add_test(query, budget, expected, category)
        
        # 12. Question format (route based on intent, many go Smart for LLM disambiguation)
        question_bundles = [
            ("what do i need for streaming", None, "smart", "question_bundle"),
            ("what should i buy for gaming", None, "smart", "question_bundle"),
            ("what equipment for podcasting", None, "smart", "question_bundle"),
            ("how to build a gaming setup", None, "deep", "question_bundle"),  # build = Deep
            ("what's needed for content creation", None, "deep", "question_bundle"),  # LLM correctly identifies multi-product need
        ]
        for query, budget, expected, category in question_bundles:
            self._add_test(query, budget, expected, category)
    
    def generate_edge_cases(self):
        """Generate edge cases and boundary conditions."""
        
        edge_cases = [
            # Empty-ish queries (should default to smart)
            ("the", None, "smart", "edge_minimal"),
            ("a", None, "smart", "edge_minimal"),
            ("find", None, "smart", "edge_minimal"),
            
            # Very long queries
            ("i am looking for a really good high quality gaming laptop with excellent performance and great battery life for school and work", None, "smart", "edge_long"),
            ("complete professional streaming setup with webcam microphone lighting ring light boom arm headphones mixer audio interface capture card and monitors", None, "deep", "edge_long"),
            
            # Mixed case
            ("LAPTOP", None, "fast", "edge_case"),
            ("GaMiNg MoUsE", None, "smart", "edge_case"),
            ("WIRELESS KEYBOARD", None, "smart", "edge_case"),
            
            # Extra spaces
            ("  laptop  ", None, "fast", "edge_whitespace"),
            ("gaming   mouse", None, "smart", "edge_whitespace"),
            
            # Numbers in queries
            ("top 10 laptops", None, "smart", "edge_numbers"),
            ("best 5 monitors", None, "smart", "edge_numbers"),
            ("number 1 keyboard", None, "smart", "edge_numbers"),
            
            # Special characters (should be cleaned and matched)
            ("laptop!", None, "fast", "edge_special"),
            ("mouse?", None, "fast", "edge_special"),
            ("keyboard...", None, "fast", "edge_special"),
            
            # Common typos/variations - route to Smart (LLM can help)
            ("labtop", None, "smart", "edge_typo"),
            ("keybord", None, "smart", "edge_typo"),
            ("moniter", None, "smart", "edge_typo"),
            
            # Abbreviations
            ("kb", None, "smart", "edge_abbrev"),
            ("hdphn", None, "smart", "edge_abbrev"),
            
            # Price without category
            ("under $500", 500, "smart", "edge_price_only"),
            ("around $1000", 1000, "smart", "edge_price_only"),
            
            # Just features
            ("wireless", None, "smart", "edge_feature_only"),
            ("mechanical", None, "smart", "edge_feature_only"),
            ("rgb", None, "smart", "edge_feature_only"),
            
            # Ambiguous queries (Smart path with LLM disambiguation)
            ("something for gaming", None, "smart", "edge_ambiguous"),
            ("tech stuff", None, "smart", "edge_ambiguous"),
            ("computer things", None, "smart", "edge_ambiguous"),
        ]
        
        for query, budget, expected, category in edge_cases:
            self._add_test(query, budget, expected, category)
    
    def generate_all(self) -> List[TestCase]:
        """Generate all test cases."""
        print("Generating test cases...")
        
        self.generate_fast_path_tests()
        print(f"  FAST path tests: {len(self.test_cases)}")
        fast_count = len(self.test_cases)
        
        self.generate_smart_path_tests()
        print(f"  SMART path tests: {len(self.test_cases) - fast_count}")
        smart_count = len(self.test_cases) - fast_count
        
        self.generate_deep_path_tests()
        print(f"  DEEP path tests: {len(self.test_cases) - fast_count - smart_count}")
        
        self.generate_edge_cases()
        print(f"  Edge cases: added")
        
        print(f"\nTotal unique test cases: {len(self.test_cases)}")
        return self.test_cases


def run_comprehensive_tests():
    """Run all generated test cases."""
    
    # Generate tests
    generator = RouterTestGenerator()
    test_cases = generator.generate_all()
    
    # Initialize router
    router = QueryRouter()
    print(f"\n{'='*80}")
    print(f"🧪 COMPREHENSIVE ROUTER TEST SUITE")
    print(f"{'='*80}")
    print(f"Router LLM Available: {router._groq_client is not None}")
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"{'='*80}\n")
    
    # Run tests
    results = defaultdict(lambda: {'passed': 0, 'failed': 0, 'failures': []})
    overall_passed = 0
    overall_failed = 0
    
    start_time = time.time()
    
    for i, test in enumerate(test_cases):
        # Clear cache for each test
        router.clear_cache()
        
        try:
            decision = router.analyze(test.query, test.budget)
            actual_path = decision.path.value
            
            if actual_path == test.expected_path:
                overall_passed += 1
                results[test.category]['passed'] += 1
            else:
                overall_failed += 1
                results[test.category]['failed'] += 1
                results[test.category]['failures'].append({
                    'query': test.query,
                    'budget': test.budget,
                    'expected': test.expected_path,
                    'actual': actual_path,
                    'reason': decision.reason
                })
        except Exception as e:
            overall_failed += 1
            results[test.category]['failed'] += 1
            results[test.category]['failures'].append({
                'query': test.query,
                'budget': test.budget,
                'expected': test.expected_path,
                'actual': 'ERROR',
                'reason': str(e)
            })
        
        # Progress indicator
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i + 1}/{len(test_cases)} tests completed...")
    
    elapsed = time.time() - start_time
    
    # Print results
    print(f"\n{'='*80}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"Total:  {overall_passed} passed, {overall_failed} failed out of {len(test_cases)}")
    print(f"Time:   {elapsed:.2f}s ({elapsed/len(test_cases)*1000:.1f}ms per test)")
    print(f"Rate:   {overall_passed/len(test_cases)*100:.1f}% pass rate")
    print(f"{'='*80}\n")
    
    # Path breakdown
    fast_cases = [t for t in test_cases if t.expected_path == 'fast']
    smart_cases = [t for t in test_cases if t.expected_path == 'smart']
    deep_cases = [t for t in test_cases if t.expected_path == 'deep']
    
    fast_passed = sum(1 for t in test_cases if t.expected_path == 'fast' and 
                      any(r['passed'] > 0 for cat, r in results.items() 
                          if any(tc.category == cat and tc.expected_path == 'fast' for tc in test_cases)))
    
    print("PATH BREAKDOWN:")
    print(f"  FAST:  {len(fast_cases)} tests")
    print(f"  SMART: {len(smart_cases)} tests")
    print(f"  DEEP:  {len(deep_cases)} tests")
    print()
    
    # Category breakdown
    print("CATEGORY BREAKDOWN:")
    print("-" * 80)
    sorted_categories = sorted(results.keys())
    for category in sorted_categories:
        r = results[category]
        total = r['passed'] + r['failed']
        rate = r['passed'] / total * 100 if total > 0 else 0
        status = "✅" if r['failed'] == 0 else "❌"
        print(f"  {status} {category:35} {r['passed']:4}/{total:4} ({rate:5.1f}%)")
    
    # Failed tests detail
    if overall_failed > 0:
        print(f"\n{'='*80}")
        print(f"FAILED TESTS DETAIL (showing first 50)")
        print(f"{'='*80}")
        
        failure_count = 0
        for category in sorted_categories:
            for failure in results[category]['failures']:
                if failure_count >= 50:
                    break
                print(f"\n  Category: {category}")
                print(f"  Query: '{failure['query']}' (budget: {failure['budget']})")
                print(f"  Expected: {failure['expected'].upper()}")
                print(f"  Actual:   {failure['actual'].upper()}")
                print(f"  Reason:   {failure['reason'][:80]}")
                failure_count += 1
        
        if overall_failed > 50:
            print(f"\n  ... and {overall_failed - 50} more failures")
    
    # Final summary
    print(f"\n{'='*80}")
    if overall_failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {overall_failed} tests failed. Review the failures above.")
    print(f"{'='*80}")
    
    return overall_passed, overall_failed, len(test_cases)


if __name__ == "__main__":
    run_comprehensive_tests()
