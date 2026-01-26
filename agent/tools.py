"""
Agent Tools for Budget Pathfinder Agent
========================================
Collection of tools for finding creative affordability paths.

Each tool follows a standardized interface:
- Accepts: args (Dict), user_afig (Dict), current_cart (List), budget (float), gap (float)
- Returns: Dict with {viable, path_type, summary, action, trade_off, ...}

Tools:
1. check_cart_removals - Find optional items to remove from cart
2. check_income_projection - Calculate saving timeline based on income
3. check_installment_plans - Generate installment payment options
4. check_refurbished_alternatives - Search for refurbished/cheaper alternatives (Qdrant)
5. check_bundle_swaps - Find cheaper substitutes for cart items (Qdrant)
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# Import the existing QdrantSearch from retrieval module
try:
    from retrieval.qdrant_search import QdrantSearch, QDRANT_AVAILABLE
    from core.embeddings import EmbeddingService
    SEARCH_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    SEARCH_AVAILABLE = False
    print("⚠️ Retrieval/embeddings modules not available, product search disabled")

# Qdrant client for direct access if needed
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny, Range
except ImportError:
    pass


# Legacy compatibility - keep ToolResult for backward compat
@dataclass
class ToolResult:
    """Result from a tool execution (legacy compatibility)."""
    success: bool
    data: Dict[str, Any]
    message: str


@dataclass
class IncomeConfig:
    """Income tier configuration."""
    weekly_disposable: int
    savings_rate: float = 0.20  # 20% saveable
    
    @property
    def weekly_savings(self) -> float:
        return self.weekly_disposable * self.savings_rate
    
    @property
    def monthly_income(self) -> float:
        return self.weekly_disposable * 4
    
    @property
    def max_monthly_payment(self) -> float:
        """Max affordable monthly payment (20% of monthly income)."""
        return self.monthly_income * 0.20


# Item categories by "optional-ness" (higher = more optional, easier to remove)
CATEGORY_OPTIONALITY = {
    # Very optional - accessories
    "accessories": 0.9,
    "cables": 0.9,
    "adapters": 0.9,
    "usb_hubs": 0.85,
    "stands": 0.85,
    
    # Optional - peripherals
    "mice": 0.8,
    "keyboards": 0.75,
    "headsets": 0.75,
    "webcams": 0.7,
    "speakers": 0.7,
    "mousepads": 0.9,
    
    # Moderate - displays and storage
    "monitors": 0.5,
    "storage": 0.4,
    "memory": 0.35,
    
    # Core items - hard to remove
    "laptops": 0.1,
    "desktops": 0.1,
    "gpus": 0.15,
    "cpus": 0.15,
    "motherboards": 0.15,
    "cases": 0.2,
    "power_supplies": 0.2,
}


class AgentTools:
    """
    Collection of tools for the Budget Pathfinder Agent.
    Each tool helps find a creative way to make products affordable.
    
    All tools are async and return standardized results:
    {
        "viable": bool,           # Is this path realistic?
        "path_type": str,         # Type identifier
        "summary": str,           # One-line description
        "action": str,            # What user should do
        "trade_off": str,         # What they sacrifice
        ... (tool-specific fields)
    }
    
    Uses real data from:
    - Qdrant: Vector search for products
    - PostgreSQL: Product details (via QdrantSearch.enrich_results)
    """
    
    def __init__(self, qdrant_client: Optional[Any] = None, verbose: bool = False):
        """
        Initialize tools with dependencies.
        
        Args:
            qdrant_client: Optional QdrantClient for product search (legacy)
            verbose: Whether to print debug messages
        """
        self._qdrant = qdrant_client
        self.verbose = verbose
        
        # Use the existing QdrantSearch from retrieval module
        self._search_service: Optional[QdrantSearch] = None
        self._embedder: Optional[EmbeddingService] = None
        self._init_search()
        
        # Income tier configurations
        self.income_config = {
            "low": IncomeConfig(weekly_disposable=400),
            "medium": IncomeConfig(weekly_disposable=600),
            "high": IncomeConfig(weekly_disposable=1000),
        }
        
        # Standard installment periods (months)
        self.installment_periods = [3, 6, 12]
    
    def _init_search(self):
        """Initialize search service using existing modules."""
        if not SEARCH_AVAILABLE:
            if self.verbose:
                print("⚠️ Search service not available")
            return
        
        try:
            self._search_service = QdrantSearch(collection_name="products_main")
            self._embedder = EmbeddingService()
            if self.verbose:
                print("✅ Search service initialized")
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Search service init failed: {e}")
            self._search_service = None
            self._embedder = None
    
    @property
    def qdrant_available(self) -> bool:
        """Check if search service is available."""
        return self._search_service is not None and self._search_service.is_available
    
    # =========================================================================
    # TOOL 1: check_cart_removals
    # =========================================================================
    
    async def check_cart_removals(
        self,
        args: Dict[str, Any],
        user_afig: Dict[str, Any],
        current_cart: List[Dict[str, Any]],
        budget: float,
        gap: float,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Find items in current cart that could be removed to free budget.
        Prioritizes removing optional accessories over core items.
        
        Args:
            args: {min_savings_needed: float} - Dollar amount needed
            user_afig: User context from AFIG
            current_cart: List of cart items
            budget: User's budget
            gap: Current budget shortfall
        
        Returns:
            {
                "viable": bool,
                "path_type": "cart_removal",
                "summary": str,
                "savings": float,
                "action": str,
                "trade_off": str,
                "items_to_remove": List[Dict]
            }
        """
        try:
            min_savings = args.get("min_savings_needed", gap)
            
            # Edge case: empty cart
            if not current_cart:
                return {
                    "viable": False,
                    "path_type": "cart_removal",
                    "summary": "Cart is empty, no items to remove",
                    "savings": 0,
                    "action": "N/A",
                    "trade_off": "N/A",
                    "items_to_remove": []
                }
            
            # Find optional items (higher optionality score = more removable)
            removable_items = self._find_optional_items(current_cart)
            
            if not removable_items:
                return {
                    "viable": False,
                    "path_type": "cart_removal",
                    "summary": "No optional items found in cart",
                    "savings": 0,
                    "action": "N/A",
                    "trade_off": "N/A",
                    "items_to_remove": []
                }
            
            # Sort by optionality (prefer removing more optional items first)
            removable_items.sort(key=lambda x: (-x["optionality"], -x["price"]))
            
            # Find best combination to meet savings target
            items_to_remove = []
            total_savings = 0
            
            for item in removable_items:
                items_to_remove.append(item)
                total_savings += item["price"]
                
                if total_savings >= min_savings:
                    break
            
            # Check if we found enough savings
            if total_savings < min_savings * 0.5:  # Less than 50% of target
                return {
                    "viable": False,
                    "path_type": "cart_removal",
                    "summary": f"Removable items only save ${total_savings:.0f}, need ${min_savings:.0f}",
                    "savings": total_savings,
                    "action": "N/A",
                    "trade_off": "Insufficient savings from cart removals alone",
                    "items_to_remove": items_to_remove
                }
            
            # Build summary
            item_names = [item["name"] for item in items_to_remove]
            if len(item_names) == 1:
                summary = f"Remove {item_names[0]} (${items_to_remove[0]['price']:.0f}) to save ${total_savings:.0f}"
            else:
                summary = f"Remove {len(item_names)} items to save ${total_savings:.0f}"
            
            # Calculate impact
            covers_gap = total_savings >= gap
            
            return {
                "viable": True,
                "path_type": "cart_removal",
                "summary": summary,
                "savings": round(total_savings, 2),
                "action": f"Remove {len(items_to_remove)} item(s) from cart: {', '.join(item_names[:3])}{'...' if len(item_names) > 3 else ''}",
                "trade_off": f"No {', '.join([i['category'] for i in items_to_remove[:2]])}, but they're optional for now",
                "items_to_remove": items_to_remove,
                "covers_full_gap": covers_gap,
                "remaining_gap": max(0, gap - total_savings)
            }
        
        except Exception as e:
            return {
                "viable": False,
                "path_type": "cart_removal",
                "summary": f"Tool execution failed: {str(e)}",
                "error": str(e),
                "savings": 0,
                "action": "N/A",
                "trade_off": "N/A"
            }
    
    def _find_optional_items(self, cart: List[Dict]) -> List[Dict]:
        """Find items in cart that are optional/removable."""
        optional = []
        
        for item in cart:
            category = item.get("category", "").lower()
            is_optional = item.get("optional", False)
            optionality = CATEGORY_OPTIONALITY.get(category, 0.5)
            
            if is_optional:
                optionality = min(1.0, optionality + 0.2)
            
            if optionality >= 0.5 or is_optional:
                optional.append({
                    "name": item.get("name", "Unknown Item"),
                    "price": item.get("price", 0),
                    "category": category,
                    "optionality": optionality,
                    "product_id": item.get("product_id", item.get("id", "")),
                    "original_item": item
                })
        
        return optional
    
    # =========================================================================
    # TOOL 2: check_income_projection
    # =========================================================================
    
    async def check_income_projection(
        self,
        args: Dict[str, Any],
        user_afig: Dict[str, Any],
        budget: float = 0,
        gap: float = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Calculate how many weeks user needs to save to afford the gap.
        
        Args:
            args: {target_amount: float} - Dollar amount to save
            user_afig: User context with income_tier
        
        Returns:
            {
                "viable": bool,
                "path_type": "save_and_wait",
                "summary": str,
                "weeks": int,
                "weekly_amount": float,
                "total_saved": float,
                "action": str,
                "trade_off": str,
                "timeline": str
            }
        """
        try:
            target_amount = args.get("target_amount", gap)
            
            if target_amount <= 0:
                return {
                    "viable": True,
                    "path_type": "save_and_wait",
                    "summary": "No saving needed, already affordable",
                    "weeks": 0,
                    "weekly_amount": 0,
                    "total_saved": 0,
                    "action": "Purchase now",
                    "trade_off": "None"
                }
            
            income_tier = user_afig.get("income_tier", "medium")
            if income_tier not in self.income_config:
                income_tier = "medium"
            
            config = self.income_config[income_tier]
            weekly_savings = config.weekly_savings
            weeks_needed = int((target_amount / weekly_savings) + 0.99)
            
            if weeks_needed <= 4:
                viability = "high"
                viable = True
            elif weeks_needed <= 8:
                viability = "moderate"
                viable = True
            elif weeks_needed <= 12:
                viability = "marginal"
                viable = True
            else:
                viability = "low"
                viable = False
            
            target_date = datetime.now() + timedelta(weeks=weeks_needed)
            timeline = target_date.strftime("Ready to buy by %B %d, %Y")
            
            if viable:
                summary = f"Save ${weekly_savings:.0f}/week for {weeks_needed} weeks to afford this item"
                action = f"Set aside ${weekly_savings:.0f} per week starting next paycheck"
            else:
                summary = f"Would take {weeks_needed} weeks ({weeks_needed // 4} months) to save ${target_amount:.0f}"
                action = "Consider other options - waiting time is too long"
            
            return {
                "viable": viable,
                "path_type": "save_and_wait",
                "summary": summary,
                "weeks": weeks_needed,
                "weekly_amount": round(weekly_savings, 2),
                "total_saved": round(weeks_needed * weekly_savings, 2),
                "action": action,
                "trade_off": f"Wait {weeks_needed} weeks before purchasing",
                "timeline": timeline,
                "viability": viability,
                "income_tier": income_tier
            }
        
        except Exception as e:
            return {
                "viable": False,
                "path_type": "save_and_wait",
                "summary": f"Tool execution failed: {str(e)}",
                "error": str(e),
                "weeks": 0,
                "weekly_amount": 0,
                "action": "N/A",
                "trade_off": "N/A"
            }
    
    # =========================================================================
    # TOOL 3: check_installment_plans
    # =========================================================================
    
    async def check_installment_plans(
        self,
        args: Dict[str, Any],
        user_afig: Dict[str, Any],
        budget: float = 0,
        gap: float = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Find payment plan options to spread cost over time.
        
        Args:
            args: {product_price: float, max_monthly_payment?: float}
            user_afig: User context with income_tier
        
        Returns:
            {
                "viable": bool,
                "path_type": "installment",
                "summary": str,
                "plan": {months, monthly_payment, total_cost, total_interest},
                "action": str,
                "trade_off": str,
                "affordability": str
            }
        """
        try:
            product_price = args.get("product_price", 0)
            
            if product_price < 100:
                return {
                    "viable": False,
                    "path_type": "installment",
                    "summary": f"${product_price:.0f} is too low for installment plans - pay outright",
                    "action": "Pay full price",
                    "trade_off": "N/A"
                }
            
            income_tier = user_afig.get("income_tier", "medium")
            if income_tier not in self.income_config:
                income_tier = "medium"
            
            config = self.income_config[income_tier]
            max_monthly = args.get("max_monthly_payment") or config.max_monthly_payment
            max_monthly_stretched = max_monthly * 1.2
            
            options = []
            
            for months in self.installment_periods:
                if months == 3:
                    apr = 0.0
                elif months == 6:
                    apr = 0.05
                else:
                    apr = 0.10
                
                total_interest = product_price * apr * (months / 12)
                total_cost = product_price + total_interest
                monthly_payment = total_cost / months
                
                if monthly_payment <= max_monthly_stretched:
                    affordable = "within" if monthly_payment <= max_monthly else "stretch"
                    options.append({
                        "months": months,
                        "monthly_payment": round(monthly_payment, 2),
                        "total_cost": round(total_cost, 2),
                        "total_interest": round(total_interest, 2),
                        "apr": f"{apr*100:.0f}%",
                        "affordable": affordable
                    })
            
            if not options:
                return {
                    "viable": False,
                    "path_type": "installment",
                    "summary": f"No affordable installment plans for ${product_price:.0f}",
                    "action": "N/A",
                    "trade_off": f"Monthly payments would exceed ${max_monthly:.0f} budget",
                    "max_monthly": max_monthly
                }
            
            best_option = None
            for opt in options:
                if opt["affordable"] == "within":
                    best_option = opt
                    break
            
            if not best_option:
                best_option = options[0]
            
            summary = f"{best_option['months']}-month payment plan: ${best_option['monthly_payment']:.0f}/month"
            if best_option["affordable"] == "within":
                summary += " (affordable)"
            else:
                summary += " (slight stretch)"
            
            return {
                "viable": True,
                "path_type": "installment",
                "summary": summary,
                "plan": best_option,
                "all_options": options,
                "action": f"Apply for {best_option['months']}-month installment plan",
                "trade_off": f"Commit to ${best_option['monthly_payment']:.0f}/month for {best_option['months']} months",
                "affordability": f"Within your ${max_monthly:.0f}/month budget" if best_option["affordable"] == "within" else f"Stretches to ${best_option['monthly_payment']:.0f}/month (budget: ${max_monthly:.0f})",
                "income_tier": income_tier
            }
        
        except Exception as e:
            return {
                "viable": False,
                "path_type": "installment",
                "summary": f"Tool execution failed: {str(e)}",
                "error": str(e),
                "action": "N/A",
                "trade_off": "N/A"
            }
    
    # =========================================================================
    # TOOL 4: check_refurbished_alternatives
    # =========================================================================
    
    async def check_refurbished_alternatives(
        self,
        args: Dict[str, Any],
        user_afig: Dict[str, Any] = None,
        current_cart: List[Dict] = None,
        budget: float = 0,
        gap: float = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search for refurbished/open-box versions to save money.
        
        Args:
            args: {product_category: str, max_price: float, min_savings?: float}
        
        Returns:
            {
                "viable": bool,
                "path_type": "refurbished",
                "summary": str,
                "product": {name, price, condition, rating, warranty},
                "savings": float,
                "action": str,
                "trade_off": str,
                "quality_note": str
            }
        """
        try:
            category = args.get("product_category", "").lower()
            max_price = args.get("max_price", budget)
            min_savings = args.get("min_savings", 100)
            
            if not self.qdrant_available:
                return {
                    "viable": False,
                    "path_type": "refurbished",
                    "summary": "Database unavailable - cannot search for refurbished products",
                    "action": "N/A",
                    "trade_off": "N/A",
                    "savings": 0
                }
            
            products = await self._search_refurbished_qdrant(category, max_price)
            
            if not products:
                return {
                    "viable": False,
                    "path_type": "refurbished",
                    "summary": f"No refurbished {category} found within ${max_price:.0f}",
                    "action": "N/A",
                    "trade_off": "N/A",
                    "savings": 0
                }
            
            estimated_original = max_price + gap if gap > 0 else max_price * 1.3
            filtered = []
            
            for product in products:
                savings = estimated_original - product.get("price", 0)
                if savings >= min_savings:
                    product["estimated_savings"] = savings
                    filtered.append(product)
            
            if not filtered:
                return {
                    "viable": False,
                    "path_type": "refurbished",
                    "summary": f"Refurbished options don't save enough (min ${min_savings:.0f} needed)",
                    "action": "N/A",
                    "trade_off": "N/A",
                    "savings": 0
                }
            
            filtered.sort(key=lambda x: (-x.get("estimated_savings", 0), -x.get("rating", 0)))
            
            best = filtered[0]
            savings = best.get("estimated_savings", estimated_original - best.get("price", 0))
            
            condition = best.get("condition", "refurbished")
            if condition == "open-box":
                warranty = "Full manufacturer warranty"
                quality_note = "Opened but unused, original packaging"
            else:
                warranty = "1 year certified warranty"
                quality_note = "Professionally refurbished, tested and certified"
            
            summary = f"Buy {condition} {category.rstrip('s')} for ${best['price']:.0f} (save ${savings:.0f})"
            
            return {
                "viable": True,
                "path_type": "refurbished",
                "summary": summary,
                "product": {
                    "name": best.get("name", f"Refurbished {category.title()}"),
                    "price": round(best.get("price", 0), 2),
                    "condition": condition,
                    "rating": best.get("rating", 4.5),
                    "warranty": warranty,
                    "product_id": best.get("product_id", "")
                },
                "savings": round(savings, 2),
                "action": f"Purchase certified {condition} {category.rstrip('s')} instead",
                "trade_off": f"{condition.title()} vs brand new",
                "quality_note": quality_note
            }
        
        except Exception as e:
            return {
                "viable": False,
                "path_type": "refurbished",
                "summary": f"Tool execution failed: {str(e)}",
                "error": str(e),
                "action": "N/A",
                "trade_off": "N/A",
                "savings": 0
            }
    
    async def _search_refurbished_qdrant(
        self, category: str, max_price: float, min_rating: float = 3.5, limit: int = 10
    ) -> List[Dict]:
        """
        Search Qdrant for refurbished/open-box products using the existing QdrantSearch service.
        
        Uses semantic search via the retrieval module. Since Qdrant may not have
        payload indexes, we do filtering in Python after retrieving results.
        """
        if not self._search_service or not self._embedder:
            return []
        
        # Accessory keywords to filter out (not actual products)
        accessory_keywords = [
            "case", "cover", "stand", "bag", "sleeve", "adapter", "charger", 
            "cable", "protector", "skin", "sticker", "decal", "dock", "hub",
            "mount", "holder", "kit", "ram", "memory", "ssd", "hard drive",
            "keyboard", "mouse", "webcam", "headphones", "earbuds"
        ]
        
        # Minimum price thresholds for actual products (not accessories)
        min_price_thresholds = {
            "laptops": 300,
            "computers": 300,
            "smartphones": 150,
            "phones": 150,
            "tablets": 150,
            "monitors": 100,
            "gpus": 150,
            "cpus": 80,
        }
        min_product_price = min_price_thresholds.get(category.lower(), 100)
        
        try:
            # Build query text for semantic search - be more specific
            if category.lower() in ["laptops", "computers"]:
                query_text = f"refurbished laptop notebook computer macbook thinkpad dell hp renewed certified"
            else:
                query_text = f"refurbished {category} open-box certified renewed budget"
            
            query_vector = self._embedder.encode_query(query_text).tolist()
            
            # Search WITHOUT filters (to avoid index requirements), get more results
            results = self._search_service.search(
                query_vector=query_vector,
                limit=100,  # Get more to filter in Python
                filters=None  # No filters - filter in Python
            )
            
            # Enrich with PostgreSQL data if available
            if results:
                results = self._search_service.enrich_results(results)
            
            # Filter results in Python
            products = []
            for r in results:
                # Apply price filters - must be above minimum for this category
                if r.price < min_product_price or r.price > max_price:
                    continue
                if r.rating < min_rating:
                    continue
                
                name_lower = r.name.lower()
                
                # Skip if it's clearly an accessory
                is_accessory = any(kw in name_lower for kw in accessory_keywords)
                if is_accessory:
                    continue
                
                # Check if it's a refurbished/renewed item
                is_refurb = r.condition in ["refurbished", "open-box", "renewed"] or \
                           "refurbished" in name_lower or "open-box" in name_lower or \
                           "renewed" in name_lower or "(renewed)" in name_lower
                
                # For laptops, also check if it's actually a laptop
                if category.lower() in ["laptops", "computers"]:
                    is_laptop = any(kw in name_lower for kw in [
                        "macbook", "thinkpad", "latitude", "xps", "pavilion", 
                        "inspiron", "envy", "spectre", "surface", "ideapad",
                        "yoga", "chromebook", "notebook", "laptop"
                    ])
                    # Must be both a laptop AND have reasonable price
                    if not is_laptop:
                        continue
                
                products.append({
                    "product_id": r.product_id,
                    "name": r.name,
                    "price": r.price,
                    "condition": r.condition if r.condition else ("refurbished" if is_refurb else "new"),
                    "rating": r.rating,
                    "category": r.category
                })
                
                if len(products) >= limit:
                    break
            
            return products
        
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Refurbished search error: {e}")
            return []
    
    # =========================================================================
    # TOOL 5: check_bundle_swaps
    # =========================================================================
    
    async def check_bundle_swaps(
        self,
        args: Dict[str, Any],
        user_afig: Dict[str, Any] = None,
        current_cart: List[Dict] = None,
        budget: float = 0,
        gap: float = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Find cheaper alternatives for expensive items in cart.
        
        Args:
            args: {savings_target: float} - How much to save through swaps
            current_cart: List of cart items
        
        Returns:
            {
                "viable": bool,
                "path_type": "bundle_swap",
                "summary": str,
                "from_product": {name, price, performance_tier},
                "to_product": {name, price, performance_tier},
                "savings": float,
                "action": str,
                "trade_off": str,
                "recommendation": str
            }
        """
        try:
            savings_target = args.get("savings_target", gap)
            
            if not current_cart:
                return {
                    "viable": False,
                    "path_type": "bundle_swap",
                    "summary": "Cart is empty, no items to swap",
                    "action": "N/A",
                    "trade_off": "N/A",
                    "savings": 0
                }
            
            swappable_categories = ["laptops", "gpus", "monitors", "cpus", "desktops", "motherboards"]
            swappable_items = [
                item for item in current_cart
                if item.get("category", "").lower() in swappable_categories
            ]
            
            if not swappable_items:
                return {
                    "viable": False,
                    "path_type": "bundle_swap",
                    "summary": "No swappable items in cart (only accessories)",
                    "action": "N/A",
                    "trade_off": "N/A",
                    "savings": 0
                }
            
            swappable_items.sort(key=lambda x: -x.get("price", 0))
            
            most_expensive = swappable_items[0]
            category = most_expensive.get("category", "").lower()
            current_price = most_expensive.get("price", 0)
            
            target_max = current_price * 0.80
            target_min = current_price * 0.50
            
            if not self.qdrant_available:
                return {
                    "viable": False,
                    "path_type": "bundle_swap",
                    "summary": "Database unavailable - cannot search for alternatives",
                    "action": "N/A",
                    "trade_off": "N/A",
                    "savings": 0
                }
            
            alternatives = await self._search_alternatives_qdrant(category, target_max, target_min)
            
            if not alternatives:
                return {
                    "viable": False,
                    "path_type": "bundle_swap",
                    "summary": f"No suitable alternatives found for {most_expensive.get('name', category)}",
                    "action": "N/A",
                    "trade_off": "N/A",
                    "savings": 0
                }
            
            best_alt = None
            best_savings = 0
            
            for alt in alternatives:
                alt_price = alt.get("price", 0)
                savings = current_price - alt_price
                
                if savings >= savings_target * 0.70:
                    if alt.get("rating", 0) >= 4.0:
                        if savings > best_savings:
                            best_alt = alt
                            best_savings = savings
            
            if not best_alt:
                alternatives.sort(key=lambda x: current_price - x.get("price", 0), reverse=True)
                best_alt = alternatives[0]
                best_savings = current_price - best_alt.get("price", 0)
            
            if best_savings < min(savings_target * 0.70, 100):
                return {
                    "viable": False,
                    "path_type": "bundle_swap",
                    "summary": f"Swaps only save ${best_savings:.0f}, need ${savings_target:.0f}",
                    "action": "N/A",
                    "trade_off": "Insufficient savings from swaps",
                    "savings": best_savings
                }
            
            from_tier = self._get_performance_tier(current_price, category)
            to_tier = self._get_performance_tier(best_alt.get("price", 0), category)
            perf_diff = self._calculate_perf_difference(from_tier, to_tier)
            
            summary = f"Swap {most_expensive.get('name', category)} (${current_price:.0f}) for {best_alt.get('name', '')} (${best_alt.get('price', 0):.0f}), save ${best_savings:.0f}"
            
            return {
                "viable": True,
                "path_type": "bundle_swap",
                "summary": summary,
                "from_product": {
                    "name": most_expensive.get("name", "Current Item"),
                    "price": round(current_price, 2),
                    "performance_tier": from_tier,
                    "category": category
                },
                "to_product": {
                    "name": best_alt.get("name", "Alternative"),
                    "price": round(best_alt.get("price", 0), 2),
                    "performance_tier": to_tier,
                    "rating": best_alt.get("rating", 4.5),
                    "product_id": best_alt.get("product_id", "")
                },
                "savings": round(best_savings, 2),
                "action": f"Replace {most_expensive.get('name', 'item')} with {best_alt.get('name', 'alternative')} in bundle",
                "trade_off": f"{perf_diff}, but still excellent value",
                "recommendation": f"Good swap - {best_alt.get('name', 'alternative')} is sweet spot for value"
            }
        
        except Exception as e:
            return {
                "viable": False,
                "path_type": "bundle_swap",
                "summary": f"Tool execution failed: {str(e)}",
                "error": str(e),
                "action": "N/A",
                "trade_off": "N/A",
                "savings": 0
            }
    
    async def _search_alternatives_qdrant(
        self, category: str, max_price: float, min_price: float, min_rating: float = 4.0, limit: int = 10
    ) -> List[Dict]:
        """
        Search Qdrant for alternative products using the existing QdrantSearch service.
        
        Finds cheaper alternatives to cart items using semantic search.
        Since Qdrant may not have payload indexes, we filter in Python.
        """
        if not self._search_service or not self._embedder:
            return []
        
        try:
            # Build query text for semantic search
            query_text = f"best {category} budget value good performance affordable"
            query_vector = self._embedder.encode_query(query_text).tolist()
            
            # Search WITHOUT filters (to avoid index requirements)
            results = self._search_service.search(
                query_vector=query_vector,
                limit=50,  # Get more to filter in Python
                filters=None
            )
            
            # Enrich with PostgreSQL data if available
            if results:
                results = self._search_service.enrich_results(results)
            
            # Filter results in Python
            products = []
            for r in results:
                # Apply price filters
                if r.price < min_price or r.price > max_price:
                    continue
                if r.rating < min_rating:
                    continue
                if not r.in_stock:
                    continue
                # Only new items for alternatives
                if r.condition and r.condition not in ["new", ""]:
                    continue
                
                # Check if it matches the category
                cat_lower = r.category.lower() if r.category else ""
                name_lower = r.name.lower()
                
                if category.lower() in cat_lower or category.lower() in name_lower:
                    products.append({
                        "product_id": r.product_id,
                        "name": r.name,
                        "price": r.price,
                        "rating": r.rating,
                        "category": r.category
                    })
                    
                    if len(products) >= limit:
                        break
            
            return products
        
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Alternatives search error: {e}")
            return []
    
    def _get_performance_tier(self, price: float, category: str) -> str:
        """Determine performance tier based on price and category."""
        tier_thresholds = {
            "gpus": [(800, "flagship"), (500, "high-end"), (300, "mid-high"), (200, "mid-range"), (0, "entry")],
            "laptops": [(1500, "flagship"), (1000, "high-end"), (700, "mid-high"), (500, "mid-range"), (0, "entry")],
            "monitors": [(500, "premium"), (300, "high-end"), (200, "mid-range"), (0, "entry")],
            "cpus": [(400, "flagship"), (300, "high-end"), (200, "mid-range"), (0, "entry")],
        }
        
        thresholds = tier_thresholds.get(category, [(500, "high"), (250, "mid"), (0, "entry")])
        
        for threshold, tier in thresholds:
            if price >= threshold:
                return tier
        
        return "entry"
    
    def _calculate_perf_difference(self, from_tier: str, to_tier: str) -> str:
        """Calculate performance difference description."""
        tier_order = ["entry", "mid-range", "mid-high", "high-end", "premium", "flagship"]
        
        try:
            from_idx = tier_order.index(from_tier)
            to_idx = tier_order.index(to_tier)
            diff = from_idx - to_idx
            
            if diff == 0:
                return "Same performance tier"
            elif diff == 1:
                return "Slightly lower tier, minimal real-world difference"
            elif diff == 2:
                return "One tier lower, ~15% less performance"
            else:
                return f"{diff} tiers lower, ~{diff * 10}% less performance"
        except ValueError:
            return "Different performance tier"
    
    def _calculate_weekly_savings(self, income_tier: str) -> float:
        """Calculate weekly savings amount based on income tier."""
        config = self.income_config.get(income_tier, self.income_config["medium"])
        return config.weekly_savings
    
    # =========================================================================
    # TOOL DEFINITIONS (for LLM function calling)
    # =========================================================================
    
    def get_tool_definitions(self) -> List[Dict]:
        """Return OpenAI-compatible function definitions for all tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_cart_removals",
                    "description": "Analyze current shopping cart to find items that could be removed to free up budget. Useful when user has items in cart that might be optional or lower priority.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "min_savings_needed": {
                                "type": "number",
                                "description": "Minimum dollar amount that needs to be freed up by removing items"
                            }
                        },
                        "required": ["min_savings_needed"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_income_projection",
                    "description": "Calculate how many weeks the user needs to save money based on their income tier to afford the target amount. Useful for time-based affordability strategies.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_amount": {
                                "type": "number",
                                "description": "Dollar amount the user needs to save"
                            }
                        },
                        "required": ["target_amount"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_installment_plans",
                    "description": "Find installment payment plan options to spread the cost over multiple months. Useful when upfront cost is too high but monthly payments would be affordable.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_price": {
                                "type": "number",
                                "description": "Total price of the product to finance"
                            },
                            "max_monthly_payment": {
                                "type": "number",
                                "description": "Optional: maximum monthly payment user can afford"
                            }
                        },
                        "required": ["product_price"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_refurbished_alternatives",
                    "description": "Search for refurbished or open-box versions of similar products that cost less but maintain quality. Great for finding immediate savings.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_category": {
                                "type": "string",
                                "description": "Category to search in (e.g., 'laptops', 'monitors', 'gpus')"
                            },
                            "max_price": {
                                "type": "number",
                                "description": "Maximum price user can afford"
                            },
                            "min_savings": {
                                "type": "number",
                                "description": "Minimum savings needed to make refurbished worthwhile"
                            }
                        },
                        "required": ["product_category", "max_price"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_bundle_swaps",
                    "description": "Find cheaper alternatives for expensive items currently in the shopping cart bundle. Useful for optimizing bundle cost while maintaining utility.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "savings_target": {
                                "type": "number",
                                "description": "Target dollar amount to save through swaps"
                            }
                        },
                        "required": ["savings_target"]
                    }
                }
            }
        ]
    
    def get_tool_descriptions(self) -> Dict[str, str]:
        """Get simple descriptions of all available tools."""
        return {
            'check_cart_removals': 'Find optional items in cart that could be removed to free budget',
            'check_income_projection': 'Calculate weeks needed to save for the target amount',
            'check_installment_plans': 'Find payment plan options to spread cost over time',
            'check_refurbished_alternatives': 'Search for refurbished/open-box alternatives at lower prices',
            'check_bundle_swaps': 'Find cheaper alternatives for expensive cart items'
        }
    
    # =========================================================================
    # Legacy compatibility methods (for backward compatibility)
    # =========================================================================
    
    def check_cart_removals_sync(self, current_cart: List[Dict], budget: float, target_price: float) -> ToolResult:
        """Legacy synchronous cart removal check."""
        import asyncio
        cart_total = sum(item.get('price', 0) for item in current_cart)
        gap = (cart_total + target_price) - budget
        
        result = asyncio.get_event_loop().run_until_complete(
            self.check_cart_removals(
                args={"min_savings_needed": gap},
                user_afig={},
                current_cart=current_cart,
                budget=budget,
                gap=gap
            )
        )
        
        return ToolResult(
            success=result.get("viable", False),
            data=result,
            message=result.get("summary", "")
        )
    
    def find_refurb_alternatives(self, product: Dict, max_price: Optional[float] = None) -> ToolResult:
        """Legacy refurbished alternatives search."""
        import asyncio
        
        result = asyncio.get_event_loop().run_until_complete(
            self.check_refurbished_alternatives(
                args={
                    "product_category": product.get("category", ""),
                    "max_price": max_price or product.get("price", 0)
                },
                user_afig={},
                current_cart=[],
                budget=max_price or 0,
                gap=0
            )
        )
        
        # Convert to legacy format
        alternatives = []
        if result.get("viable") and result.get("product"):
            prod = result["product"]
            alternatives.append({
                'type': prod.get('condition', 'refurbished'),
                'name': prod.get('name', ''),
                'price': prod.get('price', 0),
                'savings': result.get('savings', 0),
                'savings_percent': round((result.get('savings', 0) / (max_price or 1)) * 100, 1),
                'warranty': prod.get('warranty', ''),
                'condition_notes': result.get('quality_note', ''),
                'risk_level': 'low'
            })
        
        return ToolResult(
            success=result.get("viable", False),
            data={'alternatives': alternatives, 'original_price': product.get('price', 0)},
            message=result.get("summary", "")
        )
    
    def suggest_financing(self, price: float, user_context: Optional[Dict] = None) -> ToolResult:
        """Legacy financing suggestion."""
        import asyncio
        
        result = asyncio.get_event_loop().run_until_complete(
            self.check_installment_plans(
                args={"product_price": price},
                user_afig=user_context or {},
                budget=0,
                gap=0
            )
        )
        
        options = result.get("all_options", [])
        legacy_options = []
        for opt in options:
            legacy_options.append({
                'provider': 'Pay in Installments',
                'months': opt.get('months', 0),
                'monthly_payment': opt.get('monthly_payment', 0),
                'apr': opt.get('apr', '0%'),
                'total_cost': opt.get('total_cost', 0),
                'extra_cost': opt.get('total_interest', 0),
                'approval_likelihood': 'high'
            })
        
        return ToolResult(
            success=result.get("viable", False),
            data={'options': legacy_options, 'recommended': result.get("plan", {})},
            message=result.get("summary", "")
        )


# =============================================================================
# TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_tools():
        print("🧪 Testing Agent Tools...\n")
        
        tools = AgentTools()
        
        user_afig = {"income_tier": "medium", "risk_tolerance": 0.6}
        cart = [
            {"name": "NVIDIA RTX 4070", "price": 599, "category": "gpus"},
            {"name": "Logitech MX Master 3", "price": 89, "category": "mice", "optional": True},
            {"name": "USB-C Hub", "price": 45, "category": "accessories"},
        ]
        
        budget = 1500
        gap = 600
        
        print("=" * 60)
        print("TEST 1: check_cart_removals")
        print("=" * 60)
        result = await tools.check_cart_removals(
            args={"min_savings_needed": 200},
            user_afig=user_afig,
            current_cart=cart,
            budget=budget,
            gap=gap
        )
        print(f"Viable: {result['viable']}")
        print(f"Summary: {result['summary']}")
        print(f"Savings: ${result.get('savings', 0)}")
        
        print("\n" + "=" * 60)
        print("TEST 2: check_income_projection")
        print("=" * 60)
        result = await tools.check_income_projection(
            args={"target_amount": 600},
            user_afig=user_afig,
            budget=budget,
            gap=gap
        )
        print(f"Viable: {result['viable']}")
        print(f"Summary: {result['summary']}")
        print(f"Weeks: {result.get('weeks', 0)}, Weekly: ${result.get('weekly_amount', 0)}")
        
        print("\n" + "=" * 60)
        print("TEST 3: check_installment_plans")
        print("=" * 60)
        result = await tools.check_installment_plans(
            args={"product_price": 2499},
            user_afig=user_afig,
            budget=budget,
            gap=gap
        )
        print(f"Viable: {result['viable']}")
        print(f"Summary: {result['summary']}")
        
        print("\n" + "=" * 60)
        print("TEST 4: check_refurbished_alternatives")
        print("=" * 60)
        result = await tools.check_refurbished_alternatives(
            args={"product_category": "laptops", "max_price": 1500},
            user_afig=user_afig,
            current_cart=cart,
            budget=budget,
            gap=gap
        )
        print(f"Viable: {result['viable']}")
        print(f"Summary: {result['summary']}")
        
        print("\n" + "=" * 60)
        print("TEST 5: check_bundle_swaps")
        print("=" * 60)
        result = await tools.check_bundle_swaps(
            args={"savings_target": 300},
            user_afig=user_afig,
            current_cart=cart,
            budget=budget,
            gap=gap
        )
        print(f"Viable: {result['viable']}")
        print(f"Summary: {result['summary']}")
        
        print("\n✅ All tools tested!")
    
    asyncio.run(test_tools())