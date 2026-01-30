#!/usr/bin/env python3
"""
Post-Ingestion Search Quality Test Suite
-----------------------------------------
Run after 500K product ingestion to verify search quality improvements.

Tests:
1. Category Coverage - Do we have products in each major category?
2. Ambiguous Query Resolution - Do disambiguation rules work?
3. Match Quality - Are Qdrant scores in expected range (0.4-0.7)?
4. Budget Filtering - Does price filtering work correctly?
5. End-to-End Latency - Is search < 300ms target?

Usage:
    python scripts/test_search_quality.py
    python scripts/test_search_quality.py --verbose
    python scripts/test_search_quality.py --category-only
"""

import asyncio
import argparse
import time
import sys
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.search_engine import FinBundleEngine as SearchEngine
from retrieval.qdrant_search import QdrantSearch


@dataclass
class TestResult:
    """Single test result"""
    name: str
    passed: bool
    message: str
    latency_ms: float = 0
    details: Optional[Dict] = None


class SearchQualityTester:
    """Test search quality after ingestion"""
    
    # Expected categories with minimum product count
    EXPECTED_CATEGORIES = {
        'monitors': 500,
        'keyboards': 300,
        'mice': 200,
        'headphones': 300,
        'speakers': 200,
        'laptops': 200,
        'tablets': 100,
        'cameras': 200,
        'tvs': 200,
        'smart home': 150,
        'networking': 150,
        'storage': 200,
        'cables': 300,
        'audio': 300,
        'gaming': 200,
    }
    
    # Test queries with expected categories
    AMBIGUOUS_QUERIES = [
        {
            'query': 'gaming keyboard',
            'expected_category_keywords': ['keyboard', 'gaming'],
            'excluded_keywords': ['piano', 'synthesizer', 'midi', 'music'],
        },
        {
            'query': '4K monitor',
            'expected_category_keywords': ['monitor', 'display', 'screen'],
            'excluded_keywords': ['baby', 'security', 'heart rate'],
        },
        {
            'query': 'wireless mouse',
            'expected_category_keywords': ['mouse', 'mice'],
            'excluded_keywords': ['trap', 'repellent', 'pest', 'toy'],
        },
        {
            'query': 'computer screen',
            'expected_category_keywords': ['monitor', 'screen', 'display'],
            'excluded_keywords': ['protector', 'film', 'privacy'],
        },
        {
            'query': 'Bluetooth speaker',
            'expected_category_keywords': ['speaker', 'audio'],
            'excluded_keywords': ['mount', 'stand', 'cover'],
        },
    ]
    
    # Budget test cases
    BUDGET_TESTS = [
        {'query': 'laptop', 'budget': 500, 'min_results': 5},
        {'query': 'headphones', 'budget': 100, 'min_results': 10},
        {'query': '4K TV', 'budget': 1000, 'min_results': 5},
        {'query': 'webcam', 'budget': 200, 'min_results': 10},
    ]
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.search_engine = None
        self.qdrant = None
    
    async def setup(self):
        """Initialize search engine and Qdrant"""
        print("🔧 Setting up test environment...")
        self.search_engine = SearchEngine()
        self.qdrant = QdrantSearch()
        
        # Check Qdrant collection stats
        try:
            info = self.qdrant._client.get_collection('products_main')
            point_count = info.points_count
            print(f"📊 Qdrant collection has {point_count:,} products")
            if point_count < 100000:
                print(f"⚠️  Warning: Only {point_count:,} products. Expected 500K for best results.")
            return point_count
        except Exception as e:
            print(f"❌ Failed to connect to Qdrant: {e}")
            return 0
    
    async def test_category_coverage(self) -> List[TestResult]:
        """Test that we have products in major categories"""
        print("\n📁 Testing Category Coverage...")
        results = []
        
        for category, expected_min in self.EXPECTED_CATEGORIES.items():
            start = time.time()
            try:
                # Search for category
                search_results = await self.search_engine.search(
                    query=category,
                    user_id="test_user",
                    budget=10000
                )
                
                count = search_results.get('count', 0)
                latency = (time.time() - start) * 1000
                
                # Check if we got enough results
                passed = count >= min(expected_min, 30)  # Cap at 30 since that's our limit
                
                result = TestResult(
                    name=f"Category: {category}",
                    passed=passed,
                    message=f"Found {count} results (expected ≥{min(expected_min, 30)})",
                    latency_ms=latency,
                    details={'count': count, 'expected': expected_min}
                )
                results.append(result)
                
                if self.verbose:
                    status = "✅" if passed else "❌"
                    print(f"  {status} {category}: {count} results ({latency:.0f}ms)")
                    
            except Exception as e:
                results.append(TestResult(
                    name=f"Category: {category}",
                    passed=False,
                    message=f"Error: {e}"
                ))
        
        return results
    
    async def test_disambiguation(self) -> List[TestResult]:
        """Test that ambiguous queries return correct products"""
        print("\n🎯 Testing Query Disambiguation...")
        results = []
        
        for test_case in self.AMBIGUOUS_QUERIES:
            query = test_case['query']
            expected_keywords = test_case['expected_category_keywords']
            excluded_keywords = test_case['excluded_keywords']
            
            start = time.time()
            try:
                search_results = await self.search_engine.search(
                    query=query,
                    user_id="test_user",
                    budget=10000
                )
                
                products = search_results.get('results', [])
                latency = (time.time() - start) * 1000
                
                # Check if results contain expected keywords
                relevant_count = 0
                irrelevant_products = []
                
                for p in products[:10]:  # Check top 10
                    name_lower = p.get('name', '').lower()
                    category_lower = p.get('category', '').lower()
                    text = f"{name_lower} {category_lower}"
                    
                    # Check for expected keywords
                    has_expected = any(kw in text for kw in expected_keywords)
                    
                    # Check for excluded keywords
                    has_excluded = any(kw in text for kw in excluded_keywords)
                    
                    if has_expected and not has_excluded:
                        relevant_count += 1
                    elif has_excluded:
                        irrelevant_products.append(p.get('name', '')[:50])
                
                # Pass if at least 70% of top 10 are relevant
                relevance_ratio = relevant_count / min(10, len(products)) if products else 0
                passed = relevance_ratio >= 0.7
                
                result = TestResult(
                    name=f"Disambiguation: '{query}'",
                    passed=passed,
                    message=f"{relevant_count}/10 relevant ({relevance_ratio*100:.0f}%)",
                    latency_ms=latency,
                    details={
                        'relevant_count': relevant_count,
                        'irrelevant_examples': irrelevant_products[:3],
                        'disambiguation_applied': search_results.get('disambiguation', {}).get('applied', False)
                    }
                )
                results.append(result)
                
                if self.verbose:
                    status = "✅" if passed else "❌"
                    print(f"  {status} '{query}': {relevant_count}/10 relevant ({latency:.0f}ms)")
                    if irrelevant_products and not passed:
                        print(f"      ⚠️ Irrelevant: {irrelevant_products[:2]}")
                        
            except Exception as e:
                results.append(TestResult(
                    name=f"Disambiguation: '{query}'",
                    passed=False,
                    message=f"Error: {e}"
                ))
        
        return results
    
    async def test_match_quality(self) -> List[TestResult]:
        """Test that match scores are in expected range"""
        print("\n📈 Testing Match Quality...")
        results = []
        
        test_queries = [
            'gaming monitor 144hz',
            'wireless earbuds noise cancelling',
            'mechanical keyboard rgb',
            'usb-c hub dock',
            '4k webcam streaming',
        ]
        
        for query in test_queries:
            start = time.time()
            try:
                search_results = await self.search_engine.search(
                    query=query,
                    user_id="test_user",
                    budget=10000
                )
                
                products = search_results.get('results', [])
                latency = (time.time() - start) * 1000
                
                if not products:
                    results.append(TestResult(
                        name=f"Match Quality: '{query}'",
                        passed=False,
                        message="No results returned"
                    ))
                    continue
                
                # Analyze score distribution
                scores = [p.get('score', 0) for p in products[:10]]
                avg_score = sum(scores) / len(scores) if scores else 0
                top_score = scores[0] if scores else 0
                
                # With 500K products, top scores should be > 0.7
                passed = top_score >= 0.65 and avg_score >= 0.50
                
                # Count primary vs related matches
                primary_count = sum(1 for p in products if p.get('match_tier') == 'primary')
                
                result = TestResult(
                    name=f"Match Quality: '{query[:30]}'",
                    passed=passed,
                    message=f"Top: {top_score:.1%}, Avg: {avg_score:.1%}, Primary: {primary_count}",
                    latency_ms=latency,
                    details={
                        'top_score': top_score,
                        'avg_score': avg_score,
                        'primary_matches': primary_count,
                        'total_results': len(products)
                    }
                )
                results.append(result)
                
                if self.verbose:
                    status = "✅" if passed else "❌"
                    print(f"  {status} '{query[:30]}': Top {top_score:.1%}, Avg {avg_score:.1%} ({latency:.0f}ms)")
                    
            except Exception as e:
                results.append(TestResult(
                    name=f"Match Quality: '{query[:30]}'",
                    passed=False,
                    message=f"Error: {e}"
                ))
        
        return results
    
    async def test_budget_filtering(self) -> List[TestResult]:
        """Test that budget filtering works correctly"""
        print("\n💰 Testing Budget Filtering...")
        results = []
        
        for test_case in self.BUDGET_TESTS:
            query = test_case['query']
            budget = test_case['budget']
            min_results = test_case['min_results']
            
            start = time.time()
            try:
                search_results = await self.search_engine.search(
                    query=query,
                    user_id="test_user",
                    budget=budget
                )
                
                products = search_results.get('results', [])
                latency = (time.time() - start) * 1000
                
                # Check that results are within budget (with 20% tolerance)
                max_allowed = budget * 1.2
                within_budget = [p for p in products if p.get('price', 0) <= max_allowed]
                over_budget = [p for p in products if p.get('price', 0) > max_allowed]
                
                passed = len(within_budget) >= min_results and len(over_budget) == 0
                
                result = TestResult(
                    name=f"Budget: '{query}' ≤${budget}",
                    passed=passed,
                    message=f"{len(within_budget)} within budget, {len(over_budget)} over",
                    latency_ms=latency,
                    details={
                        'within_budget_count': len(within_budget),
                        'over_budget_count': len(over_budget),
                        'min_expected': min_results
                    }
                )
                results.append(result)
                
                if self.verbose:
                    status = "✅" if passed else "❌"
                    print(f"  {status} '{query}' ≤${budget}: {len(within_budget)} results ({latency:.0f}ms)")
                    if over_budget:
                        prices = [p.get('price', 0) for p in over_budget[:3]]
                        print(f"      ⚠️ Over budget: ${prices}")
                        
            except Exception as e:
                results.append(TestResult(
                    name=f"Budget: '{query}' ≤${budget}",
                    passed=False,
                    message=f"Error: {e}"
                ))
        
        return results
    
    async def test_latency(self) -> List[TestResult]:
        """Test that search latency is within target"""
        print("\n⏱️ Testing Search Latency...")
        results = []
        
        test_queries = [
            'laptop',
            'wireless earbuds',
            'gaming keyboard mechanical rgb',
            '4k monitor for office work',
        ]
        
        latencies = []
        
        for query in test_queries:
            start = time.time()
            try:
                await self.search_engine.search(query=query, user_id="test_user", budget=1000)
                latency = (time.time() - start) * 1000
                latencies.append(latency)
                
                # Target: < 300ms
                passed = latency < 300
                
                result = TestResult(
                    name=f"Latency: '{query[:25]}'",
                    passed=passed,
                    message=f"{latency:.0f}ms (target <300ms)",
                    latency_ms=latency
                )
                results.append(result)
                
                if self.verbose:
                    status = "✅" if passed else "❌"
                    print(f"  {status} '{query[:25]}': {latency:.0f}ms")
                    
            except Exception as e:
                results.append(TestResult(
                    name=f"Latency: '{query[:25]}'",
                    passed=False,
                    message=f"Error: {e}"
                ))
        
        # Add summary
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 5 else max(latencies)
            
            results.append(TestResult(
                name="Latency Summary",
                passed=avg_latency < 300,
                message=f"Avg: {avg_latency:.0f}ms, Max: {max(latencies):.0f}ms",
                latency_ms=avg_latency,
                details={'avg': avg_latency, 'max': max(latencies), 'min': min(latencies)}
            ))
        
        return results
    
    async def run_all_tests(self, category_only: bool = False) -> Dict:
        """Run all quality tests"""
        point_count = await self.setup()
        
        if point_count == 0:
            return {'error': 'Failed to connect to Qdrant', 'passed': 0, 'failed': 1}
        
        all_results = []
        
        # Always run category tests
        all_results.extend(await self.test_category_coverage())
        
        if not category_only:
            all_results.extend(await self.test_disambiguation())
            all_results.extend(await self.test_match_quality())
            all_results.extend(await self.test_budget_filtering())
            all_results.extend(await self.test_latency())
        
        # Summary
        passed = sum(1 for r in all_results if r.passed)
        failed = sum(1 for r in all_results if not r.passed)
        total = len(all_results)
        
        print("\n" + "="*60)
        print(f"📊 SEARCH QUALITY TEST RESULTS")
        print("="*60)
        print(f"  ✅ Passed: {passed}/{total}")
        print(f"  ❌ Failed: {failed}/{total}")
        print(f"  📦 Products: {point_count:,}")
        
        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for r in all_results:
                if not r.passed:
                    print(f"  - {r.name}: {r.message}")
        
        # Calculate overall score
        score = (passed / total) * 100 if total > 0 else 0
        print(f"\n🎯 Quality Score: {score:.1f}%")
        
        if score >= 90:
            print("✨ Excellent! Search quality is production-ready.")
        elif score >= 75:
            print("👍 Good. Minor improvements possible.")
        elif score >= 50:
            print("⚠️ Fair. Review failed tests for improvements.")
        else:
            print("🔧 Needs Work. Consider re-ingesting more products.")
        
        return {
            'passed': passed,
            'failed': failed,
            'total': total,
            'score': score,
            'product_count': point_count,
            'results': [
                {
                    'name': r.name,
                    'passed': r.passed,
                    'message': r.message,
                    'latency_ms': r.latency_ms
                }
                for r in all_results
            ]
        }


async def main():
    parser = argparse.ArgumentParser(description='Test search quality after ingestion')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--category-only', action='store_true', help='Only test category coverage')
    args = parser.parse_args()
    
    tester = SearchQualityTester(verbose=args.verbose)
    results = await tester.run_all_tests(category_only=args.category_only)
    
    # Exit with error code if too many failures
    if results.get('score', 0) < 50:
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
