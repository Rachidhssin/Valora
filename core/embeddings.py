"""
Embedding Service
Wraps sentence-transformers for query and batch encoding
"""
import numpy as np
from typing import List, Union
from functools import lru_cache

# Lazy load to avoid import time
_model = None


def _get_model():
    """Lazy load the embedding model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        print("🔄 Loading embedding model (all-MiniLM-L6-v2)...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Model loaded!")
    return _model


class EmbeddingService:
    """
    Service for generating text embeddings.
    Uses all-MiniLM-L6-v2 (384 dimensions, fast inference).
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self._model = None
    
    @property
    def model(self):
        """Lazy load model on first use."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model
    
    def encode_query(self, text: str) -> np.ndarray:
        """
        Encode a single query text.
        
        Args:
            text: Query string
            
        Returns:
            numpy array of shape (384,)
        """
        return self.model.encode(text, convert_to_numpy=True)
    
    def encode_batch(self, texts: List[str], batch_size: int = 32,
                     show_progress: bool = False) -> np.ndarray:
        """
        Encode multiple texts in batch.
        
        Args:
            texts: List of text strings
            batch_size: Batch size for encoding
            show_progress: Show progress bar
            
        Returns:
            numpy array of shape (len(texts), 384)
        """
        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
    
    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.
        """
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return 384


# Singleton instance for convenience
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get or create singleton embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


if __name__ == "__main__":
    print("🧪 Testing Embedding Service...")
    
    service = EmbeddingService()
    
    # Test single query
    query = "gaming laptop with RTX 4070"
    embedding = service.encode_query(query)
    print(f"\n📊 Query: \"{query}\"")
    print(f"   Embedding shape: {embedding.shape}")
    print(f"   First 5 values: {embedding[:5]}")
    
    # Test batch encoding
    queries = [
        "mechanical keyboard",
        "wireless gaming mouse",
        "4K monitor for programming"
    ]
    embeddings = service.encode_batch(queries)
    print(f"\n📊 Batch encoding: {len(queries)} queries")
    print(f"   Embeddings shape: {embeddings.shape}")
    
    # Test similarity
    sim = service.similarity(embeddings[0], embeddings[1])
    print(f"\n📊 Similarity (keyboard vs mouse): {sim:.4f}")
    
    print("\n✅ Embedding service test complete!")
