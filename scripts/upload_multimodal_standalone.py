"""
Upload Multimodal Embeddings to Qdrant - Standalone Version

This script uploads CLIP embeddings to Qdrant WITHOUT depending on products_main.
It reads product data directly from products.jsonl, making it fully self-contained.

Features:
- Reads products.jsonl directly for product payloads
- Uses CLIP text + image embeddings from .npy files
- Creates products_multimodal collection with named vectors
- Completely independent of products_main collection

Usage:
    python scripts/upload_multimodal_standalone.py
"""
import json
import numpy as np
import os
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, NamedVectors
)
from tqdm import tqdm

load_dotenv()


def extract_product_payload(product: dict) -> dict:
    """
    Extract relevant fields from products.jsonl into Qdrant-friendly payload.
    
    Normalizes the Amazon Product Dataset 2023 format into our schema.
    """
    # Get main image URL
    images = product.get('images', [])
    image_url = ""
    if images:
        main_img = images[0]
        image_url = main_img.get('hi_res') or main_img.get('large') or main_img.get('thumb', '')
    
    # Extract price (may be a dict or already processed)
    price_field = product.get('price', 0)
    try:
        if isinstance(price_field, str):
            # Parse "$299.99" format
            price = float(price_field.replace('$', '').replace(',', '').strip())
        elif isinstance(price_field, dict):
            price = price_field.get('value', 0)
        else:
            price = float(price_field or 0)
    except (ValueError, TypeError):
        price = 0
    
    # Extract rating
    rating = product.get('rating', 0)
    if isinstance(rating, str):
        try:
            rating = float(rating.split()[0])
        except (ValueError, IndexError):
            rating = 0
    
    # Get category from categories list (last 2 are most specific)
    categories = product.get('categories', [])
    category = categories[-1] if categories else 'General'
    
    # Features (flatten list)
    features = product.get('features', [])
    if isinstance(features, list):
        features = features[:5]  # Top 5 features
    else:
        features = []
    
    # Description (may be list)
    desc = product.get('description', '')
    if isinstance(desc, list):
        desc = ' '.join(desc[:2])  # First 2 paragraphs
    
    return {
        'product_id': product.get('parent_asin') or product.get('asin', ''),
        'name': product.get('title', '')[:500],  # Truncate long names
        'category': category,
        'brand': product.get('store', 'Unknown'),
        'price': price,
        'rating': rating,
        'review_count': product.get('rating_number', 0),
        'condition': 'new',
        'in_stock': True,
        'features': features,
        'description': desc[:1000],  # Truncate long descriptions
        'image_url': image_url,
    }


def upload_multimodal_standalone():
    """
    Upload CLIP embeddings to Qdrant using products.jsonl directly.
    
    This is completely independent of products_main collection.
    """
    data_dir = Path(__file__).parent.parent / 'data'
    
    # Check for CLIP embeddings
    clip_text_path = data_dir / 'clip_text_embeddings.npy'
    clip_image_path = data_dir / 'clip_image_embeddings.npy'
    ids_path = data_dir / 'clip_product_ids.npy'
    products_path = data_dir / 'products.jsonl'
    
    # Verify all files exist
    missing = []
    if not clip_text_path.exists():
        missing.append('clip_text_embeddings.npy')
    if not clip_image_path.exists():
        missing.append('clip_image_embeddings.npy')
    if not products_path.exists():
        missing.append('products.jsonl')
    
    if missing:
        print(f"❌ Missing required files: {missing}")
        print("   Run: python scripts/generate_multimodal_embeddings.py first")
        return
    
    # Load embeddings
    print("📥 Loading CLIP embeddings...")
    clip_text_embeddings = np.load(clip_text_path)
    clip_image_embeddings = np.load(clip_image_path)
    product_ids = np.load(ids_path) if ids_path.exists() else None
    
    print(f"   📐 Text embeddings: {clip_text_embeddings.shape}")
    print(f"   📐 Image embeddings: {clip_image_embeddings.shape}")
    
    total_embeddings = len(clip_text_embeddings)
    
    # Connect to Qdrant
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if not qdrant_url:
        print("❌ QDRANT_URL not set in .env")
        return
    
    print(f"🔗 Connecting to Qdrant: {qdrant_url}")
    
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    collection_name = "products_multimodal"
    
    # Create/recreate collection with named vectors
    try:
        collections = client.get_collections()
        existing = [c.name for c in collections.collections]
        
        if collection_name in existing:
            print(f"⚠️ Collection '{collection_name}' exists, recreating...")
            client.delete_collection(collection_name)
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "text": VectorParams(size=512, distance=Distance.COSINE),
                "image": VectorParams(size=512, distance=Distance.COSINE)
            }
        )
        print(f"✅ Created multimodal collection '{collection_name}'")
        print("   - text: 512-dim CLIP text embeddings")
        print("   - image: 512-dim CLIP image embeddings")
        
    except Exception as e:
        print(f"❌ Error creating collection: {e}")
        return
    
    # Upload products with embeddings
    print(f"\n🚀 Uploading {total_embeddings} products from products.jsonl...")
    
    batch_size = 100
    processed = 0
    
    # Build ID mapping if available
    if product_ids is not None:
        id_to_idx = {int(pid): idx for idx, pid in enumerate(product_ids)}
    else:
        id_to_idx = None
    
    batch_points = []
    
    with tqdm(total=total_embeddings, desc="Processing") as pbar:
        with open(products_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                if line_num >= total_embeddings:
                    break
                
                try:
                    product = json.loads(line.strip())
                    
                    # Get embedding index
                    if id_to_idx is not None and line_num not in id_to_idx:
                        continue
                    idx = id_to_idx.get(line_num, line_num) if id_to_idx else line_num
                    
                    if idx >= len(clip_text_embeddings):
                        continue
                    
                    # Extract payload from product
                    payload = extract_product_payload(product)
                    
                    # Create point with named vectors
                    point = PointStruct(
                        id=line_num,  # Use sequential line number as ID
                        vector={
                            "text": clip_text_embeddings[idx].tolist(),
                            "image": clip_image_embeddings[idx].tolist()
                        },
                        payload=payload
                    )
                    
                    batch_points.append(point)
                    
                    # Upload batch
                    if len(batch_points) >= batch_size:
                        client.upsert(collection_name=collection_name, points=batch_points)
                        pbar.update(len(batch_points))
                        processed += len(batch_points)
                        batch_points = []
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    if line_num < 10:  # Only log first few errors
                        print(f"\n⚠️ Error at line {line_num}: {e}")
                    continue
    
    # Upload remaining
    if batch_points:
        client.upsert(collection_name=collection_name, points=batch_points)
        processed += len(batch_points)
        print(f"   Uploaded final batch: {len(batch_points)}")
    
    # Verify upload
    collection_info = client.get_collection(collection_name)
    print(f"\n✅ Upload complete!")
    print(f"📊 Collection stats:")
    print(f"   Points: {collection_info.points_count}")
    print(f"   Status: {collection_info.status.value}")
    
    # Test searches
    print("\n🔍 Testing search capabilities...")
    
    # Test 1: Text search
    print("\n📝 Test 1: Text Vector Search")
    test_text_vec = clip_text_embeddings[0].tolist()
    text_results = client.search(
        collection_name=collection_name,
        query_vector=("text", test_text_vec),
        limit=3
    )
    for r in text_results:
        print(f"   - {r.payload.get('name', 'N/A')[:50]} | Score: {r.score:.4f}")
    
    # Test 2: Image search
    print("\n🖼️ Test 2: Image Vector Search")
    test_image_vec = clip_image_embeddings[0].tolist()
    image_results = client.search(
        collection_name=collection_name,
        query_vector=("image", test_image_vec),
        limit=3
    )
    for r in image_results:
        print(f"   - {r.payload.get('name', 'N/A')[:50]} | Score: {r.score:.4f}")
    
    # Test 3: Cross-modal (text query -> image similarity)
    print("\n🔄 Test 3: Cross-Modal Search (text vector against image index)")
    cross_results = client.search(
        collection_name=collection_name,
        query_vector=("image", test_text_vec),  # Use text vec to search images
        limit=3
    )
    for r in cross_results:
        print(f"   - {r.payload.get('name', 'N/A')[:50]} | Score: {r.score:.4f}")
    
    print("\n🎉 Multimodal search ready!")
    print("   All searches (text, image, hybrid) now use this collection.")


if __name__ == "__main__":
    upload_multimodal_standalone()
