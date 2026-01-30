"""
Visual Search using CLIP
Encode images and find similar products
"""
import os
import base64
import numpy as np
from typing import Optional, Union, List, Dict, Any
from io import BytesIO

# Lazy load CLIP to avoid import time
_clip_model = None
_clip_processor = None
_clip_available = None


def _check_clip_available() -> bool:
    """Check if CLIP dependencies are available."""
    global _clip_available
    if _clip_available is None:
        try:
            import torch
            from transformers import CLIPProcessor, CLIPModel
            from PIL import Image
            _clip_available = True
        except ImportError:
            _clip_available = False
    return _clip_available


def _load_clip():
    """Lazy load CLIP model."""
    global _clip_model, _clip_processor
    
    if _clip_model is None:
        if not _check_clip_available():
            print("⚠️ CLIP dependencies not available")
            print("   Install with: pip install transformers torch pillow")
            return None, None
        
        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch
            
            print("🔄 Loading CLIP model (openai/clip-vit-base-patch32)...")
            model_name = "openai/clip-vit-base-patch32"
            
            _clip_processor = CLIPProcessor.from_pretrained(model_name)
            _clip_model = CLIPModel.from_pretrained(model_name)
            
            # Use GPU if available
            if torch.cuda.is_available():
                _clip_model = _clip_model.cuda()
                print("✅ CLIP loaded on GPU!")
            else:
                print("✅ CLIP loaded on CPU")
                
        except Exception as e:
            print(f"⚠️ CLIP loading failed: {e}")
            return None, None
    
    return _clip_model, _clip_processor


class VisualSearchService:
    """
    Visual search using CLIP embeddings.
    
    Supports:
    - Image file upload (bytes)
    - Base64 encoded images
    - PIL Image objects
    
    CLIP encodes both images and text into the same embedding space,
    enabling cross-modal similarity search.
    """
    
    def __init__(self):
        self._model = None
        self._processor = None
        self._dimension = 512  # CLIP ViT-B/32 output dimension
        self._initialized = False
    
    def _ensure_loaded(self):
        """Ensure CLIP is loaded."""
        if not self._initialized:
            self._model, self._processor = _load_clip()
            self._initialized = True
    
    @property
    def model(self):
        self._ensure_loaded()
        return self._model
    
    @property
    def processor(self):
        self._ensure_loaded()
        return self._processor
    
    @property
    def is_available(self) -> bool:
        """Check if CLIP is available and loaded."""
        if not _check_clip_available():
            return False
        self._ensure_loaded()
        return self._model is not None
    
    @property
    def dimension(self) -> int:
        """CLIP embedding dimension."""
        return self._dimension
    
    def encode_image(self, image_data: Union[bytes, str, Any]) -> Optional[np.ndarray]:
        """
        Encode an image into CLIP embedding space.
        
        Args:
            image_data: Raw bytes, base64 string, or PIL Image
            
        Returns:
            512-dim L2-normalized numpy array, or None on error
        """
        if not self.is_available:
            print("⚠️ CLIP not available for visual search")
            return None
        
        try:
            from PIL import Image
            import torch
            
            # Handle different input types
            if hasattr(image_data, 'convert'):
                # Already a PIL Image
                image = image_data.convert('RGB')
            elif isinstance(image_data, str):
                # Base64 string
                # Remove data URL prefix if present (e.g., "data:image/png;base64,...")
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                image = Image.open(BytesIO(image_bytes)).convert('RGB')
            elif isinstance(image_data, bytes):
                # Raw bytes
                image = Image.open(BytesIO(image_data)).convert('RGB')
            else:
                print(f"⚠️ Unsupported image type: {type(image_data)}")
                return None
            
            # Process with CLIP
            inputs = self.processor(images=image, return_tensors="pt")
            
            # Move to GPU if model is on GPU
            if next(self.model.parameters()).is_cuda:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Get image features
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
            
            # L2 normalize
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            # Convert to numpy
            embedding = image_features.cpu().numpy().flatten()
            
            return embedding
            
        except Exception as e:
            print(f"⚠️ Image encoding error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def encode_text(self, text: str) -> Optional[np.ndarray]:
        """
        Encode text into CLIP embedding space.
        
        Useful for text-to-image similarity or combining modalities.
        
        Args:
            text: Text string to encode
            
        Returns:
            512-dim L2-normalized numpy array
        """
        if not self.is_available:
            return None
        
        try:
            import torch
            
            inputs = self.processor(text=[text], return_tensors="pt", padding=True)
            
            if next(self.model.parameters()).is_cuda:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
            
            # L2 normalize
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            return text_features.cpu().numpy().flatten()
            
        except Exception as e:
            print(f"⚠️ Text encoding error: {e}")
            return None
    
    def encode_batch_images(self, images: List[Any]) -> Optional[np.ndarray]:
        """
        Encode multiple images in batch for efficiency.
        
        Args:
            images: List of PIL Images, bytes, or base64 strings
            
        Returns:
            Array of shape (N, 512) with L2-normalized embeddings
        """
        if not self.is_available:
            return None
        
        try:
            from PIL import Image
            import torch
            
            pil_images = []
            for img_data in images:
                if hasattr(img_data, 'convert'):
                    pil_images.append(img_data.convert('RGB'))
                elif isinstance(img_data, str):
                    if ',' in img_data:
                        img_data = img_data.split(',')[1]
                    img_bytes = base64.b64decode(img_data)
                    pil_images.append(Image.open(BytesIO(img_bytes)).convert('RGB'))
                elif isinstance(img_data, bytes):
                    pil_images.append(Image.open(BytesIO(img_data)).convert('RGB'))
            
            if not pil_images:
                return None
            
            inputs = self.processor(images=pil_images, return_tensors="pt")
            
            if next(self.model.parameters()).is_cuda:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
            
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy()
            
        except Exception as e:
            print(f"⚠️ Batch image encoding error: {e}")
            return None
    
    def compute_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two L2-normalized vectors.
        
        For normalized vectors, dot product equals cosine similarity.
        """
        if vec1 is None or vec2 is None:
            return 0.0
        return float(np.dot(vec1.flatten(), vec2.flatten()))
    
    def find_similar_products(
        self,
        image_vec: np.ndarray,
        product_images: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find products with similar images.
        
        Args:
            image_vec: Query image embedding (512-dim)
            product_images: List of dicts with 'product_id' and 'image_embedding'
            top_k: Number of results to return
            
        Returns:
            Top-k similar products sorted by similarity
        """
        if image_vec is None or not product_images:
            return []
        
        scored = []
        for product in product_images:
            prod_vec = product.get('image_embedding')
            if prod_vec is not None:
                similarity = self.compute_similarity(image_vec, prod_vec)
                scored.append({
                    **product,
                    'visual_similarity': similarity
                })
        
        # Sort by similarity
        scored.sort(key=lambda x: x.get('visual_similarity', 0), reverse=True)
        
        return scored[:top_k]


# Singleton
_visual_service = None


def get_visual_service() -> VisualSearchService:
    """Get singleton visual search service."""
    global _visual_service
    if _visual_service is None:
        _visual_service = VisualSearchService()
    return _visual_service


if __name__ == "__main__":
    print("🧪 Testing Visual Search Service...")
    
    service = VisualSearchService()
    
    print(f"   CLIP available: {_check_clip_available()}")
    
    if service.is_available:
        print("✅ CLIP model loaded successfully!")
        
        # Test text encoding (since we may not have an image file)
        text_vec = service.encode_text("a red gaming laptop with RGB keyboard")
        if text_vec is not None:
            print(f"✅ Text embedding shape: {text_vec.shape}")
            print(f"   Dimension: {service.dimension}")
            print(f"   First 5 values: {text_vec[:5]}")
            print(f"   L2 norm: {np.linalg.norm(text_vec):.4f} (should be ~1.0)")
        
        # Test similarity between related concepts
        vec1 = service.encode_text("gaming laptop")
        vec2 = service.encode_text("gaming computer")
        vec3 = service.encode_text("kitchen blender")
        
        if all(v is not None for v in [vec1, vec2, vec3]):
            sim_related = service.compute_similarity(vec1, vec2)
            sim_unrelated = service.compute_similarity(vec1, vec3)
            print(f"\n📊 Similarity tests:")
            print(f"   'gaming laptop' vs 'gaming computer': {sim_related:.4f}")
            print(f"   'gaming laptop' vs 'kitchen blender': {sim_unrelated:.4f}")
        
        print("\n✅ Visual search service ready!")
    else:
        print("⚠️ CLIP not available")
        print("   Install with: pip install transformers torch pillow")
