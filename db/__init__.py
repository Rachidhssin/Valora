"""
Database Module for FinBundle
PostgreSQL connection pooling and product operations
"""
from db.connection import get_connection, execute_query
from db.products import (
    create_products_table,
    insert_products,
    get_product_by_id,
    get_products_by_ids
)

__all__ = [
    'get_connection',
    'execute_query',
    'create_products_table',
    'insert_products',
    'get_product_by_id',
    'get_products_by_ids'
]
