"""
LLM Explainer
Generates personalized product explanations using Groq LLM
"""
import os
import re
import asyncio
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Import cache (use try/except for standalone testing)
try:
    from retrieval.cache import PostgreSQLCache
except ImportError:
    PostgreSQLCache = None


class LLMExplainer:
    """
    Generates personalized product explanations using Groq LLM.
    Includes caching and hallucination verification.
    """
    
    MODEL = "llama-3.1-8b-instant"
    CACHE_TTL = 86400  # 24 hours
    
    def __init__(self, cache_enabled: bool = True):
        self._client = None
        self._cache = None
        
        if GROQ_AVAILABLE:
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                self._client = Groq(api_key=api_key)
        
        if cache_enabled and PostgreSQLCache:
            try:
                self._cache = PostgreSQLCache(table_name="explanation_cache")
            except:
                pass
    
    async def explain(self, product: Dict[str, Any], 
                     user_context: Dict[str, Any]) -> str:
        """
        Generate personalized explanation for why a product fits the user.
        
        Args:
            product: Product dict with name, price, category, features, etc.
            user_context: AFIG reconciled context with archetype, preferences
            
        Returns:
            2-3 sentence explanation
        """
        # Build cache key
        product_id = product.get('product_id', product.get('id', 'unknown'))
        archetype = user_context.get('archetype', 'default')
        cache_key = f"explain:{product_id}:{archetype}"
        
        # Check cache
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached.get('explanation', self._fallback_template(product, user_context))
        
        # Generate with LLM
        if self._client:
            explanation = await self._generate_llm_explanation(product, user_context)
            
            # Verify and cache
            if self._verify_explanation(explanation, product):
                if self._cache:
                    self._cache.set(cache_key, {'explanation': explanation}, ttl=self.CACHE_TTL)
                return explanation
        
        # Fallback to template
        return self._fallback_template(product, user_context)
    
    async def explain_batch(self, products: list, 
                           user_context: Dict[str, Any]) -> list:
        """Generate explanations for multiple products."""
        tasks = [self.explain(p, user_context) for p in products]
        return await asyncio.gather(*tasks)
    
    async def _generate_llm_explanation(self, product: Dict, 
                                        user_context: Dict) -> str:
        """Generate explanation using Groq LLM."""
        archetype = user_context.get('archetype', 'general')
        price = product.get('price', 0)
        name = product.get('name', 'This product')
        category = product.get('category', 'product')
        features = product.get('features', [])
        rating = product.get('rating', 4.0)
        
        archetype_context = {
            'budget_conscious': 'looking for the best value and price efficiency',
            'quality_seeker': 'wanting premium quality and top performance',
            'convenience_buyer': 'needing a quick, reliable purchase',
            'early_adopter': 'interested in the latest technology and features',
            'value_balanced': 'seeking a good balance of quality and price'
        }
        
        user_goal = archetype_context.get(archetype, 'shopping for quality products')
        features_text = ', '.join(features[:3]) if features else 'quality components'
        
        prompt = f"""Write a brief, personalized product recommendation (2 sentences max).

Product: {name}
Price: ${price:.2f}
Category: {category}
Key Features: {features_text}
Rating: {rating}/5

Shopper profile: A customer who is {user_goal}.

Requirements:
1. Mention the exact price (${price:.2f}) once
2. Highlight why it fits their shopping style
3. Be specific about one key feature or benefit
4. Keep it under 50 words
5. Sound helpful, not salesy

Write the recommendation:"""

        try:
            response = self._client.chat.completions.create(
                model=self.MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"⚠️ LLM explanation error: {e}")
            return self._fallback_template(product, user_context)
    
    def _verify_explanation(self, explanation: str, product: Dict) -> bool:
        """
        Verify explanation doesn't contain hallucinated prices or info.
        
        Returns:
            True if explanation is valid
        """
        if not explanation or len(explanation) < 20:
            return False
        
        actual_price = product.get('price', 0)
        
        # Extract mentioned prices
        price_pattern = r'\$\s*([\d,]+(?:\.\d{2})?)'
        mentioned_prices = re.findall(price_pattern, explanation)
        
        for price_str in mentioned_prices:
            try:
                mentioned = float(price_str.replace(',', ''))
                # Allow 10% tolerance for rounding
                if abs(mentioned - actual_price) > actual_price * 0.1:
                    print(f"⚠️ Price hallucination detected: mentioned ${mentioned}, actual ${actual_price}")
                    return False
            except ValueError:
                continue
        
        # Check for common hallucination patterns
        hallucination_patterns = [
            r'best .* ever',
            r'#1 rated',
            r'guaranteed',
            r'risk-free',
            r'limited time',
            r'act now'
        ]
        
        explanation_lower = explanation.lower()
        for pattern in hallucination_patterns:
            if re.search(pattern, explanation_lower):
                return False
        
        return True
    
    def _fallback_template(self, product: Dict, user_context: Dict) -> str:
        """Generate explanation using templates when LLM unavailable."""
        name = product.get('name', 'This product')
        price = product.get('price', 0)
        category = product.get('category', 'product')
        rating = product.get('rating', 4.0)
        archetype = user_context.get('archetype', 'default')
        
        templates = {
            'budget_conscious': (
                f"The {name} offers excellent value at ${price:.2f}, "
                f"providing solid {category.rstrip('s')} functionality without breaking your budget. "
                f"With a {rating}/5 rating, it's a smart choice for cost-conscious shoppers."
            ),
            'quality_seeker': (
                f"The {name} at ${price:.2f} delivers premium {category.rstrip('s')} performance "
                f"that quality-focused buyers appreciate. "
                f"Its {rating}/5 rating reflects the exceptional build and features."
            ),
            'convenience_buyer': (
                f"Get the {name} at ${price:.2f} for a reliable, no-hassle {category.rstrip('s')} solution. "
                f"Highly rated at {rating}/5 and ready to ship quickly."
            ),
            'early_adopter': (
                f"The {name} features cutting-edge {category.rstrip('s')} technology at ${price:.2f}. "
                f"Perfect for tech enthusiasts wanting the latest innovations, with {rating}/5 user approval."
            ),
            'value_balanced': (
                f"The {name} at ${price:.2f} strikes the ideal balance of quality and price "
                f"for {category.rstrip('s')} shoppers. "
                f"A {rating}/5 rating confirms its all-around appeal."
            ),
            'default': (
                f"The {name} at ${price:.2f} is a solid {category.rstrip('s')} choice "
                f"with a {rating}/5 user rating. A reliable option worth considering."
            )
        }
        
        return templates.get(archetype, templates['default'])
    
    def explain_bundle(self, bundle: list, total_price: float,
                      user_context: Dict) -> str:
        """Generate explanation for a product bundle."""
        archetype = user_context.get('archetype', 'default')
        item_count = len(bundle)
        
        categories = set()
        for item in bundle:
            if hasattr(item, 'category'):
                categories.add(item.category)
            elif isinstance(item, dict):
                categories.add(item.get('category', ''))
        
        categories_text = ', '.join(c.rstrip('s') for c in categories if c)
        
        if archetype == 'budget_conscious':
            return (
                f"This {item_count}-item bundle gives you a complete {categories_text} setup "
                f"at ${total_price:.2f}—optimized for maximum value. "
                f"Each item was selected to deliver the best performance per dollar."
            )
        elif archetype == 'quality_seeker':
            return (
                f"Your curated {item_count}-piece {categories_text} bundle at ${total_price:.2f} "
                f"features top-rated components chosen for premium performance. "
                f"A cohesive setup that exceeds expectations."
            )
        else:
            return (
                f"This balanced {item_count}-item {categories_text} bundle at ${total_price:.2f} "
                f"combines quality and value. "
                f"Each piece complements the others for a seamless experience."
            )


# Async test
async def _test_explainer():
    print("🧪 Testing LLM Explainer...")
    
    explainer = LLMExplainer(cache_enabled=False)
    
    product = {
        'product_id': 'prod_001',
        'name': 'ASUS ROG Strix G16 Gaming Laptop',
        'price': 1399.99,
        'category': 'laptops',
        'features': ['RTX 4070', '16GB RAM', '144Hz Display'],
        'rating': 4.7
    }
    
    contexts = [
        {'archetype': 'budget_conscious'},
        {'archetype': 'quality_seeker'},
        {'archetype': 'value_balanced'}
    ]
    
    for ctx in contexts:
        print(f"\n📊 Archetype: {ctx['archetype']}")
        explanation = await explainer.explain(product, ctx)
        print(f"   {explanation}")
    
    # Test verification
    good_exp = f"The laptop at ${product['price']:.2f} offers great value."
    bad_exp = "This laptop at $999.99 is the best ever!"
    
    print(f"\n📊 Verification test:")
    print(f"   Good explanation valid: {explainer._verify_explanation(good_exp, product)}")
    print(f"   Bad explanation valid: {explainer._verify_explanation(bad_exp, product)}")
    
    print("\n✅ Explainer test complete!")


if __name__ == "__main__":
    asyncio.run(_test_explainer())
