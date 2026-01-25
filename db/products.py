"""
Product Database Operations
PostgreSQL CRUD for Amazon products
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from db.connection import get_cursor, execute_query, execute_many


@dataclass
class Product:
    """Product model mapping Amazon JSONL to FinBundle schema."""
    product_id: str          # parent_asin
    title: str               # title (maps to name)
    main_category: str       # main_category (maps to category)
    brand: str               # store or details.Brand
    price: float             # price
    rating: float            # average_rating
    rating_count: int        # rating_number (maps to review_count)
    description: str         # description[0]
    features: List[str] = field(default_factory=list)
    image_url: str = ""      # images[0].large
    details: Dict = field(default_factory=dict)  # details (JSONB)
    in_stock: bool = True    # default True
    condition: str = "new"   # default 'new'
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.product_id,
            'product_id': self.product_id,
            'name': self.title,
            'category': self.main_category,
            'brand': self.brand,
            'price': self.price,
            'rating': self.rating,
            'review_count': self.rating_count,
            'description': self.description,
            'features': self.features,
            'image_url': self.image_url,
            'in_stock': self.in_stock,
            'condition': self.condition,
            'specs': self.details
        }
    
    @classmethod
    def from_amazon_json(cls, data: Dict) -> Optional['Product']:
        """
        Create Product from Amazon JSONL record.
        
        Returns None if product is invalid (e.g., no price).
        """
        # Skip products without price
        price = data.get('price')
        if price is None:
            return None
        
        # Skip products without category
        main_category = data.get('main_category')
        if main_category is None:
            return None
        # Truncate long category names
        if len(main_category) > 100:
            main_category = main_category[:100]
        
        # Extract brand from store or details
        brand = data.get('store', '')
        if not brand:
            details = data.get('details', {})
            brand = details.get('Brand', details.get('Manufacturer', 'Unknown'))
        # Truncate long brand names
        if len(brand) > 100:
            brand = brand[:100]
        
        # Extract first image
        images = data.get('images', [])
        image_url = images[0].get('large', '') if images else ''
        
        # Extract first description
        descriptions = data.get('description', [])
        description = descriptions[0] if descriptions else ''
        # Truncate very long descriptions
        if len(description) > 500:
            description = description[:500] + '...'
        
        return cls(
            product_id=data.get('parent_asin', ''),
            title=data.get('title', ''),
            main_category=main_category,
            brand=brand,
            price=float(price),
            rating=float(data.get('average_rating', 0)),
            rating_count=int(data.get('rating_number', 0)),
            description=description,
            features=data.get('features', []),
            image_url=image_url,
            details=data.get('details', {}),
            in_stock=True,  # Amazon data doesn't have stock info
            condition='new'
        )


# SQL Statements
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(50) PRIMARY KEY,
    title TEXT NOT NULL,
    main_category VARCHAR(200) NOT NULL,
    brand VARCHAR(200),
    price NUMERIC(10, 2),
    rating NUMERIC(3, 2),
    rating_count INTEGER DEFAULT 0,
    description TEXT,
    features JSONB,
    image_url TEXT,
    details JSONB,
    in_stock BOOLEAN DEFAULT true,
    condition VARCHAR(20) DEFAULT 'new',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast filtering
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(main_category);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating);
CREATE INDEX IF NOT EXISTS idx_products_stock ON products(in_stock) WHERE in_stock = true;
"""

INSERT_PRODUCT_SQL = """
INSERT INTO products (
    product_id, title, main_category, brand, price, 
    rating, rating_count, description, features, 
    image_url, details, in_stock, condition
) VALUES %s
ON CONFLICT (product_id) DO UPDATE SET
    title = EXCLUDED.title,
    price = EXCLUDED.price,
    rating = EXCLUDED.rating,
    rating_count = EXCLUDED.rating_count
"""


def create_products_table() -> bool:
    """
    Create the products table and indexes.
    
    Returns:
        True if successful
    """
    with get_cursor() as cursor:
        if cursor is None:
            print("❌ No database connection")
            return False
        
        cursor.execute(CREATE_TABLE_SQL)
        print("✅ Products table created/verified")
        return True


def insert_products(products: List[Product], batch_size: int = 100) -> int:
    """
    Batch insert products into PostgreSQL.
    
    Args:
        products: List of Product objects
        batch_size: Insert batch size
    
    Returns:
        Number of products inserted
    """
    if not products:
        return 0
    
    # Convert to tuples for execute_values
    data = []
    for p in products:
        data.append((
            p.product_id,
            p.title,
            p.main_category,
            p.brand,
            p.price,
            p.rating,
            p.rating_count,
            p.description,
            json.dumps(p.features),
            p.image_url,
            json.dumps(p.details),
            p.in_stock,
            p.condition
        ))
    
    count = execute_many(INSERT_PRODUCT_SQL, data, page_size=batch_size)
    return count


def get_product_by_id(product_id: str) -> Optional[Dict]:
    """
    Get a single product by ID.
    
    Args:
        product_id: Product ID (parent_asin)
    
    Returns:
        Product dict or None
    """
    result = execute_query(
        "SELECT * FROM products WHERE product_id = %s",
        (product_id,)
    )
    
    if result and len(result) > 0:
        row = dict(result[0])
        # Parse JSONB fields
        if isinstance(row.get('features'), str):
            row['features'] = json.loads(row['features'])
        if isinstance(row.get('details'), str):
            row['details'] = json.loads(row['details'])
        return row
    return None


def get_products_by_ids(product_ids: List[str]) -> List[Dict]:
    """
    Get multiple products by IDs (for enriching Qdrant results).
    
    Args:
        product_ids: List of product IDs
    
    Returns:
        List of product dicts
    """
    if not product_ids:
        return []
    
    # Use ANY for efficient IN query
    result = execute_query(
        "SELECT * FROM products WHERE product_id = ANY(%s)",
        (product_ids,)
    )
    
    if not result:
        return []
    
    products = []
    for row in result:
        row = dict(row)
        # Parse JSONB fields
        if isinstance(row.get('features'), str):
            row['features'] = json.loads(row['features'])
        if isinstance(row.get('details'), str):
            row['details'] = json.loads(row['details'])
        products.append(row)
    
    return products


def get_product_count() -> int:
    """Get total product count."""
    result = execute_query("SELECT COUNT(*) as count FROM products")
    if result:
        return result[0]['count']
    return 0


def get_category_counts() -> Dict[str, int]:
    """Get product counts by category."""
    result = execute_query("""
        SELECT main_category, COUNT(*) as count 
        FROM products 
        GROUP BY main_category 
        ORDER BY count DESC
    """)
    
    if result:
        return {row['main_category']: row['count'] for row in result}
    return {}


def get_popular_products_by_category(category: str, limit: int = 10) -> List[Dict]:
    """
    Get popular products in a category (sorted by rating and review count).
    """
    # Simple 'popular' heuristic: High rating + many reviews
    query = """
        SELECT * FROM products 
        WHERE main_category = %s 
        ORDER BY rating DESC, rating_count DESC 
        LIMIT %s
    """
    
    result = execute_query(query, (category, limit))
    if not result:
        return []
        
    products = []
    for row in result:
        row = dict(row)
        if isinstance(row.get('features'), str):
            row['features'] = json.loads(row['features'])
        if isinstance(row.get('details'), str):
            row['details'] = json.loads(row['details'])
        products.append(row)
        
    return products


# Test
if __name__ == "__main__":
    print("🧪 Testing products module...")
    
    if create_products_table():
        count = get_product_count()
        print(f"📊 Current product count: {count}")
        
        categories = get_category_counts()
        if categories:
            print("📊 Categories:")
            for cat, cnt in list(categories.items())[:5]:
                print(f"   {cat}: {cnt}")
