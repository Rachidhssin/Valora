"""
Agent Tools
Tools for the Budget Pathfinder Agent to find affordability paths
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import random


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    data: Dict[str, Any]
    message: str


class AgentTools:
    """
    Collection of tools for the Budget Pathfinder Agent.
    Each tool helps find a way to make products more affordable.
    """
    
    def __init__(self, search_client=None, cache=None):
        """
        Initialize tools with optional dependencies.
        
        Args:
            search_client: QdrantSearch instance for product lookups
            cache: PostgreSQLCache instance for caching results
        """
        self.search = search_client
        self.cache = cache
    
    def check_cart_removals(self, current_cart: List[Dict], 
                           budget: float,
                           target_price: float) -> ToolResult:
        """
        Identify items that can be removed from cart to fit budget.
        
        Args:
            current_cart: List of products in cart
            budget: User's budget
            target_price: Price of desired product
            
        Returns:
            ToolResult with removal suggestions
        """
        if not current_cart:
            return ToolResult(
                success=False,
                data={},
                message="Cart is empty, no items to remove"
            )
        
        cart_total = sum(item.get('price', 0) for item in current_cart)
        gap = (cart_total + target_price) - budget
        
        if gap <= 0:
            return ToolResult(
                success=True,
                data={'gap': 0, 'suggestions': []},
                message="No gap - product fits within budget with current cart"
            )
        
        # Find items that could be removed
        removable = []
        for item in current_cart:
            item_price = item.get('price', 0)
            item_utility = item.get('utility', 0.5)
            
            # Calculate removal value (how much it helps vs utility lost)
            if gap > 0:
                removal_efficiency = item_price / gap if item_price <= gap else 1.0
                removable.append({
                    'item': item,
                    'price': item_price,
                    'utility_loss': item_utility,
                    'closes_gap': item_price >= gap,
                    'remaining_gap': max(0, gap - item_price)
                })
        
        # Sort by efficiency (prefer removing lower utility items that close gap)
        removable.sort(key=lambda x: (-x['closes_gap'], x['utility_loss']))
        
        return ToolResult(
            success=True,
            data={
                'gap': round(gap, 2),
                'suggestions': removable[:3],  # Top 3 suggestions
                'cart_total': round(cart_total, 2)
            },
            message=f"Found {len(removable)} items that could be removed to close ${gap:.2f} gap"
        )
    
    def find_refurb_alternatives(self, product: Dict,
                                 max_price: Optional[float] = None) -> ToolResult:
        """
        Find refurbished or open-box alternatives to reduce price.
        
        Args:
            product: Original product dict
            max_price: Maximum price for alternative
            
        Returns:
            ToolResult with alternative products
        """
        original_price = product.get('price', 0)
        category = product.get('category', '')
        brand = product.get('brand', '')
        
        # Simulate finding alternatives (in production, would query Qdrant)
        # Refurbished typically 20-35% cheaper, open-box 10-20% cheaper
        
        alternatives = []
        
        # Refurbished option
        refurb_price = original_price * random.uniform(0.65, 0.80)
        if max_price is None or refurb_price <= max_price:
            alternatives.append({
                'type': 'refurbished',
                'name': f"{product.get('name', 'Product')} (Refurbished)",
                'price': round(refurb_price, 2),
                'savings': round(original_price - refurb_price, 2),
                'savings_percent': round((1 - refurb_price/original_price) * 100, 1),
                'warranty': '90-day limited warranty',
                'condition_notes': 'Tested and certified, may have minor cosmetic wear',
                'risk_level': 'low'
            })
        
        # Open-box option
        openbox_price = original_price * random.uniform(0.80, 0.90)
        if max_price is None or openbox_price <= max_price:
            alternatives.append({
                'type': 'open-box',
                'name': f"{product.get('name', 'Product')} (Open Box)",
                'price': round(openbox_price, 2),
                'savings': round(original_price - openbox_price, 2),
                'savings_percent': round((1 - openbox_price/original_price) * 100, 1),
                'warranty': 'Full manufacturer warranty',
                'condition_notes': 'Returned unused, original packaging opened',
                'risk_level': 'very low'
            })
        
        # Lower-tier alternative in same category
        if category:
            lower_price = original_price * random.uniform(0.50, 0.70)
            if max_price is None or lower_price <= max_price:
                alternatives.append({
                    'type': 'alternative_model',
                    'name': f"Similar {category.rstrip('s').title()} - Budget Model",
                    'price': round(lower_price, 2),
                    'savings': round(original_price - lower_price, 2),
                    'savings_percent': round((1 - lower_price/original_price) * 100, 1),
                    'warranty': 'Full manufacturer warranty',
                    'condition_notes': 'New, lower specifications',
                    'risk_level': 'none'
                })
        
        if alternatives:
            return ToolResult(
                success=True,
                data={'alternatives': alternatives, 'original_price': original_price},
                message=f"Found {len(alternatives)} alternatives with savings up to ${max(a['savings'] for a in alternatives):.2f}"
            )
        else:
            return ToolResult(
                success=False,
                data={},
                message="No alternatives found within price constraints"
            )
    
    def suggest_financing(self, price: float,
                         user_context: Optional[Dict] = None) -> ToolResult:
        """
        Suggest financing options to spread cost over time.
        
        Args:
            price: Total price to finance
            user_context: AFIG context for personalization
            
        Returns:
            ToolResult with financing options
        """
        credit_tier = 'good'
        if user_context:
            credit_tier = user_context.get('credit_score_tier', 'good')
        
        options = []
        
        # Buy Now Pay Later (Affirm/Klarna style)
        if price >= 50:
            for months in [3, 6, 12]:
                if months == 3:
                    apr = 0  # 0% for 3 months often available
                elif months == 6:
                    apr = 0.10 if credit_tier in ['good', 'excellent'] else 0.15
                else:
                    apr = 0.15 if credit_tier in ['good', 'excellent'] else 0.20
                
                monthly = (price * (1 + apr)) / months
                total_cost = monthly * months
                
                options.append({
                    'provider': 'Pay in Installments',
                    'months': months,
                    'monthly_payment': round(monthly, 2),
                    'apr': f"{apr*100:.0f}%",
                    'total_cost': round(total_cost, 2),
                    'extra_cost': round(total_cost - price, 2),
                    'approval_likelihood': 'high' if credit_tier in ['good', 'excellent'] else 'medium'
                })
        
        # Store credit card
        if price >= 200:
            options.append({
                'provider': 'Store Credit Card',
                'months': 18,
                'monthly_payment': round(price / 18, 2),
                'apr': '0% promotional (18 months)',
                'total_cost': price,
                'extra_cost': 0,
                'approval_likelihood': 'medium' if credit_tier in ['fair', 'good', 'excellent'] else 'low',
                'note': 'Requires new credit application'
            })
        
        # PayPal Credit
        if price >= 99:
            options.append({
                'provider': 'PayPal Pay in 4',
                'months': 1.5,  # 6 weeks
                'monthly_payment': round(price / 4, 2),
                'apr': '0%',
                'total_cost': price,
                'extra_cost': 0,
                'approval_likelihood': 'high',
                'note': '4 payments every 2 weeks, no interest'
            })
        
        if options:
            best_option = min(options, key=lambda x: x['extra_cost'])
            return ToolResult(
                success=True,
                data={'options': options, 'recommended': best_option},
                message=f"Found {len(options)} financing options, best saves ${(price - best_option['total_cost']):.2f}"
            )
        else:
            return ToolResult(
                success=False,
                data={},
                message="Price too low for financing options"
            )
    
    def find_bundle_discounts(self, products: List[Dict],
                              category: str) -> ToolResult:
        """
        Find bundle or combo deals for multiple products.
        
        Args:
            products: Products being considered
            category: Primary category to match bundles
            
        Returns:
            ToolResult with bundle deals
        """
        total_price = sum(p.get('price', 0) for p in products)
        
        bundles = []
        
        # Simulate bundle discovery
        if len(products) >= 2:
            # Multi-item discount
            discount_percent = min(15, 5 + len(products) * 2)  # 7-15% based on items
            bundle_price = total_price * (1 - discount_percent/100)
            
            bundles.append({
                'type': 'multi_item_discount',
                'name': f'Buy {len(products)} Together & Save',
                'original_total': round(total_price, 2),
                'bundle_price': round(bundle_price, 2),
                'savings': round(total_price - bundle_price, 2),
                'discount_percent': discount_percent
            })
        
        # Category-specific bundles
        bundle_combos = {
            'laptops': ['mice', 'keyboards', 'monitors'],
            'gpus': ['monitors', 'keyboards'],
            'desks': ['chairs', 'monitors'],
            'monitors': ['webcams', 'speakers']
        }
        
        if category in bundle_combos:
            combo_categories = bundle_combos[category]
            bundles.append({
                'type': 'category_bundle',
                'name': f'{category.title()} Bundle Deal',
                'includes': combo_categories[:2],
                'estimated_savings': f"10-20% when bundled with {', '.join(combo_categories[:2])}",
                'note': 'Add qualifying items to see exact discount'
            })
        
        if bundles:
            return ToolResult(
                success=True,
                data={'bundles': bundles},
                message=f"Found {len(bundles)} bundle deals with potential savings"
            )
        else:
            return ToolResult(
                success=False,
                data={},
                message="No bundle deals available for current selection"
            )
    
    def check_upcoming_sales(self, product: Dict,
                            days_willing_to_wait: int = 30) -> ToolResult:
        """
        Check for upcoming sales or price drops.
        
        Args:
            product: Product to check
            days_willing_to_wait: How long user can wait
            
        Returns:
            ToolResult with sale predictions
        """
        category = product.get('category', '')
        price = product.get('price', 0)
        
        # Simulated sale calendar (in production, would use price history API)
        upcoming_sales = []
        
        # Check for known sale events
        import datetime
        today = datetime.date.today()
        
        sale_events = [
            {'name': 'Flash Sale', 'days_away': random.randint(3, 14), 'discount': '10-15%'},
            {'name': 'Monthly Deal', 'days_away': random.randint(7, 21), 'discount': '15-25%'},
        ]
        
        # Prime Day (July) or Black Friday (November)
        if today.month in [6, 10]:  # Approaching big sales
            sale_events.append({
                'name': 'Black Friday' if today.month == 10 else 'Prime Day',
                'days_away': random.randint(20, 40),
                'discount': '25-40%'
            })
        
        for event in sale_events:
            if event['days_away'] <= days_willing_to_wait:
                discount_range = event['discount'].split('-')
                avg_discount = (int(discount_range[0]) + int(discount_range[1])) / 2 / 100
                predicted_price = price * (1 - avg_discount)
                
                upcoming_sales.append({
                    'event': event['name'],
                    'days_until': event['days_away'],
                    'expected_discount': event['discount'],
                    'predicted_price': round(predicted_price, 2),
                    'potential_savings': round(price - predicted_price, 2),
                    'confidence': 'medium' if event['days_away'] > 20 else 'high'
                })
        
        # Price drop prediction based on category
        if category in ['gpus', 'laptops']:
            upcoming_sales.append({
                'event': 'New Model Release',
                'days_until': random.randint(30, 60),
                'expected_discount': '15-30%',
                'predicted_price': round(price * 0.78, 2),
                'potential_savings': round(price * 0.22, 2),
                'confidence': 'low',
                'note': 'Older models often discounted when new versions launch'
            })
        
        # Filter by wait tolerance
        valid_sales = [s for s in upcoming_sales if s['days_until'] <= days_willing_to_wait]
        
        if valid_sales:
            best_sale = max(valid_sales, key=lambda x: x['potential_savings'])
            return ToolResult(
                success=True,
                data={'upcoming_sales': valid_sales, 'best_option': best_sale},
                message=f"Found {len(valid_sales)} upcoming sales, best could save ${best_sale['potential_savings']:.2f}"
            )
        else:
            return ToolResult(
                success=False,
                data={},
                message=f"No significant sales predicted in next {days_willing_to_wait} days"
            )
    
    def get_tool_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all available tools for the agent."""
        return {
            'check_cart_removals': 'Identify items in cart that could be removed to fit budget',
            'find_refurb_alternatives': 'Find refurbished or open-box alternatives at lower prices',
            'suggest_financing': 'Get financing options like buy-now-pay-later or installment plans',
            'find_bundle_discounts': 'Find bundle deals when buying multiple items together',
            'check_upcoming_sales': 'Check for upcoming sales or predicted price drops'
        }


if __name__ == "__main__":
    print("🧪 Testing Agent Tools...")
    
    tools = AgentTools()
    
    # Test product
    product = {
        'id': 'prod_001',
        'name': 'ASUS ROG Laptop RTX 4070',
        'category': 'laptops',
        'brand': 'ASUS',
        'price': 1499
    }
    
    # Test cart
    cart = [
        {'id': 'cart_1', 'name': 'Gaming Mouse', 'price': 89, 'utility': 0.7},
        {'id': 'cart_2', 'name': 'Mechanical Keyboard', 'price': 149, 'utility': 0.8},
        {'id': 'cart_3', 'name': '27" Monitor', 'price': 349, 'utility': 0.85}
    ]
    
    print("\n📊 Tool: check_cart_removals")
    result = tools.check_cart_removals(cart, budget=1200, target_price=product['price'])
    print(f"   {result.message}")
    print(f"   Gap: ${result.data.get('gap', 0):.2f}")
    
    print("\n📊 Tool: find_refurb_alternatives")
    result = tools.find_refurb_alternatives(product, max_price=1200)
    print(f"   {result.message}")
    for alt in result.data.get('alternatives', [])[:2]:
        print(f"   - {alt['type']}: ${alt['price']} (save ${alt['savings']})")
    
    print("\n📊 Tool: suggest_financing")
    result = tools.suggest_financing(product['price'])
    print(f"   {result.message}")
    rec = result.data.get('recommended', {})
    print(f"   Recommended: {rec.get('provider')} - ${rec.get('monthly_payment')}/mo for {rec.get('months')} months")
    
    print("\n📊 Tool: check_upcoming_sales")
    result = tools.check_upcoming_sales(product, days_willing_to_wait=30)
    print(f"   {result.message}")
    
    print("\n✅ Agent tools test complete!")
