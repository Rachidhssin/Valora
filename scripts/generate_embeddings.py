"""
Generate Text Embeddings for Products
Uses sentence-transformers all-MiniLM-L6-v2 model (384 dimensions)
"""
import json
import numpy as np
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer


def create_product_text(product: dict) -> str:
    """Create rich text representation for embedding."""
    features = ' '.join(product.get('features', []))
    return f"{product['name']} {product['category']} {product['brand']} {product['description']} {features}"


def generate_embeddings():
    """Generate embeddings for all products."""
    data_dir = Path(__file__).parent.parent / 'data'
    products_path = data_dir / 'products.json'
    
    if not products_path.exists():
        print("❌ products.json not found! Run generate_mock_data.py first.")
        return
    
    with open(products_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    print(f"📂 Loaded {len(products)} products")
    print("🔄 Loading sentence-transformers model (all-MiniLM-L6-v2)...")
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("🔄 Generating embeddings...")
    texts = [create_product_text(p) for p in products]
    
    # Generate embeddings in batches with progress bar
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    # Save embeddings
    output_path = data_dir / 'text_embeddings.npy'
    np.save(output_path, embeddings)
    
    print(f"\n✅ Generated {len(embeddings)} embeddings")
    print(f"📐 Embedding shape: {embeddings.shape}")
    print(f"📁 Saved to: {output_path}")
    
    # Verify
    loaded = np.load(output_path)
    print(f"✓ Verification: Loaded shape = {loaded.shape}")


if __name__ == "__main__":
    generate_embeddings()
