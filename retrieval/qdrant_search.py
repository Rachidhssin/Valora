"""
Qdrant Search Module
Provides ANN search with payload filtering via Qdrant Cloud
"""
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


@dataclass
class SearchResult:
    """Represents a single search result."""
    product_id: str
    name: str
    category: str
    brand: str
    price: float
    rating: float
    rating_count: int
    score: float  # Similarity score
    condition: str
    in_stock: bool
    features: List[str]
    image_url: str = ""
    description: str = ""
    specs: Dict = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'product_id': self.product_id,
            'name': self.name,
            'category': self.category,
            'brand': self.brand,
            'price': self.price,
            'rating': self.rating,
            'rating_count': self.rating_count,
            'score': self.score,
            'condition': self.condition,
            'in_stock': self.in_stock,
            'features': self.features,
            'image_url': self.image_url,
            'description': self.description,
            'specs': self.specs or {}
        }


class QdrantSearch:
    """
    Qdrant-based semantic search with payload filtering.
    """
    
    def __init__(self, collection_name: str = "products_main"):
        self.collection_name = collection_name
        self._client = None
        
        if QDRANT_AVAILABLE:
            self._init_client()
            
    def enrich_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Enrich Qdrant results with full details from PostgreSQL.
        """
        from db.products import get_products_by_ids
        
        if not results:
            return []
            
        product_ids = [r.product_id for r in results]
        db_products = {p['product_id']: p for p in get_products_by_ids(product_ids)}
        
        enriched = []
        for r in results:
            if r.product_id in db_products:
                p = db_products[r.product_id]
                # Update fields that might be truncated in Qdrant or missing
                r.description = p.get('description', r.description)
                r.specs = p.get('details', {})
                r.image_url = p.get('image_url', "")
                r.features = p.get('features', r.features)
                r.rating_count = p.get('rating_count', r.rating_count)
            enriched.append(r)
            
        return enriched
    
    def _init_client(self):
        """Initialize Qdrant client."""
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if not qdrant_url:
            print("⚠️ QDRANT_URL not set, search will not work")
            return
        
        try:
            self._client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key
            )
        except Exception as e:
            print(f"⚠️ Qdrant client init failed: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if Qdrant is available."""
        return self._client is not None
    
    def search(self, query_vector: List[float], limit: int = 20,
               filters: Optional[Dict] = None) -> List[SearchResult]:
        """
        Perform ANN search with optional filters.
        
        Args:
            query_vector: 384-dim embedding vector
            limit: Max results to return
            filters: Optional Qdrant filter dict
            
        Returns:
            List of SearchResult objects
        """
        if not self._client:
            return []
        
        try:
            # Build Qdrant filter if provided
            qdrant_filter = self._build_filter(filters) if filters else None
            
            results = self._client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                limit=limit,
                with_payload=True
            )
            
            return [self._to_search_result(r) for r in results.points]
            
        except Exception as e:
            print(f"⚠️ Search error: {e}")
            return []
    
    def search_with_constraints(self, query_vector: List[float],
                                max_price: Optional[float] = None,
                                min_price: Optional[float] = None,
                                category: Optional[str] = None,
                                categories: Optional[List[str]] = None,
                                brands: Optional[List[str]] = None,
                                in_stock_only: bool = True,
                                conditions: Optional[List[str]] = None,
                                min_rating: Optional[float] = None,
                                limit: int = 20) -> List[SearchResult]:
        """
        Search with multiple constraint filters.
        
        Args:
            query_vector: Embedding vector
            max_price: Maximum price filter
            min_price: Minimum price filter
            category: Single category filter
            categories: Multiple category filter (OR)
            brands: Brand filter (OR)
            in_stock_only: Only show in-stock items
            conditions: Condition filter (new, refurbished, open-box)
            min_rating: Minimum rating filter
            limit: Max results
            
        Returns:
            Filtered search results
        """
        filters = {"must": []}
        
        # Price range
        if max_price is not None or min_price is not None:
            price_filter = {"key": "price", "range": {}}
            if max_price is not None:
                price_filter["range"]["lte"] = max_price
            if min_price is not None:
                price_filter["range"]["gte"] = min_price
            filters["must"].append(price_filter)
        
        # In stock
        if in_stock_only:
            filters["must"].append({
                "key": "in_stock",
                "match": {"value": True}
            })
        
        # Rating
        if min_rating is not None:
            filters["must"].append({
                "key": "rating",
                "range": {"gte": min_rating}
            })
        
        # Single category
        if category:
            filters["must"].append({
                "key": "category",
                "match": {"value": category}
            })
        
        # Multiple categories (should)
        if categories:
            filters["should"] = [
                {"key": "category", "match": {"value": cat}}
                for cat in categories
            ]
        
        # Brands
        if brands:
            brand_filter = {"should": [
                {"key": "brand", "match": {"value": brand}}
                for brand in brands
            ]}
            # Merge with existing
            if "should" not in filters:
                filters.update(brand_filter)
        
        # Conditions
        if conditions:
            condition_filter = {"should": [
                {"key": "condition", "match": {"value": cond}}
                for cond in conditions
            ]}
            if "should" not in filters:
                filters.update(condition_filter)
        
        return self.search(query_vector, limit=limit, filters=filters if filters["must"] else None)
    
    def _build_filter(self, filter_dict: Dict) -> Filter:
        """Build Qdrant Filter from dict."""
        must_conditions = []
        should_conditions = []
        
        for condition in filter_dict.get("must", []):
            if "match" in condition:
                must_conditions.append(
                    FieldCondition(
                        key=condition["key"],
                        match=MatchValue(value=condition["match"]["value"])
                    )
                )
            elif "range" in condition:
                must_conditions.append(
                    FieldCondition(
                        key=condition["key"],
                        range=Range(**condition["range"])
                    )
                )
        
        for condition in filter_dict.get("should", []):
            if "match" in condition:
                should_conditions.append(
                    FieldCondition(
                        key=condition["key"],
                        match=MatchValue(value=condition["match"]["value"])
                    )
                )
        
        return Filter(
            must=must_conditions if must_conditions else None,
            should=should_conditions if should_conditions else None
        )
    
    def _to_search_result(self, hit) -> SearchResult:
        """Convert Qdrant hit to SearchResult."""
        payload = hit.payload
        return SearchResult(
            product_id=payload.get("product_id", ""),
            name=payload.get("name", ""),
            category=payload.get("category", ""),
            brand=payload.get("brand", ""),
            price=payload.get("price", 0.0),
            rating=payload.get("rating", 0.0),
            rating_count=payload.get("rating_count", 0),
            score=hit.score,
            condition=payload.get("condition", "new"),
            in_stock=payload.get("in_stock", True),
            features=payload.get("features", []),
            description=payload.get("description", "")
        )
    
    def get_by_category(self, category: str, limit: int = 50) -> List[Dict]:
        """Get products by category (scroll, no vector needed)."""
        if not self._client:
            return []
        
        try:
            result = self._client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[FieldCondition(
                        key="category",
                        match=MatchValue(value=category)
                    )]
                ),
                limit=limit,
                with_payload=True
            )
            
            return [point.payload for point, _ in [result]]
            
        except Exception as e:
            print(f"⚠️ Category fetch error: {e}")
            return []
    
    def collection_info(self) -> Dict[str, Any]:
        """Get collection statistics."""
        if not self._client:
            return {"error": "Client not initialized"}
        
        try:
            info = self._client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "status": info.status.value
            }
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    print("🧪 Testing Qdrant Search...")
    
    search = QdrantSearch()
    
    if search.is_available:
        info = search.collection_info()
        print(f"\n📊 Collection info: {info}")
        
        # Test search (would need embeddings)
        print("\n✅ Qdrant search module initialized successfully")
    else:
        print("\n⚠️ Qdrant not available (check QDRANT_URL in .env)")
