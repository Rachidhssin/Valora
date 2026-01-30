"""
Create Qdrant Payload Indices
Required for filtered search with ACORN
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "products")


def create_indices():
    """Create payload indices for filtered search."""
    print(f"🔗 Connecting to Qdrant at {QDRANT_URL}...")
    
    # Connect with API key if provided (for Qdrant Cloud)
    if QDRANT_API_KEY:
        print("   Using API key authentication")
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    else:
        client = QdrantClient(url=QDRANT_URL)
    
    # Check collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if COLLECTION_NAME not in collection_names:
        print(f"❌ Collection '{COLLECTION_NAME}' not found!")
        print(f"   Available: {collection_names}")
        return False
    
    print(f"✅ Found collection: {COLLECTION_NAME}")
    
    # Define indices to create
    indices = [
        ("price", PayloadSchemaType.FLOAT),
        ("in_stock", PayloadSchemaType.BOOL),
        ("category", PayloadSchemaType.KEYWORD),
        ("brand", PayloadSchemaType.KEYWORD),
        ("rating", PayloadSchemaType.FLOAT),
        ("name", PayloadSchemaType.TEXT),  # For text_any search
    ]
    
    print("\n📊 Creating payload indices...")
    
    for field_name, schema_type in indices:
        try:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field_name,
                field_schema=schema_type,
                wait=True
            )
            print(f"  ✅ Created index: {field_name} ({schema_type.value})")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"  ⏭️  Index already exists: {field_name}")
            else:
                print(f"  ⚠️  Failed to create {field_name}: {e}")
    
    # Verify indices
    print("\n🔍 Verifying indices...")
    collection_info = client.get_collection(COLLECTION_NAME)
    
    if hasattr(collection_info, 'payload_schema') and collection_info.payload_schema:
        print("  Payload schema:")
        for field, schema in collection_info.payload_schema.items():
            print(f"    • {field}: {schema}")
    
    print("\n✅ Payload indices configured!")
    print("   Filtered search with ACORN is now enabled.")
    
    return True


if __name__ == "__main__":
    success = create_indices()
    sys.exit(0 if success else 1)
