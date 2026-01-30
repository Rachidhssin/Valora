"""Test the taxonomy disambiguation system."""
import sys
sys.path.insert(0, '.')

from core.taxonomy import disambiguate_search, CategoryTaxonomy

# Test cases for disambiguation
test_queries = [
    'screen',
    'laptop screen',
    'gaming keyboard',
    'musical keyboard',
    'keyboard',
    'monitor',
    'baby monitor',
    'wireless mouse',
    'gaming mouse',
]

print('=' * 60)
print('TAXONOMY DISAMBIGUATION TEST')
print('=' * 60)

for query in test_queries:
    result = disambiguate_search(query)
    print(f"\nQuery: '{query}'")
    print(f"  Primary: {result['primary_category']}")
    print(f"  Boost: {result['boost_categories']}")
    print(f"  Exclude: {result['exclude_categories']}")
    print(f"  Ambiguous: {result['is_ambiguous']}")
    print(f"  Terms: {result['detected_terms']}")

print()
print('=' * 60)
print('All disambiguation tests completed!')
