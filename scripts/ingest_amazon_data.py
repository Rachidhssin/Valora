"""
Amazon JSONL Data Ingestion Pipeline
Loads real Amazon products into PostgreSQL and Qdrant
"""
import json
import argparse
import time
from pathlib import Path
from typing import List, Optional, Generator
import numpy as np
from tqdm import tqdm

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.connection import init_pool, close_pool
from db.products import Product, create_products_table, insert_products, get_product_count


def parse_jsonl(filepath: Path, limit: Optional[int] = None) -> Generator[dict, None, None]:
    """
    Parse JSONL file line by line (memory efficient).
    
    Args:
        filepath: Path to JSONL file
        limit: Max records to read (None = all)
    
    Yields:
        Parsed JSON records
    """
    count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if limit and count >= limit:
                break
            try:
                yield json.loads(line.strip())
                count += 1
            except json.JSONDecodeError:
                continue


def filter_valid_products(records: Generator, min_price: float = 1.0) -> List[Product]:
    """
    Filter and convert Amazon records to Product objects.
    
    Args:
        records: Generator of Amazon JSON records
        min_price: Minimum price to include
    
    Returns:
        List of valid Product objects
    """
    products = []
    skipped = 0
    
    for record in records:
        product = Product.from_amazon_json(record)
        
        if product is None:
            skipped += 1
            continue
        
        # Skip very low prices (likely errors)
        if product.price < min_price:
            skipped += 1
            continue
        
        # Skip products without title
        if not product.title or len(product.title) < 5:
            skipped += 1
            continue
        
        products.append(product)
    
    print(f"   ✓ Valid products: {len(products)}, Skipped: {skipped}")
    return products


def generate_embeddings(products: List[Product], batch_size: int = 32) -> np.ndarray:
    """
    Generate embeddings for products using sentence-transformers.
    
    Args:
        products: List of Product objects
        batch_size: Embedding batch size
    
    Returns:
        Numpy array of embeddings (N x 384)
    """
    from sentence_transformers import SentenceTransformer
    
    print("🔄 Loading sentence-transformers model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Create text representations
    texts = []
    for p in products:
        features_text = ' '.join(p.features[:5]) if p.features else ''
        text = f"{p.title} {p.main_category} {p.brand} {p.description[:200]} {features_text}"
        texts.append(text)
    
    print(f"🔄 Generating embeddings for {len(texts)} products...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    return embeddings


def upload_to_qdrant(products: List[Product], embeddings: np.ndarray, 
                     collection_name: str = "products_main") -> bool:
    """
    Upload products with embeddings to Qdrant.
    
    Args:
        products: List of Product objects
        embeddings: Numpy array of embeddings
        collection_name: Qdrant collection name
    
    Returns:
        True if successful
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if not qdrant_url:
        print("❌ QDRANT_URL not set in .env")
        return False
    
    print(f"🔗 Connecting to Qdrant: {qdrant_url[:50]}...")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    
    # Recreate collection
    try:
        collections = client.get_collections()
        existing = [c.name for c in collections.collections]
        
        if collection_name in existing:
            print(f"⚠️ Collection '{collection_name}' exists, recreating...")
            client.delete_collection(collection_name)
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        print(f"✅ Created collection '{collection_name}'")
    except Exception as e:
        print(f"❌ Error creating collection: {e}")
        return False
    
    # Prepare points with minimal payload
    points = []
    for idx, (product, embedding) in enumerate(zip(products, embeddings)):
        point = PointStruct(
            id=idx,
            vector=embedding.tolist(),
            payload={
                "product_id": product.product_id,
                "name": product.title,
                "category": product.main_category,
                "brand": product.brand,
                "price": product.price,
                "rating": product.rating,
                "rating_count": product.rating_count,
                "condition": product.condition,
                "in_stock": product.in_stock
            }
        )
        points.append(point)
    
    # Upload in batches
    batch_size = 100
    total_batches = (len(points) + batch_size - 1) // batch_size
    
    print(f"🚀 Uploading {len(points)} points to Qdrant...")
    for i in tqdm(range(0, len(points), batch_size), total=total_batches):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
    
    # Verify
    info = client.get_collection(collection_name)
    print(f"✅ Upload complete! Points in collection: {info.points_count}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Ingest Amazon JSONL data")
    parser.add_argument("--jsonl", type=str, 
                        default="data/electronic_products.jsonl",
                        help="Path to JSONL file")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of products (None = all with valid price)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and validate only, don't load")
    parser.add_argument("--skip-qdrant", action="store_true",
                        help="Skip Qdrant upload")
    parser.add_argument("--skip-postgres", action="store_true",
                        help="Skip PostgreSQL insert")
    
    args = parser.parse_args()
    
    # Resolve path
    base_dir = Path(__file__).parent.parent
    jsonl_path = base_dir / args.jsonl
    
    if not jsonl_path.exists():
        print(f"❌ File not found: {jsonl_path}")
        return
    
    print("=" * 60)
    print("🔄 AMAZON DATA INGESTION PIPELINE")
    print("=" * 60)
    print(f"📂 Source: {jsonl_path}")
    print(f"📊 Limit: {args.limit or 'All with valid price'}")
    print(f"🧪 Dry run: {args.dry_run}")
    print()
    
    # Step 1: Parse JSONL
    print("📖 Step 1: Parsing JSONL...")
    start = time.time()
    records = parse_jsonl(jsonl_path, limit=args.limit)
    products = filter_valid_products(records)
    print(f"   Time: {time.time() - start:.1f}s")
    print()
    
    if not products:
        print("❌ No valid products found!")
        return
    
    # Show sample
    print("📊 Sample product:")
    sample = products[0]
    print(f"   ID: {sample.product_id}")
    print(f"   Title: {sample.title[:60]}...")
    print(f"   Category: {sample.main_category}")
    print(f"   Brand: {sample.brand}")
    print(f"   Price: ${sample.price}")
    print(f"   Rating: {sample.rating} ({sample.rating_count} reviews)")
    print()
    
    if args.dry_run:
        print("🧪 Dry run complete - no data loaded")
        return
    
    # Step 2: Load to PostgreSQL
    if not args.skip_postgres:
        print("🐘 Step 2: Loading to PostgreSQL...")
        start = time.time()
        
        if not init_pool():
            print("❌ Failed to connect to PostgreSQL")
            return
        
        if not create_products_table():
            print("❌ Failed to create products table")
            return
        
        count = insert_products(products, batch_size=100)
        print(f"   ✓ Inserted {count} products")
        print(f"   Total in DB: {get_product_count()}")
        print(f"   Time: {time.time() - start:.1f}s")
        print()
        
        close_pool()
    
    # Step 3: Generate embeddings
    print("🧠 Step 3: Generating embeddings...")
    start = time.time()
    embeddings = generate_embeddings(products)
    print(f"   Shape: {embeddings.shape}")
    print(f"   Time: {time.time() - start:.1f}s")
    print()
    
    # Step 4: Upload to Qdrant
    if not args.skip_qdrant:
        print("🔍 Step 4: Uploading to Qdrant...")
        start = time.time()
        
        if upload_to_qdrant(products, embeddings):
            print(f"   Time: {time.time() - start:.1f}s")
        else:
            print("❌ Qdrant upload failed")
            return
    
    print()
    print("=" * 60)
    print("✅ INGESTION COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
