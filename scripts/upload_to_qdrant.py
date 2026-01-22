"""
Upload Products and Embeddings to Qdrant Cloud
"""
import json
import numpy as np
import os
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

load_dotenv()


def upload_to_qdrant():
    """Upload products with embeddings to Qdrant."""
    data_dir = Path(__file__).parent.parent / 'data'
    
    # Load products
    products_path = data_dir / 'products.json'
    embeddings_path = data_dir / 'text_embeddings.npy'
    
    if not products_path.exists() or not embeddings_path.exists():
        print("❌ Missing files! Run generate_mock_data.py and generate_embeddings.py first.")
        return
    
    with open(products_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    embeddings = np.load(embeddings_path)
    
    print(f"📂 Loaded {len(products)} products and {len(embeddings)} embeddings")
    
    # Connect to Qdrant
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    
    if not qdrant_url:
        print("❌ QDRANT_URL not set in .env file!")
        return
    
    print(f"🔗 Connecting to Qdrant: {qdrant_url}")
    
    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key
    )
    
    collection_name = "products_main"
    
    # Create collection (or recreate if exists)
    try:
        collections = client.get_collections()
        existing = [c.name for c in collections.collections]
        
        if collection_name in existing:
            print(f"⚠️ Collection '{collection_name}' exists, recreating...")
            client.delete_collection(collection_name)
        
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=384,  # all-MiniLM-L6-v2 dimension
                distance=Distance.COSINE
            )
        )
        print(f"✅ Created collection '{collection_name}'")
    
    except Exception as e:
        print(f"❌ Error creating collection: {e}")
        return
    
    # Prepare points
    points = []
    for idx, (product, embedding) in enumerate(zip(products, embeddings)):
        point = PointStruct(
            id=idx,
            vector=embedding.tolist(),
            payload={
                "product_id": product["id"],
                "name": product["name"],
                "category": product["category"],
                "brand": product["brand"],
                "price": product["price"],
                "rating": product["rating"],
                "review_count": product["review_count"],
                "description": product["description"][:200],  # Truncate for payload size
                "features": product["features"],
                "condition": product["condition"],
                "in_stock": product["in_stock"],
                "warranty_months": product["warranty_months"],
                "shipping_days": product["shipping_days"],
                "seller_rating": product["seller_rating"]
            }
        )
        points.append(point)
    
    # Upload in batches
    batch_size = 100
    total_batches = (len(points) + batch_size - 1) // batch_size
    
    print(f"🚀 Uploading {len(points)} points in {total_batches} batches...")
    
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
        batch_num = i // batch_size + 1
        print(f"   Batch {batch_num}/{total_batches} uploaded ({len(batch)} points)")
    
    # Verify upload
    collection_info = client.get_collection(collection_name)
    print(f"\n✅ Upload complete!")
    print(f"📊 Collection stats:")
    print(f"   Points: {collection_info.points_count}")
    print(f"   Vectors: {collection_info.vectors_count}")


if __name__ == "__main__":
    upload_to_qdrant()
