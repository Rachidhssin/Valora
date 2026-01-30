"""
PostgreSQL Cache
TTL-based caching with PostgreSQL backend
"""
import json
import time
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Any, Dict
from dotenv import load_dotenv

load_dotenv()


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles Decimal, datetime, and numpy types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        # Handle numpy types
        try:
            import numpy as np
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.float32, np.float64)):
                return float(obj)
            if isinstance(obj, (np.int32, np.int64)):
                return int(obj)
        except ImportError:
            pass
        return super().default(obj)


# Try PostgreSQL, fall back to in-memory
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class PostgreSQLCache:
    """
    PostgreSQL-backed cache with TTL support.
    Falls back to in-memory cache if PostgreSQL unavailable.
    """
    
    def __init__(self, table_name: str = "cache"):
        self.table_name = table_name
        self._conn = None
        self._memory_cache: Dict[str, Dict] = {}  # Fallback
        
        self._init_storage()
    
    def _init_storage(self):
        """Initialize PostgreSQL storage."""
        if not POSTGRES_AVAILABLE:
            print("⚠️ psycopg2 not installed, using in-memory cache")
            return
        
        try:
            self._conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "finbundle"),
                user=os.getenv("POSTGRES_USER", "user"),
                password=os.getenv("POSTGRES_PASSWORD", "password"),
                connect_timeout=1
            )
            
            with self._conn.cursor() as cur:
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        key VARCHAR(512) PRIMARY KEY,
                        value JSONB NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Create index for expiry cleanup
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_expires 
                    ON {self.table_name} (expires_at)
                """)
                self._conn.commit()
                
        except Exception as e:
            print(f"⚠️ PostgreSQL cache init failed: {e}")
            self._conn = None
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Returns:
            Cached value or None if not found/expired
        """
        if self._conn:
            return self._get_postgres(key)
        else:
            return self._get_memory(key)
    
    def _get_postgres(self, key: str) -> Optional[Any]:
        """Get from PostgreSQL."""
        try:
            with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"""
                    SELECT value FROM {self.table_name}
                    WHERE key = %s AND expires_at > NOW()
                """, (key,))
                row = cur.fetchone()
                return row['value'] if row else None
        except Exception as e:
            print(f"⚠️ Cache get error: {e}")
            return None
    
    def _get_memory(self, key: str) -> Optional[Any]:
        """Get from in-memory cache."""
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if entry['expires_at'] > time.time():
                return entry['value']
            else:
                del self._memory_cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default 1 hour)
            
        Returns:
            True if successful
        """
        if self._conn:
            return self._set_postgres(key, value, ttl)
        else:
            return self._set_memory(key, value, ttl)
    
    def _set_postgres(self, key: str, value: Any, ttl: int) -> bool:
        """Set in PostgreSQL."""
        try:
            expires_at = datetime.now() + timedelta(seconds=ttl)
            
            with self._conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {self.table_name} (key, value, expires_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (key) DO UPDATE SET
                        value = EXCLUDED.value,
                        expires_at = EXCLUDED.expires_at
                """, (key, json.dumps(value, cls=DecimalEncoder), expires_at))
                self._conn.commit()
            return True
        except Exception as e:
            print(f"⚠️ Cache set error: {e}")
            return False
    
    def _set_memory(self, key: str, value: Any, ttl: int) -> bool:
        """Set in in-memory cache."""
        self._memory_cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }
        return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if self._conn:
            try:
                with self._conn.cursor() as cur:
                    cur.execute(f"DELETE FROM {self.table_name} WHERE key = %s", (key,))
                    self._conn.commit()
                return True
            except Exception as e:
                print(f"⚠️ Cache delete error: {e}")
                return False
        else:
            if key in self._memory_cache:
                del self._memory_cache[key]
            return True
    
    def clear_expired(self) -> int:
        """
        Clear expired entries.
        
        Returns:
            Number of entries deleted
        """
        if self._conn:
            try:
                with self._conn.cursor() as cur:
                    cur.execute(f"""
                        DELETE FROM {self.table_name}
                        WHERE expires_at < NOW()
                    """)
                    count = cur.rowcount
                    self._conn.commit()
                return count
            except Exception as e:
                print(f"⚠️ Cache cleanup error: {e}")
                return 0
        else:
            now = time.time()
            expired = [k for k, v in self._memory_cache.items() if v['expires_at'] < now]
            for k in expired:
                del self._memory_cache[k]
            return len(expired)
    
    def clear_all(self) -> bool:
        """Clear all cache entries."""
        if self._conn:
            try:
                with self._conn.cursor() as cur:
                    cur.execute(f"TRUNCATE TABLE {self.table_name}")
                    self._conn.commit()
                return True
            except Exception as e:
                print(f"⚠️ Cache clear error: {e}")
                return False
        else:
            self._memory_cache.clear()
            return True
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        if self._conn:
            try:
                with self._conn.cursor() as cur:
                    cur.execute(f"""
                        SELECT
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE expires_at > NOW()) as valid,
                            COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired
                        FROM {self.table_name}
                    """)
                    row = cur.fetchone()
                    return {
                        'total': row[0],
                        'valid': row[1],
                        'expired': row[2]
                    }
            except Exception as e:
                return {'error': str(e)}
        else:
            now = time.time()
            valid = sum(1 for v in self._memory_cache.values() if v['expires_at'] > now)
            return {
                'total': len(self._memory_cache),
                'valid': valid,
                'expired': len(self._memory_cache) - valid
            }
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()


# Convenience class alias
Cache = PostgreSQLCache


if __name__ == "__main__":
    print("🧪 Testing PostgreSQL Cache...")
    
    cache = PostgreSQLCache(table_name="test_cache")
    
    # Test set/get
    test_data = {"products": [1, 2, 3], "query": "gaming laptop"}
    cache.set("test_key", test_data, ttl=60)
    
    retrieved = cache.get("test_key")
    print(f"\n📊 Set/Get test:")
    print(f"   Original: {test_data}")
    print(f"   Retrieved: {retrieved}")
    print(f"   Match: {test_data == retrieved}")
    
    # Test stats
    stats = cache.stats()
    print(f"\n📊 Cache stats: {stats}")
    
    # Test non-existent key
    missing = cache.get("non_existent_key")
    print(f"\n📊 Missing key returns: {missing}")
    
    # Cleanup
    cache.delete("test_key")
    
    print("\n✅ Cache test complete!")
