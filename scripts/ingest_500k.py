"""
500K Product Ingestion Pipeline
Optimized for large-scale data with GPU acceleration and batch processing.

Usage:
    python scripts/ingest_500k.py --jsonl data/electronic_products.jsonl --limit 500000
    python scripts/ingest_500k.py --jsonl data/electronic_products.jsonl --limit 500000 --resume
"""
import json
import argparse
import time
import os
import gc
from pathlib import Path
from typing import List, Dict, Optional, Generator
import numpy as np
from tqdm import tqdm
from dataclasses import dataclass

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


# ============================================================
# CATEGORY NORMALIZATION
# ============================================================
# Map generic Amazon categories to specific subcategories for better search

CATEGORY_NORMALIZATION = {
    # Electronics catch-all → more specific based on keywords
    'all electronics': 'electronics',
    'electronics': 'electronics',
    
    # Computers
    'computers': 'computers',
    'computers & accessories': 'computers',
    'computer accessories & peripherals': 'computer_accessories',
    'laptop accessories': 'laptop_accessories',
    
    # Audio
    'headphones': 'headphones',
    'headphones & earbuds': 'headphones',
    'home audio & theater': 'audio',
    'portable audio & video': 'portable_audio',
    'speakers': 'speakers',
    
    # Apple
    'apple products': 'apple',
    
    # Cameras
    'camera & photo': 'cameras',
    'camera & photo products': 'cameras',
    
    # Phones
    'cell phones & accessories': 'phones',
    'cell phone accessories': 'phone_accessories',
    
    # TV & Video
    'television & video': 'tv_video',
    'tv & video': 'tv_video',
    
    # Office
    'office electronics': 'office',
    'office products': 'office',
    
    # Wearables
    'wearable technology': 'wearables',
    
    # GPS
    'gps, finders & accessories': 'gps',
    'gps & navigation': 'gps',
}


def normalize_category(category: str, product_name: str = "") -> str:
    """
    Normalize category with fallback to keyword detection.
    
    Args:
        category: Original Amazon category
        product_name: Product name for keyword-based inference
        
    Returns:
        Normalized category string
    """
    cat_lower = category.lower().strip()
    
    # Direct mapping
    if cat_lower in CATEGORY_NORMALIZATION:
        return CATEGORY_NORMALIZATION[cat_lower]
    
    # Keyword-based inference for generic categories
    name_lower = product_name.lower()
    
    if 'monitor' in name_lower and 'baby' not in name_lower:
        return 'monitors'
    if 'laptop' in name_lower or 'notebook' in name_lower:
        return 'laptops'
    if 'keyboard' in name_lower:
        if any(kw in name_lower for kw in ['piano', 'midi', 'musical', 'synth']):
            return 'musical_instruments'
        return 'keyboards'
    if 'mouse' in name_lower or 'mice' in name_lower:
        return 'mice'
    if 'headphone' in name_lower or 'headset' in name_lower or 'earbuds' in name_lower:
        return 'headphones'
    if 'speaker' in name_lower:
        return 'speakers'
    if 'phone' in name_lower and 'headphone' not in name_lower:
        if 'case' in name_lower or 'charger' in name_lower:
            return 'phone_accessories'
        return 'phones'
    if 'tablet' in name_lower or 'ipad' in name_lower:
        return 'tablets'
    if 'camera' in name_lower:
        return 'cameras'
    if 'tv' in name_lower or 'television' in name_lower:
        return 'tvs'
    if 'router' in name_lower or 'modem' in name_lower:
        return 'networking'
    if 'printer' in name_lower:
        return 'printers'
    if 'ssd' in name_lower or 'hard drive' in name_lower or 'hdd' in name_lower:
        return 'storage'
    if 'ram' in name_lower or 'memory' in name_lower:
        return 'memory'
    if 'gpu' in name_lower or 'graphics card' in name_lower:
        return 'graphics_cards'
    if 'cpu' in name_lower or 'processor' in name_lower:
        return 'processors'
    if 'cable' in name_lower or 'adapter' in name_lower:
        return 'cables_adapters'
    
    # Keep original if no match
    return cat_lower.replace(' & ', '_').replace(' ', '_')


# ============================================================
# PRODUCT DATACLASS
# ============================================================

@dataclass
class Product:
    """Product model for ingestion."""
    product_id: str
    title: str
    main_category: str
    normalized_category: str
    brand: str
    price: float
    rating: float
    rating_count: int
    description: str
    features: List[str]
    image_url: str
    details: Dict
    in_stock: bool = True
    condition: str = "new"
    
    @classmethod
    def from_amazon_json(cls, data: Dict) -> Optional['Product']:
        """Convert Amazon JSON to Product."""
        try:
            # Extract price
            price = data.get('price')
            if price is None or price == '' or price == 'None':
                return None
            price = float(price) if isinstance(price, (int, float, str)) else 0
            if price < 1.0 or price > 50000:
                return None
            
            # Extract title
            title = data.get('title', '')
            if not title or len(title) < 5:
                return None
            
            # Extract category
            main_category = data.get('main_category', 'Unknown')
            normalized_category = normalize_category(main_category, title)
            
            # Extract brand
            brand = data.get('store', '')
            if not brand:
                details = data.get('details', {})
                brand = details.get('Brand', details.get('Manufacturer', 'Generic'))
            
            # Extract rating
            rating = data.get('average_rating', 0)
            if rating is None:
                rating = 0
            rating = float(rating) if rating else 0
            
            rating_count = data.get('rating_number', 0)
            if rating_count is None:
                rating_count = 0
            rating_count = int(rating_count) if rating_count else 0
            
            # Extract description
            description = ''
            desc_list = data.get('description', [])
            if isinstance(desc_list, list) and desc_list:
                description = desc_list[0][:500] if desc_list[0] else ''
            elif isinstance(desc_list, str):
                description = desc_list[:500]
            
            # Extract features
            features = data.get('features', [])
            if not isinstance(features, list):
                features = []
            features = features[:10]  # Limit features
            
            # Extract image
            images = data.get('images', [])
            image_url = ''
            if images and isinstance(images, list) and len(images) > 0:
                first_img = images[0]
                if isinstance(first_img, dict):
                    image_url = first_img.get('large', first_img.get('thumb', ''))
                elif isinstance(first_img, str):
                    image_url = first_img
            
            # Extract details
            details = data.get('details', {})
            if not isinstance(details, dict):
                details = {}
            
            return cls(
                product_id=data.get('parent_asin', ''),
                title=title,
                main_category=main_category,
                normalized_category=normalized_category,
                brand=brand or 'Generic',
                price=price,
                rating=rating,
                rating_count=rating_count,
                description=description,
                features=features,
                image_url=image_url,
                details=details
            )
            
        except Exception as e:
            return None


# ============================================================
# STREAMING PARSER
# ============================================================

def stream_products(filepath: Path, limit: Optional[int] = None, 
                    skip: int = 0) -> Generator[Product, None, None]:
    """
    Stream products from JSONL file (memory efficient).
    
    Args:
        filepath: Path to JSONL file
        limit: Max products to yield
        skip: Number of products to skip (for resume)
        
    Yields:
        Product objects
    """
    count = 0
    yielded = 0
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if limit and yielded >= limit:
                break
            
            try:
                data = json.loads(line.strip())
                product = Product.from_amazon_json(data)
                
                if product:
                    count += 1
                    if count > skip:
                        yielded += 1
                        yield product
                        
            except json.JSONDecodeError:
                continue


def count_lines(filepath: Path) -> int:
    """Count lines in file efficiently."""
    count = 0
    with open(filepath, 'rb') as f:
        for _ in f:
            count += 1
    return count


# ============================================================
# EMBEDDING GENERATION
# ============================================================

def create_embedding_text(product: Product) -> str:
    """Create rich text representation for embedding."""
    features = ' '.join(product.features[:5])
    return f"{product.title} {product.normalized_category} {product.brand} {product.description[:300]} {features}"


def generate_embeddings_batch(texts: List[str], model) -> np.ndarray:
    """Generate embeddings for a batch of texts."""
    embeddings = model.encode(
        texts,
        batch_size=128,  # Larger batch for GPU
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True  # L2 normalize for cosine similarity
    )
    return embeddings


# ============================================================
# POSTGRESQL OPERATIONS
# ============================================================

def insert_products_batch(products: List[Product], cursor) -> int:
    """Insert batch of products to PostgreSQL."""
    if not products:
        return 0
    
    # Match existing schema: main_category column, but store normalized value
    query = """
        INSERT INTO products (
            product_id, title, main_category, brand, price, rating, rating_count,
            description, features, image_url, details, in_stock, condition
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (product_id) DO UPDATE SET
            title = EXCLUDED.title,
            main_category = EXCLUDED.main_category,
            brand = EXCLUDED.brand,
            price = EXCLUDED.price,
            rating = EXCLUDED.rating,
            rating_count = EXCLUDED.rating_count,
            description = EXCLUDED.description,
            features = EXCLUDED.features,
            image_url = EXCLUDED.image_url,
            details = EXCLUDED.details,
            in_stock = EXCLUDED.in_stock,
            condition = EXCLUDED.condition
    """
    
    values = [
        (
            p.product_id, p.title, p.normalized_category, p.brand, p.price,
            p.rating, p.rating_count, p.description, 
            json.dumps(p.features),  # Convert list to JSON string
            p.image_url, json.dumps(p.details), p.in_stock, p.condition
        )
        for p in products
    ]
    
    cursor.executemany(query, values)
    return len(values)


# ============================================================
# QDRANT OPERATIONS
# ============================================================

def create_qdrant_collection(client, collection_name: str, recreate: bool = False):
    """Create or recreate Qdrant collection with proper config."""
    from qdrant_client.models import (
        Distance, VectorParams, OptimizersConfigDiff,
        HnswConfigDiff, PayloadSchemaType
    )
    
    collections = client.get_collections()
    existing = [c.name for c in collections.collections]
    
    if collection_name in existing:
        if recreate:
            print(f"   ⚠️ Deleting existing collection '{collection_name}'...")
            client.delete_collection(collection_name)
        else:
            print(f"   ✓ Collection '{collection_name}' exists, will upsert")
            return
    
    # Create optimized collection for 500K vectors
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=384,  # all-MiniLM-L6-v2 dimension
            distance=Distance.COSINE
        ),
        optimizers_config=OptimizersConfigDiff(
            indexing_threshold=20000,  # Start indexing after 20K points
            memmap_threshold=50000,    # Use memmap for large collections
        ),
        hnsw_config=HnswConfigDiff(
            m=16,                # Number of edges per node
            ef_construct=100,    # Construction search depth
            full_scan_threshold=10000  # Use HNSW after 10K points
        )
    )
    print(f"   ✅ Created collection '{collection_name}'")


def create_payload_indexes(client, collection_name: str):
    """Create payload indexes for filtered search."""
    from qdrant_client.models import PayloadSchemaType, TextIndexParams, TokenizerType
    
    print("   📇 Creating payload indexes...")
    
    # Keyword indexes
    for field in ['category', 'brand', 'condition']:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=PayloadSchemaType.KEYWORD
            )
            print(f"      ✓ {field} (keyword)")
        except Exception as e:
            print(f"      ⚠️ {field}: {e}")
    
    # Numeric indexes
    for field in ['price', 'rating']:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=PayloadSchemaType.FLOAT
            )
            print(f"      ✓ {field} (float)")
        except Exception as e:
            print(f"      ⚠️ {field}: {e}")
    
    # Boolean index
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name='in_stock',
            field_schema=PayloadSchemaType.BOOL
        )
        print(f"      ✓ in_stock (bool)")
    except Exception as e:
        print(f"      ⚠️ in_stock: {e}")
    
    # Text index for name search
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name='name',
            field_schema=TextIndexParams(
                type="text",
                tokenizer=TokenizerType.WORD,
                min_token_len=2,
                max_token_len=20,
                lowercase=True
            )
        )
        print(f"      ✓ name (text)")
    except Exception as e:
        print(f"      ⚠️ name: {e}")


def upload_to_qdrant_batch(client, collection_name: str, 
                           products: List[Product], embeddings: np.ndarray,
                           start_id: int, sub_batch_size: int = 50,
                           max_retries: int = 5) -> int:
    """Upload batch of products to Qdrant with retry logic."""
    from qdrant_client.models import PointStruct
    import time as time_module
    
    points = []
    for idx, (product, embedding) in enumerate(zip(products, embeddings)):
        point = PointStruct(
            id=start_id + idx,
            vector=embedding.tolist(),
            payload={
                "product_id": product.product_id,
                "name": product.title,
                "category": product.normalized_category,
                "brand": product.brand,
                "price": product.price,
                "rating": product.rating,
                "rating_count": product.rating_count,
                "condition": product.condition,
                "in_stock": product.in_stock
            }
        )
        points.append(point)
    
    # Upload in smaller sub-batches with retry
    uploaded = 0
    for i in range(0, len(points), sub_batch_size):
        sub_batch = points[i:i + sub_batch_size]
        
        for attempt in range(max_retries):
            try:
                client.upsert(collection_name=collection_name, points=sub_batch)
                uploaded += len(sub_batch)
                break
            except Exception as e:
                error_msg = str(e).lower()
                is_timeout = 'timeout' in error_msg or 'timed out' in error_msg
                
                if attempt < max_retries - 1:
                    # Longer waits for timeouts: 5, 10, 20, 40 seconds
                    wait_time = 5 * (2 ** attempt) if is_timeout else 2 ** attempt
                    print(f"\n   ⚠️ Retry {attempt + 1}/{max_retries} in {wait_time}s...")
                    time_module.sleep(wait_time)
                else:
                    print(f"\n❌ Failed after {max_retries} retries: {e}")
                    # Return what we uploaded so far instead of crashing
                    return uploaded
    
    return uploaded


# ============================================================
# MAIN PIPELINE
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Ingest 500K products")
    parser.add_argument("--jsonl", type=str, required=True,
                        help="Path to JSONL file")
    parser.add_argument("--limit", type=int, default=500000,
                        help="Number of products to ingest")
    parser.add_argument("--batch-size", type=int, default=5000,
                        help="Batch size for processing")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from last checkpoint")
    parser.add_argument("--recreate", action="store_true",
                        help="Recreate collection (delete existing)")
    parser.add_argument("--skip-postgres", action="store_true",
                        help="Skip PostgreSQL insert")
    parser.add_argument("--skip-qdrant", action="store_true",
                        help="Skip Qdrant upload")
    
    args = parser.parse_args()
    
    # Resolve paths
    base_dir = Path(__file__).parent.parent
    jsonl_path = base_dir / args.jsonl
    checkpoint_path = base_dir / 'data' / 'ingestion_checkpoint.json'
    
    if not jsonl_path.exists():
        print(f"❌ File not found: {jsonl_path}")
        return
    
    print("=" * 70)
    print("🚀 500K PRODUCT INGESTION PIPELINE")
    print("=" * 70)
    print(f"📂 Source: {jsonl_path}")
    print(f"📊 Target: {args.limit:,} products")
    print(f"📦 Batch size: {args.batch_size:,}")
    print()
    
    # Load checkpoint if resuming
    skip_count = 0
    if args.resume and checkpoint_path.exists():
        with open(checkpoint_path, 'r') as f:
            checkpoint = json.load(f)
            skip_count = checkpoint.get('processed', 0)
            print(f"📍 Resuming from checkpoint: {skip_count:,} products processed")
    
    # Initialize components
    print("🔧 Initializing components...")
    
    # Sentence Transformers
    from sentence_transformers import SentenceTransformer
    print("   Loading embedding model (GPU)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    device = 'cuda' if model.device.type == 'cuda' else 'cpu'
    print(f"   ✓ Model loaded on {device.upper()}")
    
    # PostgreSQL
    pg_conn = None
    pg_cursor = None
    if not args.skip_postgres:
        import psycopg2
        pg_conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', 5432),
            database=os.getenv('POSTGRES_DB', 'valora'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', '')
        )
        pg_cursor = pg_conn.cursor()
        print("   ✓ PostgreSQL connected")
    
    # Qdrant
    qdrant_client = None
    if not args.skip_qdrant:
        from qdrant_client import QdrantClient
        # Create client with longer timeouts for large uploads
        qdrant_client = QdrantClient(
            url=os.getenv('QDRANT_URL'),
            api_key=os.getenv('QDRANT_API_KEY'),
            timeout=120  # 2 minute timeout instead of default 30s
        )
        print("   ✓ Qdrant connected (timeout: 120s)")
        
        # Create/verify collection (skip if resuming)
        collection_name = "products_main"
        if not args.resume:
            create_qdrant_collection(qdrant_client, collection_name, recreate=args.recreate)
    
    print()
    
    # Process in batches
    total_processed = skip_count
    total_uploaded = skip_count
    start_time = time.time()
    batch_products = []
    
    print("🔄 Processing products...")
    print("-" * 70)
    
    try:
        # Create progress bar for entire dataset
        pbar = tqdm(
            stream_products(jsonl_path, limit=args.limit, skip=skip_count),
            total=args.limit - skip_count,
            desc="Products",
            unit="prod"
        )
        
        for product in pbar:
            batch_products.append(product)
            
            # Process batch when full
            if len(batch_products) >= args.batch_size:
                # Generate embeddings
                texts = [create_embedding_text(p) for p in batch_products]
                embeddings = generate_embeddings_batch(texts, model)
                
                # Upload to PostgreSQL
                if pg_cursor:
                    insert_products_batch(batch_products, pg_cursor)
                    pg_conn.commit()
                
                # Upload to Qdrant
                if qdrant_client:
                    upload_to_qdrant_batch(
                        qdrant_client, "products_main",
                        batch_products, embeddings,
                        start_id=total_uploaded
                    )
                
                total_processed += len(batch_products)
                total_uploaded += len(batch_products)
                
                # Update progress
                elapsed = time.time() - start_time
                rate = total_processed / elapsed if elapsed > 0 else 0
                pbar.set_postfix({
                    'uploaded': f'{total_uploaded:,}',
                    'rate': f'{rate:.0f}/s'
                })
                
                # Save checkpoint
                with open(checkpoint_path, 'w') as f:
                    json.dump({
                        'processed': total_processed,
                        'uploaded': total_uploaded,
                        'timestamp': time.time()
                    }, f)
                
                # Clear batch and free memory
                batch_products = []
                gc.collect()
        
        # Process remaining products
        if batch_products:
            texts = [create_embedding_text(p) for p in batch_products]
            embeddings = generate_embeddings_batch(texts, model)
            
            if pg_cursor:
                insert_products_batch(batch_products, pg_cursor)
                pg_conn.commit()
            
            if qdrant_client:
                upload_to_qdrant_batch(
                    qdrant_client, "products_main",
                    batch_products, embeddings,
                    start_id=total_uploaded
                )
            
            total_processed += len(batch_products)
            total_uploaded += len(batch_products)
        
        pbar.close()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted! Saving checkpoint...")
        with open(checkpoint_path, 'w') as f:
            json.dump({
                'processed': total_processed,
                'uploaded': total_uploaded,
                'timestamp': time.time()
            }, f)
        print(f"   Checkpoint saved at {total_processed:,} products")
        print("   Run with --resume to continue")
    
    finally:
        if pg_cursor:
            pg_cursor.close()
        if pg_conn:
            pg_conn.close()
    
    # Create indexes after upload
    if qdrant_client and not args.skip_qdrant:
        print()
        print("📇 Creating Qdrant payload indexes...")
        create_payload_indexes(qdrant_client, "products_main")
        
        # Verify
        info = qdrant_client.get_collection("products_main")
        print(f"\n✅ Qdrant collection: {info.points_count:,} points")
    
    # Summary
    elapsed = time.time() - start_time
    print()
    print("=" * 70)
    print("✅ INGESTION COMPLETE!")
    print("=" * 70)
    print(f"📊 Products processed: {total_processed:,}")
    print(f"⏱️  Total time: {elapsed/60:.1f} minutes")
    print(f"🚀 Rate: {total_processed/elapsed:.0f} products/second")
    print()
    
    # Cleanup checkpoint
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print("🧹 Checkpoint file removed")


if __name__ == "__main__":
    main()
