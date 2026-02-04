"""Test script for the hybrid router with trained model."""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.hybrid_router import HybridQueryRouter

def main():
    # Test with model - eagerly load it
    print("Loading hybrid router with LSTM model...")
    start = time.time()
    router = HybridQueryRouter(model_path='models/router_lstm')
    
    # Eagerly load model with a warm-up query
    print("Warming up model...")
    _ = router.route_detailed("test query", None)
    print(f"Model loaded in {time.time() - start:.2f}s")
    
    # Reset stats after warm-up
    router.stats = {"total_queries": 0, "rules_used": 0, "model_used": 0, "avg_latency_ms": 0}
    
    test_queries = [
        # FAST
        ('laptop', None),
        ('best keyboard', None),
        ('cheap mouse', None),
        
        # SMART  
        ('gaming laptop under 1000', 1000),
        ('wireless mechanical keyboard rgb', None),
        ('4k monitor for video editing', None),
        ('razer mouse for gaming', None),
        ('16gb ram laptop', None),
        ('best ssd for pc', None),
        
        # DEEP
        ('laptop and mouse', None),
        ('complete gaming setup', None),
        ('home office kit with desk and chair', None),
        ('streaming bundle under 2000', 2000),
        ('laptop monitor keyboard combo', None),
        
        # Edge cases (will use model)
        ('lpptop', None),  # typo
        ('kybord', None),  # typo
        ('mnitor 4k', None),  # typo
        ('rgb mechanical wireless 60% keyboard', None),
        ('i need a good laptop for school', None),
    ]
    
    print()
    print(f"{'Query':<50} {'Path':<8} {'Conf':<6} {'Method':<8} {'Latency'}")
    print('-' * 85)
    
    for query, budget in test_queries:
        result = router.route_detailed(query, budget)
        print(f'{query:<50} {result.path.value:<8} {result.confidence:.2f}   {result.method:<8} {result.latency_ms:.2f}ms')
    
    print()
    print('=' * 85)
    stats = router.get_stats()
    print(f"Total queries: {stats['total_queries']}")
    print(f"Rules used: {stats['rules_used']} ({stats.get('rules_percentage', 0):.1f}%)")
    print(f"Model used: {stats['model_used']} ({stats.get('model_percentage', 0):.1f}%)")
    print(f"Avg latency: {stats['avg_latency_ms']:.3f}ms")


if __name__ == "__main__":
    main()
