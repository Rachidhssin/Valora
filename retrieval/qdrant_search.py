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
    from qdrant_client.models import (
        Filter, FieldCondition, MatchValue, MatchAny, MatchText, Range,
        SearchParams, AcornSearchParams
    )
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

# ACORN-1 search method for better filtered search accuracy (Qdrant 1.13+)
# Expands HNSW traversal when multiple low-selectivity filters are applied
# This improves relevance at the cost of some performance
ACORN_SEARCH_PARAMS = SearchParams(
    exact=False,
    indexed_only=False,
    hnsw_ef=128,  # Higher ef for expanded traversal
    acorn=AcornSearchParams(
        enable=True,  # Enable ACORN-1 method
        max_selectivity=0.5  # Use ACORN when filter selectivity < 50%
    )
) if QDRANT_AVAILABLE else None


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
               filters: Optional[Dict] = None,
               use_acorn: bool = True) -> List[SearchResult]:
        """
        Perform ANN search with optional filters.
        
        Args:
            query_vector: 384-dim embedding vector
            limit: Max results to return
            filters: Optional Qdrant filter dict
            use_acorn: Use ACORN search for better filtered accuracy (Qdrant 1.13+)
            
        Returns:
            List of SearchResult objects
        """
        if not self._client:
            return []
        
        try:
            # Build Qdrant filter if provided
            qdrant_filter = self._build_filter(filters) if filters else None
            
            # Use ACORN params when filtering for better relevance
            search_params = ACORN_SEARCH_PARAMS if (use_acorn and qdrant_filter) else None
            
            results = self._client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                search_params=search_params,
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
                                text_query: Optional[str] = None,
                                limit: int = 20,
                                use_acorn: bool = True) -> List[SearchResult]:
        """
        Search with multiple constraint filters using ACORN for better accuracy.
        
        Uses Qdrant native filters with ACORN search method for improved
        relevance when multiple low-selectivity filters are applied.
        
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
            text_query: Text search in product name/description (uses text_any)
            limit: Max results
            use_acorn: Use ACORN for better filtered search (Qdrant 1.13+)
            
        Returns:
            Filtered search results
        """
        if not self._client:
            return []
        
        try:
            # Build native Qdrant filter for server-side filtering
            must_conditions = []
            should_conditions = []
            
            # Price range filter
            if max_price is not None or min_price is not None:
                range_params = {}
                if max_price is not None:
                    range_params["lte"] = max_price
                if min_price is not None:
                    range_params["gte"] = min_price
                must_conditions.append(
                    FieldCondition(key="price", range=Range(**range_params))
                )
            
            # Single category filter
            if category:
                must_conditions.append(
                    FieldCondition(key="category", match=MatchValue(value=category))
                )
            
            # Multiple categories (OR) - use MatchAny
            if categories and len(categories) > 0:
                must_conditions.append(
                    FieldCondition(key="category", match=MatchAny(any=categories))
                )
            
            # Multiple brands (OR) - use MatchAny
            if brands and len(brands) > 0:
                must_conditions.append(
                    FieldCondition(key="brand", match=MatchAny(any=brands))
                )
            
            # In stock filter
            if in_stock_only:
                must_conditions.append(
                    FieldCondition(key="in_stock", match=MatchValue(value=True))
                )
            
            # Conditions filter (new, refurbished, etc.) - use MatchAny
            if conditions and len(conditions) > 0:
                must_conditions.append(
                    FieldCondition(key="condition", match=MatchAny(any=conditions))
                )
            
            # Rating filter
            if min_rating is not None:
                must_conditions.append(
                    FieldCondition(key="rating", range=Range(gte=min_rating))
                )
            
            # Text search using text_any (Qdrant 1.13+)
            # Matches products containing ANY of the query terms
            if text_query:
                must_conditions.append(
                    FieldCondition(key="name", match=MatchText(text=text_query))
                )
            
            # Build filter
            qdrant_filter = None
            if must_conditions or should_conditions:
                qdrant_filter = Filter(
                    must=must_conditions if must_conditions else None,
                    should=should_conditions if should_conditions else None
                )
            
            # Use ACORN params when we have multiple filters for better relevance
            search_params = ACORN_SEARCH_PARAMS if (use_acorn and qdrant_filter) else None
            
            results = self._client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                search_params=search_params,
                limit=limit,
                with_payload=True
            )
            
            return [self._to_search_result(r) for r in results.points]
            
        except Exception as e:
            print(f"⚠️ Filtered search error: {e}")
            # Fallback to Python-side filtering
            return self._search_with_python_filters(
                query_vector, max_price, min_price, category, categories,
                brands, in_stock_only, conditions, min_rating, limit
            )
    
    def _search_with_python_filters(self, query_vector: List[float],
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
        Fallback: Python-side filtering when Qdrant native filters fail.
        """
        # Get more results than needed for Python-side filtering
        search_limit = min(limit * 5, 100)
        results = self.search(query_vector, limit=search_limit, filters=None, use_acorn=False)
        
        # Apply Python-side filters
        filtered = []
        for r in results:
            # Price filter
            if max_price is not None and r.price > max_price:
                continue
            if min_price is not None and r.price < min_price:
                continue
                
            # Category filter (case-insensitive partial match)
            if category:
                r_cat = r.category.lower() if r.category else ""
                if category.lower() not in r_cat and r_cat not in category.lower():
                    continue
                    
            # Multiple categories (OR) - match any
            if categories:
                r_cat = r.category.lower() if r.category else ""
                matched = any(cat.lower() in r_cat or r_cat in cat.lower() for cat in categories)
                if not matched:
                    continue
                    
            # Brand filter (OR) - match any
            if brands:
                r_brand = r.brand.lower() if r.brand else ""
                matched = any(brand.lower() in r_brand or r_brand in brand.lower() for brand in brands)
                if not matched:
                    continue
                    
            # In stock filter
            if in_stock_only and not r.in_stock:
                continue
                
            # Condition filter
            if conditions:
                r_cond = r.condition.lower() if r.condition else "new"
                if not any(cond.lower() in r_cond or r_cond in cond.lower() for cond in conditions):
                    continue
                    
            # Rating filter
            if min_rating is not None and r.rating < min_rating:
                continue
                
            filtered.append(r)
            
            # Stop once we have enough
            if len(filtered) >= limit:
                break
        
        return filtered
    
    def search_text_any(self, query_vector: List[float],
                        text_terms: List[str],
                        field: str = "name",
                        limit: int = 20) -> List[SearchResult]:
        """
        Search using text_any operator (Qdrant 1.13+).
        
        Matches documents where the field contains ANY of the provided terms.
        Useful for multi-word product searches like "gaming laptop RTX".
        
        Args:
            query_vector: Embedding vector for semantic ranking
            text_terms: List of terms to match (OR logic)
            field: Field to search in (name, description)
            limit: Max results
            
        Returns:
            Search results matching any of the terms
        """
        if not self._client:
            return []
        
        try:
            # Use MatchText for text search (supports text_any in 1.13+)
            text_query = " ".join(text_terms)
            
            qdrant_filter = Filter(
                must=[FieldCondition(key=field, match=MatchText(text=text_query))]
            )
            
            results = self._client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=qdrant_filter,
                search_params=ACORN_SEARCH_PARAMS,
                limit=limit,
                with_payload=True
            )
            
            return [self._to_search_result(r) for r in results.points]
            
        except Exception as e:
            print(f"⚠️ Text search error: {e}")
            return []
    
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


class MultimodalQdrantSearch:
    """
    Unified multimodal search using CLIP embeddings.
    Supports text, image, and hybrid search - all through ONE collection.
    
    This is the ONLY search class needed - replaces both QdrantSearch 
    and the old text-only system with a unified CLIP-based approach.
    """
    
    def __init__(self, collection_name: str = "products_multimodal"):
        self.collection_name = collection_name
        self._client = None
        self._is_available = False
        self._clip_model = None
        self._clip_processor = None
        
        if QDRANT_AVAILABLE:
            self._init_client()
    
    def _init_client(self):
        """Initialize Qdrant client."""
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if not qdrant_url:
            print("⚠️ QDRANT_URL not set")
            return
        
        try:
            self._client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key
            )
            # Check if multimodal collection exists
            collections = self._client.get_collections()
            existing = [c.name for c in collections.collections]
            self._is_available = self.collection_name in existing
            
            if not self._is_available:
                print(f"⚠️ Multimodal collection '{self.collection_name}' not found")
                print("   Run: python scripts/upload_multimodal_to_qdrant.py")
            else:
                print(f"✅ Multimodal search ready: {self.collection_name}")
        except Exception as e:
            print(f"⚠️ Qdrant client init failed: {e}")
    
    def _load_clip(self):
        """Lazy load CLIP model for text encoding."""
        if self._clip_model is None:
            try:
                from transformers import CLIPProcessor, CLIPModel
                import torch
                
                model_name = "openai/clip-vit-base-patch32"
                self._clip_processor = CLIPProcessor.from_pretrained(model_name)
                self._clip_model = CLIPModel.from_pretrained(model_name)
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self._clip_model = self._clip_model.to(device)
                self._device = device
                print(f"✅ CLIP loaded for text encoding ({device})")
            except Exception as e:
                print(f"⚠️ Failed to load CLIP: {e}")
    
    def encode_text(self, text: str) -> List[float]:
        """Encode text using CLIP (512-dim vector)."""
        self._load_clip()
        if self._clip_model is None:
            return []
        
        import torch
        
        inputs = self._clip_processor(
            text=[text], 
            return_tensors="pt", 
            padding=True, 
            truncation=True,
            max_length=77
        )
        inputs = {k: v.to(self._device) for k, v in inputs.items()}
        
        with torch.no_grad():
            features = self._clip_model.get_text_features(**inputs)
            features = features / features.norm(dim=-1, keepdim=True)
        
        return features[0].cpu().numpy().tolist()
    
    @property
    def is_available(self) -> bool:
        return self._is_available and self._client is not None
    
    @property
    def client(self):
        return self._client
    
    def enrich_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Enrich Qdrant results with full details from PostgreSQL."""
        from db.products import get_products_by_ids
        
        if not results:
            return []
            
        product_ids = [r.product_id for r in results]
        db_products = {p['product_id']: p for p in get_products_by_ids(product_ids)}
        
        enriched = []
        for r in results:
            if r.product_id in db_products:
                p = db_products[r.product_id]
                r.description = p.get('description', r.description)
                r.specs = p.get('details', {})
                r.image_url = p.get('image_url', "")
                r.features = p.get('features', r.features)
                r.rating_count = p.get('rating_count', r.rating_count)
            enriched.append(r)
            
        return enriched
    
    def search(
        self,
        query: str,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        categories: Optional[List[str]] = None,
        category: Optional[str] = None,
        brands: Optional[List[str]] = None,
        in_stock_only: bool = True,
        min_rating: Optional[float] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Main text search using CLIP text embeddings.
        
        This is the primary search method - encodes the query with CLIP
        and searches against the "text" named vector in products_multimodal.
        """
        if not self.is_available:
            return []
        
        # Encode query with CLIP
        query_vec = self.encode_text(query)
        if not query_vec:
            return []
        
        return self.search_by_text(
            text_vector=query_vec,
            max_price=max_price,
            min_price=min_price,
            categories=categories,
            category=category,
            brands=brands,
            in_stock_only=in_stock_only,
            min_rating=min_rating,
            limit=limit
        )
    
    def search_with_constraints(
        self,
        query_vector: List[float],
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        category: Optional[str] = None,
        categories: Optional[List[str]] = None,
        brands: Optional[List[str]] = None,
        in_stock_only: bool = True,
        conditions: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        text_query: Optional[str] = None,
        limit: int = 20,
        use_acorn: bool = True
    ) -> List[SearchResult]:
        """
        Search with vector and multiple constraint filters.
        Compatible with old QdrantSearch API for easy migration.
        """
        return self.search_by_text(
            text_vector=query_vector,
            max_price=max_price,
            min_price=min_price,
            categories=categories,
            category=category,
            brands=brands,
            in_stock_only=in_stock_only,
            conditions=conditions,
            min_rating=min_rating,
            limit=limit
        )
    
    def search_by_image(
        self,
        image_vector: List[float],
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        categories: Optional[List[str]] = None,
        in_stock_only: bool = True,
        min_rating: Optional[float] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Search products by image similarity using CLIP image embeddings.
        
        Args:
            image_vector: 512-dim CLIP image embedding
            max_price: Maximum price filter
            min_price: Minimum price filter
            categories: Category filter
            in_stock_only: Only show in-stock items
            min_rating: Minimum rating filter
            limit: Max results
            
        Returns:
            Products similar to the query image
        """
        if not self.is_available:
            return []
        
        try:
            # Build filter
            must_conditions = []
            
            if max_price is not None or min_price is not None:
                range_params = {}
                if max_price is not None:
                    range_params["lte"] = max_price
                if min_price is not None:
                    range_params["gte"] = min_price
                must_conditions.append(
                    FieldCondition(key="price", range=Range(**range_params))
                )
            
            if categories:
                must_conditions.append(
                    FieldCondition(key="category", match=MatchAny(any=categories))
                )
            
            if in_stock_only:
                must_conditions.append(
                    FieldCondition(key="in_stock", match=MatchValue(value=True))
                )
            
            if min_rating is not None:
                must_conditions.append(
                    FieldCondition(key="rating", range=Range(gte=min_rating))
                )
            
            qdrant_filter = Filter(must=must_conditions) if must_conditions else None
            
            # Search using named vector "image"
            results = self._client.search(
                collection_name=self.collection_name,
                query_vector=("image", image_vector),
                query_filter=qdrant_filter,
                limit=limit,
                with_payload=True
            )
            
            return [self._to_search_result(r) for r in results]
            
        except Exception as e:
            print(f"⚠️ Image search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def search_by_text(
        self,
        text_vector: List[float],
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        categories: Optional[List[str]] = None,
        category: Optional[str] = None,
        brands: Optional[List[str]] = None,
        in_stock_only: bool = True,
        conditions: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Search products by text similarity using CLIP text embeddings.
        
        Args:
            text_vector: 512-dim CLIP text embedding
            max_price: Maximum price filter
            min_price: Minimum price filter
            categories: Multiple category filter (OR)
            category: Single category filter
            brands: Brand filter (OR)
            in_stock_only: Only show in-stock items
            conditions: Condition filter (new, refurbished, etc.)
            min_rating: Minimum rating filter
            limit: Max results
            
        Returns:
            Products matching the text query
        """
        if not self.is_available:
            return []
        
        try:
            # Build filter
            must_conditions = []
            
            # Price range filter
            if max_price is not None or min_price is not None:
                range_params = {}
                if max_price is not None:
                    range_params["lte"] = max_price
                if min_price is not None:
                    range_params["gte"] = min_price
                must_conditions.append(
                    FieldCondition(key="price", range=Range(**range_params))
                )
            
            # Single category filter
            if category:
                must_conditions.append(
                    FieldCondition(key="category", match=MatchValue(value=category))
                )
            
            # Multiple categories (OR)
            if categories and len(categories) > 0:
                must_conditions.append(
                    FieldCondition(key="category", match=MatchAny(any=categories))
                )
            
            # Multiple brands (OR)
            if brands and len(brands) > 0:
                must_conditions.append(
                    FieldCondition(key="brand", match=MatchAny(any=brands))
                )
            
            if in_stock_only:
                must_conditions.append(
                    FieldCondition(key="in_stock", match=MatchValue(value=True))
                )
            
            # Conditions filter
            if conditions and len(conditions) > 0:
                must_conditions.append(
                    FieldCondition(key="condition", match=MatchAny(any=conditions))
                )
            
            # Rating filter
            if min_rating is not None:
                must_conditions.append(
                    FieldCondition(key="rating", range=Range(gte=min_rating))
                )
            
            qdrant_filter = Filter(must=must_conditions) if must_conditions else None
            
            # Search using named vector "text"
            results = self._client.search(
                collection_name=self.collection_name,
                query_vector=("text", text_vector),
                query_filter=qdrant_filter,
                limit=limit,
                with_payload=True
            )
            
            return [self._to_search_result(r) for r in results]
            
        except Exception as e:
            print(f"⚠️ Text search error: {e}")
            return []
    
    def hybrid_search(
        self,
        image_vector: Optional[List[float]] = None,
        text_vector: Optional[List[float]] = None,
        image_weight: float = 0.7,
        text_weight: float = 0.3,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        categories: Optional[List[str]] = None,
        in_stock_only: bool = True,
        min_rating: Optional[float] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """
        Hybrid search combining image and text vectors.
        
        When user provides both an image and text query, 
        combines results using weighted fusion.
        
        Args:
            image_vector: CLIP image embedding (optional)
            text_vector: CLIP text embedding (optional)
            image_weight: Weight for image results (0-1)
            text_weight: Weight for text results (0-1)
            max_price: Maximum price filter
            min_price: Minimum price filter
            categories: Category filter
            in_stock_only: Only in-stock items
            min_rating: Minimum rating filter
            limit: Max results
            
        Returns:
            Fused search results
        """
        if not self.is_available:
            return []
        
        if image_vector is None and text_vector is None:
            return []
        
        # If only one modality, use single search
        if image_vector is None:
            return self.search_by_text(
                text_vector=text_vector,
                max_price=max_price,
                min_price=min_price,
                categories=categories,
                in_stock_only=in_stock_only,
                min_rating=min_rating,
                limit=limit
            )
        
        if text_vector is None:
            return self.search_by_image(
                image_vector=image_vector,
                max_price=max_price,
                min_price=min_price,
                categories=categories,
                in_stock_only=in_stock_only,
                min_rating=min_rating,
                limit=limit
            )
        
        # Perform both searches
        image_results = self.search_by_image(
            image_vector=image_vector,
            max_price=max_price,
            min_price=min_price,
            categories=categories,
            in_stock_only=in_stock_only,
            min_rating=min_rating,
            limit=limit*2
        )
        text_results = self.search_by_text(
            text_vector=text_vector,
            max_price=max_price,
            min_price=min_price,
            categories=categories,
            in_stock_only=in_stock_only,
            min_rating=min_rating,
            limit=limit*2
        )
        
        # Fuse results using weighted reciprocal rank fusion
        product_scores = {}
        
        for rank, r in enumerate(image_results):
            pid = r.product_id
            rrf_score = image_weight / (rank + 60)  # k=60 for RRF
            product_scores[pid] = product_scores.get(pid, {'result': r, 'score': 0})
            product_scores[pid]['score'] += rrf_score
        
        for rank, r in enumerate(text_results):
            pid = r.product_id
            rrf_score = text_weight / (rank + 60)
            if pid not in product_scores:
                product_scores[pid] = {'result': r, 'score': 0}
            product_scores[pid]['score'] += rrf_score
        
        # Sort by fused score
        sorted_results = sorted(
            product_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        return [item['result'] for item in sorted_results[:limit]]
    
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
            rating_count=payload.get("review_count", 0),
            score=hit.score,
            condition=payload.get("condition", "new"),
            in_stock=payload.get("in_stock", True),
            features=payload.get("features", []),
            description=payload.get("description", "")
        )


# Singleton for multimodal search
_multimodal_search = None


def get_multimodal_search() -> MultimodalQdrantSearch:
    """Get singleton multimodal search instance."""
    global _multimodal_search
    if _multimodal_search is None:
        _multimodal_search = MultimodalQdrantSearch()
    return _multimodal_search


# Alias for unified access
def get_unified_search() -> MultimodalQdrantSearch:
    """
    Get the unified search instance (uses products_multimodal).
    This is the recommended way to get search - works for text, image, and hybrid.
    """
    return get_multimodal_search()


if __name__ == "__main__":
    print("🧪 Testing Unified Qdrant Search...")
    
    # Test the unified multimodal search
    search = get_unified_search()
    
    if search.is_available:
        print(f"\n✅ Unified multimodal search ready!")
        print(f"   Collection: {search.collection_name}")
        
        # Test text encoding
        print("\n📝 Testing text encoding with CLIP...")
        test_vec = search.encode_text("gaming laptop")
        if test_vec:
            print(f"   ✅ Text encoded: {len(test_vec)} dimensions")
        else:
            print("   ⚠️ Text encoding not available")
    else:
        print("\n⚠️ Multimodal search not available")
        print("   Run: python scripts/upload_multimodal_to_qdrant.py")
    
    # Also show legacy search status
    print("\n📊 Legacy search (for reference):")
    legacy = QdrantSearch()
    if legacy.is_available:
        info = legacy.collection_info()
        print(f"   products_main: {info.get('points_count', 0)} points")
