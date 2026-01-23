import asyncio
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

load_dotenv()

def debug_qdrant():
    print("🔍 Debugging Qdrant & Search...")
    
    # 1. Check Connection
    url = os.getenv("QDRANT_URL")
    key = os.getenv("QDRANT_API_KEY")
    print(f"🔗 URL: {url}")
    
    try:
        client = QdrantClient(url=url, api_key=key)
        collections = client.get_collections()
        print(f"✅ Connected! Collections: {[c.name for c in collections.collections]}")
        
        col_name = "products_main"
        
        # 2. Check Collection Stats
        info = client.get_collection(col_name)
        print(f"📊 Collection '{col_name}': {info.points_count} points")
        
        if info.points_count == 0:
            print("❌ Collection is empty! Run upload_to_qdrant.py again.")
            return

        # 3. Check a sample point
        res = client.scroll(collection_name=col_name, limit=1, with_payload=True)
        if res[0]:
            print(f"📝 Sample Payload: {res[0][0].payload}")
        
        # 4. Test Search
        print("\n🧠 Testing Search...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        vec = model.encode("laptop").tolist()
        
        hits = client.query_points(
            collection_name=col_name,
            query=vec,
            limit=5,
            with_payload=True
        ).points
        
        print(f"🔎 Search for 'laptop' found {len(hits)} results:")
        for hit in hits:
            print(f"   - {hit.payload.get('name')} (Score: {hit.score:.4f})")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_qdrant()
