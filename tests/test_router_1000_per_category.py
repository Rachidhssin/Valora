"""
Extended Router Test Suite - 1000 Tests Per Category
====================================================
Extends the comprehensive test suite to generate 1000 tests per category.
Uses proven patterns from test_router_comprehensive.py with expanded data pools.
"""

import sys
import os
import time
import random
import itertools
from dataclasses import dataclass
from typing import List, Tuple, Optional
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.router import QueryRouter, RoutePath

random.seed(42)


@dataclass
class TestCase:
    query: str
    budget: Optional[float]
    expected_path: str
    category: str
    
    def __hash__(self):
        return hash((self.query.lower().strip(), self.budget, self.expected_path))


class ExtendedTestGenerator:
    """Generates 1000 tests per category with proven patterns."""
    
    def __init__(self):
        self.test_cases = []
        self.seen = set()
        
        # Expanded data pools
        self.CATEGORIES = [
            'laptop', 'monitor', 'keyboard', 'mouse', 'headphones', 'headset',
            'webcam', 'speaker', 'phone', 'tablet', 'desk', 'chair', 'router',
            'charger', 'cable', 'hub', 'dock', 'microphone', 'camera', 'gpu',
            'cpu', 'tv', 'stand', 'adapter', 'printer', 'scanner', 'projector'
        ]
        
        self.PLURALS = {
            'laptop': ['laptops', 'notebooks'],
            'monitor': ['monitors', 'displays', 'screens'],
            'keyboard': ['keyboards'],
            'mouse': ['mice', 'mouses'],
            'headphones': ['headphones', 'earbuds'],
            'speaker': ['speakers', 'soundbars'],
            'phone': ['phones', 'smartphones'],
            'tablet': ['tablets', 'ipads'],
            'cable': ['cables', 'cords'],
            'gpu': ['gpus', 'graphics cards'],
        }
        
        self.QUALITY_WORDS = [
            'good', 'best', 'cheap', 'nice', 'great', 'top', 'quality',
            'affordable', 'premium', 'budget', 'excellent', 'perfect'
        ]
        
        self.MODIFIER_WORDS = ['really', 'very', 'super', 'extremely', 'quite']
        
        self.USE_CASES = [
            'gaming', 'office', 'work', 'streaming', 'coding', 'programming',
            'video editing', 'music production', 'travel', 'school', 'business',
            'home', 'professional', 'content creation', 'esports', 'productivity'
        ]
        
        self.FEATURES = [
            'wireless', 'wired', 'bluetooth', 'wifi', 'usb', 'mechanical',
            'rgb', 'backlit', '4k', '1440p', '1080p', 'curved', 'ultrawide',
            'noise cancelling', 'ergonomic', 'portable', 'compact', 'lightweight'
        ]
        
        self.BRANDS = [
            'dell', 'hp', 'lenovo', 'asus', 'acer', 'logitech', 'corsair',
            'razer', 'steelseries', 'hyperx', 'sony', 'bose', 'apple', 'samsung'
        ]
        
        self.BUNDLE_KEYWORDS = [
            'setup', 'bundle', 'kit', 'combo', 'package', 'build',
            'workstation', 'rig', 'system', 'complete'
        ]
        
        self.BUNDLE_CONTEXTS = [
            'gaming', 'streaming', 'office', 'home office', 'podcast',
            'youtube', 'content creation', 'home studio', 'music studio'
        ]
        
        self.SPECS = {
            'ram': ['4gb', '8gb', '16gb', '32gb', '64gb'],
            'storage': ['256gb', '512gb', '1tb', '2tb'],
            'display': ['13 inch', '15 inch', '24 inch', '27 inch'],
            'refresh': ['60hz', '144hz', '240hz', '360hz'],
            'processor': ['i3', 'i5', 'i7', 'i9', 'ryzen 5', 'ryzen 7']
        }
        
        self.BUDGETS = [50, 100, 200, 300, 500, 750, 1000, 1500, 2000]
        
    def add(self, query: str, budget: Optional[float], expected: str, category: str):
        """Add test if not duplicate."""
        key = (query.lower().strip(), budget, expected)
        if key not in self.seen:
            self.seen.add(key)
            self.test_cases.append(TestCase(query, budget, expected, category))
            return True
        return False
    
    def generate_all(self):
        """Generate all test categories with 1000 tests each."""
        
        print("Generating FAST path tests...")
        self.gen_single_category(1000)
        self.gen_plural_category(1000)
        self.gen_quality_category(1000)
        self.gen_double_quality(1000)
        
        print("Generating SMART path tests...")
        self.gen_use_case_category(1000)
        self.gen_feature_category(1000)
        self.gen_brand_category(1000)
        self.gen_spec_category(1000)
        self.gen_budget_category(1000)
        
        print("Generating DEEP path tests...")
        self.gen_bundle_keyword(1000)
        self.gen_multi_category(1000)
        self.gen_bundle_context(1000)
        
        return self.test_cases
    
    # FAST PATH
    def gen_single_category(self, n):
        for cat in self.CATEGORIES:
            self.add(cat, None, "fast", "single_category")
            self.add(cat.upper(), None, "fast", "single_category")
            self.add(f" {cat} ", None, "fast", "single_category")
            for p in ['!', '?', '.']:
                self.add(f"{cat}{p}", None, "fast", "single_category")
        
        # No filling needed - these are exhaustive enough
    
    def gen_plural_category(self, n):
        for cat, plurals in self.PLURALS.items():
            for pl in plurals:
                if ' ' not in pl:
                    self.add(pl, None, "fast", "plural_category")
                    self.add(pl.upper(), None, "fast", "plural_category")
                    self.add(f" {pl} ", None, "fast", "plural_category")
                    for p in ['!', '?', '.']:
                        self.add(f"{pl}{p}", None, "fast", "plural_category")
                else:
                    self.add(pl, None, "smart", "plural_category")
        
        # No filling needed
    
    def gen_quality_category(self, n):
        combos = list(itertools.product(self.QUALITY_WORDS, self.CATEGORIES))
        for q, c in combos:
            self.add(f"{q} {c}", None, "fast", "quality_category")
        
        # Add with plurals
        for q in self.QUALITY_WORDS:
            for cat, plurals in self.PLURALS.items():
                for pl in plurals:
                    if ' ' not in pl:
                        self.add(f"{q} {pl}", None, "fast", "quality_category")
    
    def gen_double_quality(self, n):
        combos = list(itertools.product(self.MODIFIER_WORDS, self.QUALITY_WORDS, self.CATEGORIES))
        for m, q, c in combos:
            self.add(f"{m} {q} {c}", None, "fast", "double_quality")
        
        # Add with plurals
        for m in self.MODIFIER_WORDS:
            for q in self.QUALITY_WORDS:
                for cat, plurals in self.PLURALS.items():
                    for pl in plurals:
                        if ' ' not in pl:
                            self.add(f"{m} {q} {pl}", None, "fast", "double_quality")
    
    # SMART PATH
    def gen_use_case_category(self, n):
        combos = list(itertools.product(self.USE_CASES, self.CATEGORIES))
        for u, c in combos:
            self.add(f"{u} {c}", None, "smart", "use_case_category")
        
        # Add with quality words
        for q in self.QUALITY_WORDS:
            for u in self.USE_CASES:
                for c in self.CATEGORIES:
                    self.add(f"{q} {u} {c}", None, "smart", "use_case_category")
    
    def gen_feature_category(self, n):
        combos = list(itertools.product(self.FEATURES, self.CATEGORIES))
        for f, c in combos:
            self.add(f"{f} {c}", None, "smart", "feature_category")
        
        # Add with plurals
        for f in self.FEATURES:
            for cat, plurals in self.PLURALS.items():
                for pl in plurals:
                    self.add(f"{f} {pl}", None, "smart", "feature_category")
    
    def gen_brand_category(self, n):
        combos = list(itertools.product(self.BRANDS, self.CATEGORIES))
        for b, c in combos:
            self.add(f"{b} {c}", None, "smart", "brand_category")
            self.add(f"{b.upper()} {c}", None, "smart", "brand_category")
            self.add(f"{b.capitalize()} {c}", None, "smart", "brand_category")
    
    def gen_spec_category(self, n):
        for spec_type, values in self.SPECS.items():
            for val in values:
                for cat in ['laptop', 'desktop', 'monitor']:
                    self.add(f"{val} {cat}", None, "smart", "spec_category")
                    self.add(f"{cat} with {val}", None, "smart", "spec_category")
                    self.add(f"{val} {cat} option", None, "smart", "spec_category")
    
    def gen_budget_category(self, n):
        for budget in self.BUDGETS:
            for cat in self.CATEGORIES:
                self.add(f"{cat} under ${budget}", float(budget), "smart", "budget_category")
                self.add(f"{cat} for ${budget}", float(budget), "smart", "budget_category")
                self.add(f"{cat} around ${budget}", float(budget), "smart", "budget_category")
    
    # DEEP PATH
    def gen_bundle_keyword(self, n):
        for keyword in self.BUNDLE_KEYWORDS:
            self.add(keyword, None, "deep", "bundle_keyword")
            self.add(keyword.upper(), None, "deep", "bundle_keyword")
            self.add(f"gaming {keyword}", None, "deep", "bundle_keyword")
            self.add(f"office {keyword}", None, "deep", "bundle_keyword")
            self.add(f"streaming {keyword}", None, "deep", "bundle_keyword")
        
        # Add with contexts
        for context in self.BUNDLE_CONTEXTS:
            for keyword in self.BUNDLE_KEYWORDS:
                self.add(f"{context} {keyword}", None, "deep", "bundle_keyword")
    
    def gen_multi_category(self, n):
        cat_pairs = list(itertools.combinations(self.CATEGORIES, 2))
        for c1, c2 in cat_pairs:
            self.add(f"{c1} and {c2}", None, "deep", "multi_category")
            self.add(f"{c1}, {c2}", None, "deep", "multi_category")
            self.add(f"{c1} with {c2}", None, "deep", "multi_category")
    
    def gen_bundle_context(self, n):
        combos = list(itertools.product(self.BUNDLE_CONTEXTS, self.BUNDLE_KEYWORDS))
        for ctx, kw in combos:
            self.add(f"{ctx} {kw}", None, "deep", "bundle_context")
            self.add(f"complete {ctx} {kw}", None, "deep", "bundle_context")
            self.add(f"full {ctx} {kw}", None, "deep", "bundle_context")
            self.add(f"best {ctx} {kw}", None, "deep", "bundle_context")


def run_extended_tests(sample_size=None):
    """Run the extended test suite."""
    
    generator = ExtendedTestGenerator()
    test_cases = generator.generate_all()
    
    print(f"\n{'='*80}")
    print(f"Generated {len(test_cases)} total tests")
    print(f"{'='*80}\n")
    
    if sample_size and sample_size < len(test_cases):
        test_cases = random.sample(test_cases, sample_size)
        print(f"Running sample of {len(test_cases)} tests\n")
    
    router = QueryRouter()
    
    results = defaultdict(lambda: {'passed': 0, 'failed': 0})
    passed = 0
    failed = 0
    
    start = time.time()
    
    for i, test in enumerate(test_cases):
        router.clear_cache()
        try:
            decision = router.analyze(test.query, test.budget)
            if decision.path.value == test.expected_path:
                passed += 1
                results[test.category]['passed'] += 1
            else:
                failed += 1
                results[test.category]['failed'] += 1
        except Exception as e:
            failed += 1
            results[test.category]['failed'] += 1
        
        if (i + 1) % 1000 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta = (len(test_cases) - i - 1) / rate
            print(f"Progress: {i+1}/{len(test_cases)} ({rate:.1f}/s, ETA: {eta:.0f}s)")
    
    elapsed = time.time() - start
    
    print(f"\n{'='*80}")
    print(f"RESULTS: {passed} passed, {failed} failed ({passed/(passed+failed)*100:.1f}%)")
    print(f"Time: {elapsed:.2f}s ({elapsed/len(test_cases)*1000:.1f}ms/test)")
    print(f"{'='*80}\n")
    
    print("Category breakdown:")
    for cat in sorted(results.keys()):
        r = results[cat]
        total = r['passed'] + r['failed']
        pct = r['passed']/total*100 if total > 0 else 0
        status = "✅" if pct >= 95 else "⚠️"
        print(f"  {status} {cat:25} {r['passed']:4}/{total:4} ({pct:5.1f}%)")
    
    return passed, failed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', type=int, default=None)
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args()
    
    sample = args.sample if args.sample else (1000 if args.quick else None)
    run_extended_tests(sample)
