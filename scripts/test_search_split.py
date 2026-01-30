
import os
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from retrieval.qdrant_search import QdrantSearch, MultimodalQdrantSearch
from core.embeddings import EmbeddingService

async def test_search_split():
    print("🧪 Testing Search Architecture Split")
    
    # 1. Test Text Search (MiniLM on products_main)
    print("\n[1] Testing Text Search (MiniLM)...")
    try:
        embedder = EmbeddingService()
        text_search = QdrantSearch()
        
        query = "gaming laptop"
        print(f"   Query: '{query}'")
        
        vec = embedder.encode_query(query)
        print(f"   Embedding dimension: {len(vec)}")
        
        if len(vec) != 384:
            print("❌ Error: MiniLM should be 384 dim")
        else:
            print("✅ MiniLM embedding correct")

        results = text_search.search(vec.tolist(), limit=3)
        print(f"   Results found: {len(results)}")
        
        if results:
            print(f"   Top result: {results[0].name} (Score: {results[0].score:.4f})")
            print("✅ Text Search functional")
        else:
            print("⚠️ Text Search returned no results - 'products_main' might be empty")
            
    except Exception as e:
        print(f"❌ Text Search Failed: {e}")

    # 2. Test Image Search (CLIP on products_multimodal)
    print("\n[2] Testing Image Search (CLIP)...")
    try:
        visual_search = MultimodalQdrantSearch()
        if not visual_search.is_available:
             print("⚠️ Visual Search not available (skipping)")
        else:
             print("✅ Visual Search client available")
             # We won't run a real search without an image, but checking availability is good enough
             # to confirm the class loads and connects.
             
    except Exception as e:
        print(f"❌ Visual Search Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_search_split())
