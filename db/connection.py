"""
PostgreSQL Connection Pooling
Thread-safe connection management for FinBundle
"""
import os
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

# Try PostgreSQL
try:
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
    from psycopg2.extras import RealDictCursor, execute_values
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("⚠️ psycopg2 not installed, PostgreSQL unavailable")


# Global connection pool
_pool: Optional['ThreadedConnectionPool'] = None


def _get_config() -> Dict[str, Any]:
    """Get database configuration from environment."""
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'valora'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
    }


def init_pool(min_conn: int = 2, max_conn: int = 10) -> bool:
    """
    Initialize the connection pool.
    
    Returns:
        True if pool initialized successfully
    """
    global _pool
    
    if not POSTGRES_AVAILABLE:
        return False
    
    if _pool is not None:
        return True
    
    try:
        config = _get_config()
        _pool = ThreadedConnectionPool(
            minconn=min_conn,
            maxconn=max_conn,
            **config
        )
        print(f"✅ PostgreSQL pool initialized ({config['host']}:{config['port']}/{config['database']})")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize PostgreSQL pool: {e}")
        return False


def get_connection():
    """
    Get a connection from the pool.
    
    Returns:
        Database connection or None if unavailable
    """
    global _pool
    
    if not POSTGRES_AVAILABLE:
        return None
    
    if _pool is None:
        if not init_pool():
            return None
    
    try:
        return _pool.getconn()
    except Exception as e:
        print(f"❌ Failed to get connection: {e}")
        return None


def return_connection(conn):
    """Return a connection to the pool."""
    global _pool
    if _pool is not None and conn is not None:
        _pool.putconn(conn)


@contextmanager
def get_cursor(dict_cursor: bool = True):
    """
    Context manager for database cursor.
    
    Args:
        dict_cursor: If True, returns rows as dicts
    
    Yields:
        Database cursor
    """
    conn = get_connection()
    if conn is None:
        yield None
        return
    
    cursor_factory = RealDictCursor if dict_cursor else None
    cursor = conn.cursor(cursor_factory=cursor_factory)
    
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        return_connection(conn)


def execute_query(
    query: str, 
    params: Optional[Tuple] = None,
    fetch: bool = True
) -> Optional[List[Dict]]:
    """
    Execute a query and optionally fetch results.
    
    Args:
        query: SQL query string
        params: Query parameters
        fetch: If True, fetch and return results
    
    Returns:
        List of result rows as dicts, or None
    """
    with get_cursor() as cursor:
        if cursor is None:
            return None
        
        cursor.execute(query, params)
        
        if fetch:
            return cursor.fetchall()
        return None


def execute_many(
    query: str,
    data: List[Tuple],
    page_size: int = 100
) -> int:
    """
    Execute a query with many parameter sets (batch insert).
    
    Args:
        query: SQL query with %s placeholders
        data: List of tuples with values
        page_size: Batch size for execute_values
    
    Returns:
        Number of rows affected
    """
    with get_cursor() as cursor:
        if cursor is None:
            return 0
        
        execute_values(cursor, query, data, page_size=page_size)
        return len(data)


def close_pool():
    """Close all connections in the pool."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        print("✅ PostgreSQL pool closed")


# Test connection on module load (optional)
if __name__ == "__main__":
    print("🧪 Testing PostgreSQL connection...")
    
    if init_pool():
        result = execute_query("SELECT version();")
        if result:
            print(f"📊 PostgreSQL version: {result[0]['version'][:50]}...")
        close_pool()
    else:
        print("❌ Could not connect to PostgreSQL")
