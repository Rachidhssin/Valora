"""
Metrics Logging System
JSONL-based metrics logging with analysis
"""
import json
import time
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager


class MetricsLogger:
    """
    Log system metrics to JSONL file for analysis.
    Thread-safe and designed for production use.
    """
    
    def __init__(self, log_dir: str = "data"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.log_file = self.log_dir / "metrics.jsonl"
        self._file = None
    
    def _ensure_file(self):
        """Ensure log file is open."""
        if self._file is None or self._file.closed:
            self._file = open(self.log_file, "a", encoding="utf-8")
    
    def log(self, event_type: str, data: Dict[str, Any]):
        """
        Log an event with timestamp.
        
        Args:
            event_type: Type of event (search, cache_hit, agent_call, etc.)
            data: Event data dictionary
        """
        self._ensure_file()
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            **data
        }
        
        self._file.write(json.dumps(log_entry) + "\n")
        self._file.flush()
    
    def log_search(self, query: str, user_id: str, path: str,
                   latency_ms: float, cache_hit: bool = False,
                   result_count: int = 0, **extra):
        """Log a search event."""
        self.log("search", {
            "query": query,
            "user_id": user_id,
            "path": path,
            "latency_ms": latency_ms,
            "cache_hit": cache_hit,
            "result_count": result_count,
            **extra
        })
    
    def log_cache_event(self, key: str, hit: bool, ttl: int = 0):
        """Log a cache hit/miss event."""
        self.log("cache", {
            "key": key[:50],  # Truncate long keys
            "hit": hit,
            "ttl": ttl
        })
    
    def log_agent_call(self, user_id: str, gap: float, 
                       paths_found: int, latency_ms: float):
        """Log an agent invocation."""
        self.log("agent", {
            "user_id": user_id,
            "gap": gap,
            "paths_found": paths_found,
            "latency_ms": latency_ms
        })
    
    def log_optimization(self, items_in: int, items_out: int,
                        budget: float, total_price: float,
                        method: str, latency_ms: float):
        """Log an optimization event."""
        self.log("optimization", {
            "items_in": items_in,
            "items_out": items_out,
            "budget": budget,
            "total_price": total_price,
            "budget_used": total_price / budget if budget > 0 else 0,
            "method": method,
            "latency_ms": latency_ms
        })
    
    def log_error(self, component: str, error: str, context: Dict = None):
        """Log an error event."""
        self.log("error", {
            "component": component,
            "error": str(error),
            "context": context or {}
        })
    
    @contextmanager
    def measure(self, event_type: str, **static_data):
        """Context manager to measure and log execution time."""
        start = time.time()
        result = {"success": True}
        
        try:
            yield result
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            raise
        finally:
            latency_ms = (time.time() - start) * 1000
            self.log(event_type, {
                **static_data,
                "latency_ms": latency_ms,
                **result
            })
    
    def analyze(self, last_n_hours: int = 24) -> Dict[str, Any]:
        """
        Analyze logged metrics.
        
        Args:
            last_n_hours: Only analyze logs from last N hours
            
        Returns:
            Analysis summary dict
        """
        if not self.log_file.exists():
            return {"error": "No log file found"}
        
        try:
            import pandas as pd
        except ImportError:
            return self._analyze_simple()
        
        # Read logs
        logs = []
        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    logs.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        
        if not logs:
            return {"error": "No logs found"}
        
        df = pd.DataFrame(logs)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Filter by time
        cutoff = datetime.now() - pd.Timedelta(hours=last_n_hours)
        df = df[df['timestamp'] >= cutoff]
        
        if df.empty:
            return {"message": f"No logs in last {last_n_hours} hours"}
        
        # Aggregate stats
        stats = {
            "total_events": len(df),
            "time_range": {
                "start": df['timestamp'].min().isoformat(),
                "end": df['timestamp'].max().isoformat()
            }
        }
        
        # Search stats
        searches = df[df['type'] == 'search']
        if not searches.empty:
            stats["search"] = {
                "total": len(searches),
                "avg_latency_ms": round(searches['latency_ms'].mean(), 2),
                "p95_latency_ms": round(searches['latency_ms'].quantile(0.95), 2),
                "cache_hit_rate": round(searches['cache_hit'].mean() * 100, 1),
                "path_distribution": searches['path'].value_counts().to_dict()
            }
        
        # Agent stats
        agents = df[df['type'] == 'agent']
        if not agents.empty:
            stats["agent"] = {
                "total": len(agents),
                "avg_latency_ms": round(agents['latency_ms'].mean(), 2),
                "avg_paths_found": round(agents['paths_found'].mean(), 2)
            }
        
        # Error stats
        errors = df[df['type'] == 'error']
        if not errors.empty:
            stats["errors"] = {
                "total": len(errors),
                "by_component": errors['component'].value_counts().to_dict()
            }
        
        return stats
    
    def _analyze_simple(self) -> Dict[str, Any]:
        """Simple analysis without pandas."""
        if not self.log_file.exists():
            return {"error": "No log file found"}
        
        counts = {}
        latencies = []
        cache_hits = 0
        cache_total = 0
        
        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    log = json.loads(line.strip())
                    event_type = log.get('type', 'unknown')
                    counts[event_type] = counts.get(event_type, 0) + 1
                    
                    if 'latency_ms' in log:
                        latencies.append(log['latency_ms'])
                    
                    if event_type == 'search':
                        cache_total += 1
                        if log.get('cache_hit'):
                            cache_hits += 1
                            
                except json.JSONDecodeError:
                    continue
        
        return {
            "event_counts": counts,
            "total_events": sum(counts.values()),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "cache_hit_rate": round(cache_hits / cache_total * 100, 1) if cache_total > 0 else 0
        }
    
    def print_summary(self):
        """Print a formatted summary."""
        stats = self.analyze()
        
        print("\n" + "=" * 50)
        print("📊 FINBUNDLE METRICS SUMMARY")
        print("=" * 50)
        
        if "error" in stats:
            print(f"⚠️ {stats['error']}")
            return
        
        print(f"\nTotal events: {stats.get('total_events', 0)}")
        
        if "time_range" in stats:
            print(f"Time range: {stats['time_range']['start'][:19]} to {stats['time_range']['end'][:19]}")
        
        if "search" in stats:
            s = stats["search"]
            print(f"\n🔍 Searches:")
            print(f"   Total: {s['total']}")
            print(f"   Avg latency: {s['avg_latency_ms']}ms")
            print(f"   P95 latency: {s.get('p95_latency_ms', 'N/A')}ms")
            print(f"   Cache hit rate: {s['cache_hit_rate']}%")
            if 'path_distribution' in s:
                print(f"   Paths: {s['path_distribution']}")
        
        if "agent" in stats:
            a = stats["agent"]
            print(f"\n🤖 Agent calls:")
            print(f"   Total: {a['total']}")
            print(f"   Avg latency: {a['avg_latency_ms']}ms")
        
        if "errors" in stats:
            e = stats["errors"]
            print(f"\n❌ Errors: {e['total']}")
        
        print("\n" + "=" * 50)
    
    def close(self):
        """Close the log file."""
        if self._file and not self._file.closed:
            self._file.close()


# Singleton instance
_metrics_logger = None


def get_metrics_logger() -> MetricsLogger:
    """Get or create singleton metrics logger."""
    global _metrics_logger
    if _metrics_logger is None:
        _metrics_logger = MetricsLogger()
    return _metrics_logger


if __name__ == "__main__":
    # Demo usage
    logger = MetricsLogger()
    
    # Simulate some events
    logger.log_search("gaming laptop", "user_001", "smart", 245.5, cache_hit=False, result_count=15)
    logger.log_search("keyboard", "user_002", "fast", 35.2, cache_hit=True, result_count=5)
    logger.log_agent_call("user_001", 500.0, 3, 890.5)
    logger.log_optimization(25, 5, 1500, 1234.56, "milp", 120.3)
    
    # Print summary
    logger.print_summary()
    
    logger.close()
