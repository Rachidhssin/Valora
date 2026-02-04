"""
Test the Hybrid Router on 1000 unseen queries.

This script generates completely new test cases that weren't in the training data
to evaluate the hybrid router's generalization performance.
"""

import sys
import random
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.hybrid_router import HybridQueryRouter, RoutePath
from core.router import QueryRouter  # Original router for ground truth


@dataclass
class TestResult:
    query: str
    budget: Optional[float]
    expected_path: str
    actual_path: str
    confidence: float
    method: str
    latency_ms: float
    passed: bool


class UnseenTestGenerator:
    """Generate completely new test cases not in training data."""
    
    # New categories/variations not heavily used in training
    NEW_BRANDS = [
        'zowie', 'ducky', 'varmilo', 'leopold', 'realforce', 'topre',
        'glorious', 'keychron', 'nuphy', 'akko', 'epomaker', 'womier',
        'gmmk', 'drop', 'kinesis', 'ergodox', 'moonlander', 'zsa',
        'secretlab', 'noblechairs', 'autonomous', 'branch', 'uplift',
        'jarvis', 'flexispot', 'vari', 'fully', 'humanscale'
    ]
    
    NEW_USE_CASES = [
        'homework', 'thesis writing', 'dissertation', 'research',
        'day trading', 'stock trading', 'crypto mining', 'nft creation',
        'vtubing', 'asmr', 'audiobook recording', 'voiceover',
        '3d modeling', 'cad work', 'architecture', 'interior design',
        'music mixing', 'djing', 'beat making', 'audio engineering',
        'live streaming', 'conference calls', 'online teaching', 'webinars'
    ]
    
    NEW_FEATURES = [
        'tri-mode', 'hot-swap', 'gasket mount', 'south-facing',
        'pbt keycaps', 'lubed switches', 'foam modded', 'tape modded',
        'qmk compatible', 'via support', 'rotary encoder',
        'oled display', 'knob', 'macro keys', 'dedicated media keys',
        'detachable cable', 'coiled cable', 'aviator connector',
        'polycarbonate', 'aluminum frame', 'steel plate'
    ]
    
    NEW_SPECS = [
        '500gb', '8tb', '16tb', '64gb ram', '128gb ram',
        '360hz', '500hz', '4000dpi', '25000dpi', '8000hz polling',
        '100w pd', '140w charging', 'thunderbolt 4', 'usb4',
        '1ms response', '0.5ms response', 'ips nano', 'qd-oled'
    ]
    
    TYPOS = [
        ('laptop', ['laptpo', 'lapto', 'laptp', 'lpatop', 'laptoop']),
        ('keyboard', ['keybaord', 'keybord', 'keyboad', 'keboard', 'keyborad']),
        ('monitor', ['monior', 'monitr', 'mointor', 'moniter', 'monittor']),
        ('mouse', ['mose', 'moue', 'mousse', 'mous', 'mosue']),
        ('headphones', ['headphons', 'headpones', 'hedphones', 'headfones', 'headhpones']),
        ('webcam', ['webacm', 'wecam', 'webcm', 'webcma', 'webccam']),
        ('microphone', ['micropone', 'microphne', 'micrphone', 'microhone', 'micorphone']),
        ('speaker', ['speakr', 'spekaer', 'speker', 'spealer', 'speeker']),
        ('tablet', ['tabelt', 'tabet', 'tablte', 'tablt', 'tableet']),
        ('charger', ['chargr', 'charger', 'chager', 'chrger', 'chargeer'])
    ]
    
    CATEGORIES = [
        'laptop', 'monitor', 'keyboard', 'mouse', 'headphones', 'headset',
        'webcam', 'speaker', 'phone', 'tablet', 'desk', 'chair', 'router',
        'charger', 'cable', 'hub', 'dock', 'microphone', 'camera', 'tv'
    ]
    
    QUALITY_WORDS = ['good', 'best', 'great', 'nice', 'cheap', 'affordable', 'premium']
    
    BUNDLE_KEYWORDS = ['setup', 'kit', 'bundle', 'combo', 'package', 'build', 'workstation']
    
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.tests: List[Tuple[str, Optional[float], str]] = []
    
    def generate_fast_tests(self, count: int = 200) -> List[Tuple[str, Optional[float], str]]:
        """Generate FAST path test cases."""
        tests = []
        
        # Simple category queries
        for _ in range(count // 4):
            cat = random.choice(self.CATEGORIES)
            tests.append((cat, None, "fast"))
            tests.append((cat.upper(), None, "fast"))
            tests.append((f"  {cat}  ", None, "fast"))
        
        # Quality + category
        for _ in range(count // 4):
            quality = random.choice(self.QUALITY_WORDS)
            cat = random.choice(self.CATEGORIES)
            tests.append((f"{quality} {cat}", None, "fast"))
        
        # Plurals
        plurals = ['laptops', 'monitors', 'keyboards', 'mice', 'speakers', 'tablets', 'chairs', 'desks']
        for _ in range(count // 4):
            plural = random.choice(plurals)
            tests.append((plural, None, "fast"))
            tests.append((f"best {plural}", None, "fast"))
        
        return tests[:count]
    
    def generate_smart_tests(self, count: int = 400) -> List[Tuple[str, Optional[float], str]]:
        """Generate SMART path test cases."""
        tests = []
        
        # New brand + category
        for _ in range(count // 5):
            brand = random.choice(self.NEW_BRANDS)
            cat = random.choice(self.CATEGORIES)
            tests.append((f"{brand} {cat}", None, "smart"))
        
        # New use case + category
        for _ in range(count // 5):
            use_case = random.choice(self.NEW_USE_CASES)
            cat = random.choice(self.CATEGORIES)
            tests.append((f"{cat} for {use_case}", None, "smart"))
        
        # New features + category
        for _ in range(count // 5):
            feature = random.choice(self.NEW_FEATURES)
            cat = random.choice(self.CATEGORIES)
            tests.append((f"{feature} {cat}", None, "smart"))
        
        # New specs + category
        for _ in range(count // 5):
            spec = random.choice(self.NEW_SPECS)
            cat = random.choice(self.CATEGORIES)
            tests.append((f"{spec} {cat}", None, "smart"))
        
        # Budget queries
        for _ in range(count // 5):
            cat = random.choice(self.CATEGORIES)
            budget = random.choice([150, 250, 350, 450, 750, 1250, 1750, 2500])
            patterns = [
                f"{cat} under ${budget}",
                f"{cat} below {budget}",
                f"${budget} {cat}",
                f"{cat} max {budget}",
                f"budget {cat} {budget}"
            ]
            tests.append((random.choice(patterns), float(budget), "smart"))
        
        return tests[:count]
    
    def generate_deep_tests(self, count: int = 300) -> List[Tuple[str, Optional[float], str]]:
        """Generate DEEP path test cases."""
        tests = []
        
        # Multi-category with connectors
        connectors = [' and ', ' with ', ' plus ', ' & ', ', ']
        for _ in range(count // 5):
            cat1, cat2 = random.sample(self.CATEGORIES, 2)
            conn = random.choice(connectors)
            tests.append((f"{cat1}{conn}{cat2}", None, "deep"))
        
        # Bundle keywords with new contexts
        contexts = ['streaming', 'podcast', 'youtube', 'twitch', 'zoom', 
                   'remote work', 'home office', 'gaming den', 'music studio']
        for _ in range(count // 5):
            context = random.choice(contexts)
            keyword = random.choice(self.BUNDLE_KEYWORDS)
            tests.append((f"{context} {keyword}", None, "deep"))
        
        # Three categories
        for _ in range(count // 5):
            cats = random.sample(self.CATEGORIES, 3)
            tests.append((f"{cats[0]} {cats[1]} {cats[2]}", None, "deep"))
        
        # Complete/full patterns
        for _ in range(count // 5):
            context = random.choice(contexts)
            patterns = [
                f"complete {context} setup",
                f"full {context} kit",
                f"entire {context} bundle",
                f"everything for {context}"
            ]
            tests.append((random.choice(patterns), None, "deep"))
        
        # Bundle with budget
        for _ in range(count // 5):
            keyword = random.choice(self.BUNDLE_KEYWORDS)
            context = random.choice(contexts)
            budget = random.choice([500, 1000, 1500, 2000, 3000, 5000])
            tests.append((f"{context} {keyword} under ${budget}", float(budget), "deep"))
        
        return tests[:count]
    
    def generate_edge_tests(self, count: int = 100) -> List[Tuple[str, Optional[float], str]]:
        """Generate edge case test cases (typos, etc.)."""
        tests = []
        
        # Typos - these should still route correctly (model helps here)
        for cat, typos in self.TYPOS:
            for typo in typos[:2]:  # Use first 2 typos per category
                # Typos of single category should go FAST or SMART
                tests.append((typo, None, "fast"))  # Most typos → FAST
        
        # Mixed case
        for _ in range(count // 4):
            cat = random.choice(self.CATEGORIES)
            mixed = ''.join(random.choice([c.upper(), c.lower()]) for c in cat)
            tests.append((mixed, None, "fast"))
        
        # Special characters
        for _ in range(count // 4):
            cat = random.choice(self.CATEGORIES)
            char = random.choice(['!', '?', '.', '...', '!!'])
            tests.append((f"{cat}{char}", None, "fast"))
        
        # Numbers in query
        for _ in range(count // 4):
            cat = random.choice(self.CATEGORIES)
            num = random.randint(1, 5)
            tests.append((f"{num}x {cat}", None, "smart"))
            tests.append((f"{num} {cat}s", None, "smart"))
        
        return tests[:count]
    
    def generate_all(self, total: int = 1000) -> List[Tuple[str, Optional[float], str]]:
        """Generate all test cases."""
        # Distribution: 20% FAST, 40% SMART, 30% DEEP, 10% EDGE
        fast_count = int(total * 0.20)
        smart_count = int(total * 0.40)
        deep_count = int(total * 0.30)
        edge_count = total - fast_count - smart_count - deep_count
        
        all_tests = []
        all_tests.extend(self.generate_fast_tests(fast_count))
        all_tests.extend(self.generate_smart_tests(smart_count))
        all_tests.extend(self.generate_deep_tests(deep_count))
        all_tests.extend(self.generate_edge_tests(edge_count))
        
        # Shuffle
        random.shuffle(all_tests)
        
        return all_tests[:total]


def run_unseen_tests(router: HybridQueryRouter, original_router: QueryRouter, 
                     tests: List[Tuple[str, Optional[float], str]]) -> List[TestResult]:
    """Run tests and compare with expected results."""
    results = []
    
    for query, budget, expected in tests:
        # Get hybrid router result
        result = router.route_detailed(query, budget)
        actual = result.path.value
        
        # Check if passed
        passed = (actual == expected)
        
        results.append(TestResult(
            query=query,
            budget=budget,
            expected_path=expected,
            actual_path=actual,
            confidence=result.confidence,
            method=result.method,
            latency_ms=result.latency_ms,
            passed=passed
        ))
    
    return results


def analyze_results(results: List[TestResult]):
    """Analyze and print test results."""
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed
    
    print("\n" + "=" * 80)
    print("UNSEEN TEST RESULTS")
    print("=" * 80)
    
    print(f"\n📊 Overall: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    # By expected path
    print("\n📈 By Expected Path:")
    for path in ['fast', 'smart', 'deep']:
        path_results = [r for r in results if r.expected_path == path]
        path_passed = sum(1 for r in path_results if r.passed)
        if path_results:
            print(f"  {path.upper()}: {path_passed}/{len(path_results)} ({path_passed/len(path_results)*100:.1f}%)")
    
    # By method used
    print("\n🔧 By Method Used:")
    rules_results = [r for r in results if r.method == 'rules']
    model_results = [r for r in results if r.method == 'model']
    
    if rules_results:
        rules_passed = sum(1 for r in rules_results if r.passed)
        print(f"  Rules: {rules_passed}/{len(rules_results)} ({rules_passed/len(rules_results)*100:.1f}%)")
    
    if model_results:
        model_passed = sum(1 for r in model_results if r.passed)
        print(f"  Model: {model_passed}/{len(model_results)} ({model_passed/len(model_results)*100:.1f}%)")
    
    # Latency stats
    print("\n⏱️ Latency:")
    latencies = [r.latency_ms for r in results]
    print(f"  Average: {sum(latencies)/len(latencies):.3f}ms")
    print(f"  Min: {min(latencies):.3f}ms")
    print(f"  Max: {max(latencies):.3f}ms")
    
    rules_latencies = [r.latency_ms for r in rules_results] if rules_results else [0]
    model_latencies = [r.latency_ms for r in model_results] if model_results else [0]
    print(f"  Rules avg: {sum(rules_latencies)/len(rules_latencies):.3f}ms")
    if model_latencies:
        print(f"  Model avg: {sum(model_latencies)/len(model_latencies):.3f}ms")
    
    # Confusion matrix
    print("\n📊 Confusion Matrix:")
    confusion = defaultdict(lambda: defaultdict(int))
    for r in results:
        confusion[r.expected_path][r.actual_path] += 1
    
    print(f"{'Expected':<10} | {'→ FAST':<10} {'→ SMART':<10} {'→ DEEP':<10}")
    print("-" * 45)
    for expected in ['fast', 'smart', 'deep']:
        row = confusion[expected]
        print(f"{expected.upper():<10} | {row['fast']:<10} {row['smart']:<10} {row['deep']:<10}")
    
    # Show some failures
    failures = [r for r in results if not r.passed]
    if failures:
        print(f"\n❌ Sample Failures ({min(15, len(failures))} of {len(failures)}):")
        for r in failures[:15]:
            query_short = r.query[:40] + "..." if len(r.query) > 40 else r.query
            print(f"  '{query_short}' → expected {r.expected_path}, got {r.actual_path} ({r.method}, {r.confidence:.2f})")
    
    return passed, total


def main():
    print("=" * 80)
    print("HYBRID ROUTER - UNSEEN TEST EVALUATION")
    print("=" * 80)
    
    # Load hybrid router with model
    print("\n🔄 Loading hybrid router with LSTM model...")
    start = time.time()
    router = HybridQueryRouter(model_path='models/router_lstm')
    
    # Warm up
    _ = router.route_detailed("warm up query", None)
    print(f"✓ Router loaded in {time.time() - start:.2f}s")
    
    # Load original router for comparison (optional)
    original_router = QueryRouter()
    
    # Generate unseen tests
    print("\n🧪 Generating 1000 unseen test cases...")
    generator = UnseenTestGenerator(seed=12345)  # Different seed than training
    tests = generator.generate_all(1000)
    
    # Count by expected path
    fast_count = sum(1 for t in tests if t[2] == 'fast')
    smart_count = sum(1 for t in tests if t[2] == 'smart')
    deep_count = sum(1 for t in tests if t[2] == 'deep')
    print(f"✓ Generated: {fast_count} FAST, {smart_count} SMART, {deep_count} DEEP")
    
    # Run tests
    print("\n🚀 Running tests...")
    start = time.time()
    results = run_unseen_tests(router, original_router, tests)
    elapsed = time.time() - start
    print(f"✓ Completed in {elapsed:.2f}s ({len(tests)/elapsed:.0f} queries/sec)")
    
    # Analyze results
    passed, total = analyze_results(results)
    
    # Final summary
    print("\n" + "=" * 80)
    if passed / total >= 0.90:
        print(f"✅ EXCELLENT: {passed/total*100:.1f}% accuracy on unseen data!")
    elif passed / total >= 0.80:
        print(f"✓ GOOD: {passed/total*100:.1f}% accuracy on unseen data")
    else:
        print(f"⚠️ NEEDS IMPROVEMENT: {passed/total*100:.1f}% accuracy on unseen data")
    print("=" * 80)


if __name__ == "__main__":
    main()
