"""
Bundle Optimizer
Hybrid MILP (OR-Tools CP-SAT) + Greedy optimization for product bundles
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time

try:
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    print("⚠️ OR-Tools not installed, using greedy optimizer only")


class OptStatus(Enum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    TIMEOUT = "timeout"
    INFEASIBLE = "infeasible"
    ERROR = "error"


@dataclass
class Product:
    """Product for optimization."""
    id: str
    name: str
    price: float
    category: str
    utility: float  # Pre-computed utility score (0-1)
    image_url: str = ""  # Product image URL
    brand: str = ""  # Product brand
    rating: float = 0.0  # Product rating
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class OptimizationResult:
    """Result of bundle optimization."""
    status: OptStatus
    bundle: List[Product]
    total_price: float
    total_utility: float
    budget_used: float  # Percentage of budget used
    solve_time_ms: float
    method: str  # "milp" or "greedy"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'bundle': [{'id': p.id, 'name': p.name, 'price': p.price, 
                       'category': p.category, 'utility': p.utility,
                       'image_url': p.image_url, 'brand': p.brand, 
                       'rating': p.rating} for p in self.bundle],
            'total_price': round(self.total_price, 2),
            'total_utility': round(self.total_utility, 4),
            'budget_used': round(self.budget_used, 4),
            'solve_time_ms': round(self.solve_time_ms, 2),
            'method': self.method
        }


class BundleOptimizer:
    """
    Hybrid bundle optimizer.
    - Small problems (≤10 items): OR-Tools CP-SAT (exact solution)
    - Large problems (>10 items): Greedy + Beam Search (fast approximation)
    """
    
    MILP_THRESHOLD = 15  # Use MILP for up to 15 items
    MILP_TIMEOUT_MS = 500  # 500ms timeout for MILP
    
    # Categories where only one item makes sense
    SINGLE_ITEM_CATEGORIES = {'laptops', 'desks', 'chairs'}
    
    def __init__(self, milp_timeout_ms: int = 500):
        self.milp_timeout_ms = milp_timeout_ms
    
    def optimize(self, products: List[Product], 
                budget: float,
                user_prefs: Dict[str, Any],
                required_categories: Optional[List[str]] = None,
                max_items: int = 10) -> OptimizationResult:
        """
        Optimize product bundle within budget.
        
        Args:
            products: List of Product objects to consider
            budget: Maximum budget
            user_prefs: User preferences for utility weighting
            required_categories: Categories that must be included
            max_items: Maximum number of items in bundle
            
        Returns:
            OptimizationResult with selected products
        """
        if not products:
            return OptimizationResult(
                status=OptStatus.INFEASIBLE,
                bundle=[],
                total_price=0,
                total_utility=0,
                budget_used=0,
                solve_time_ms=0,
                method="none"
            )
        
        # Convert dicts to Product objects if needed
        products = self._ensure_products(products)
        
        # Filter by budget first
        affordable = [p for p in products if p.price <= budget]
        
        if not affordable:
            return OptimizationResult(
                status=OptStatus.INFEASIBLE,
                bundle=[],
                total_price=0,
                total_utility=0,
                budget_used=0,
                solve_time_ms=0,
                method="none"
            )
        
        # Choose method based on problem size
        if len(affordable) <= self.MILP_THRESHOLD and ORTOOLS_AVAILABLE:
            result = self._milp_optimize(affordable, budget, required_categories, max_items)
            
            # Fallback to greedy if MILP times out or fails
            if result.status in [OptStatus.TIMEOUT, OptStatus.ERROR]:
                result = self._greedy_optimize(affordable, budget, required_categories, max_items)
        else:
            result = self._greedy_optimize(affordable, budget, required_categories, max_items)
        
        return result
    
    def _ensure_products(self, items: List) -> List[Product]:
        """Convert dicts to Product objects."""
        p_items = []
        for item in items:
            if isinstance(item, Product):
                p_items.append(item)
            elif isinstance(item, dict):
                # Handle ID mapping
                pid = item.get("id") or item.get("product_id") or ""
                # Handle Category mapping
                cat = item.get("category") or item.get("main_category") or "Unknown"
                # Handle Name mapping
                name = item.get("name") or item.get("title") or "Unknown"
                
                # Default utility if not present (will be calc later if 0)
                util = item.get("utility", 0.0) 
                # If score is present (from search), use it as base utility
                if util == 0.0 and "score" in item:
                    util = item["score"]
                
                p_items.append(Product(
                    id=pid,
                    name=name,
                    price=float(item.get("price", 0.0)),
                    category=cat,
                    utility=util,
                    image_url=item.get("image_url", ""),
                    brand=item.get("brand", ""),
                    rating=float(item.get("rating", 0.0))
                ))
            elif hasattr(item, 'product_id'):
                utility = getattr(item, 'utility', 0.5)
                if hasattr(item, '_feasibility'):
                    utility = item._feasibility.get('adjusted_utility', utility)
                p_items.append(Product(
                    id=item.product_id,
                    name=item.name,
                    price=item.price,
                    category=item.category,
                    utility=utility,
                    image_url=getattr(item, 'image_url', ""),
                    brand=getattr(item, 'brand', ""),
                    rating=float(getattr(item, 'rating', 0.0))
                ))
        return p_items
    
    def _milp_optimize(self, products: List[Product], budget: float,
                       required_categories: Optional[List[str]],
                       max_items: int) -> OptimizationResult:
        """
        Solve using OR-Tools CP-SAT (constraint programming).
        """
        start_time = time.time()
        
        model = cp_model.CpModel()
        
        # Binary variables: x[i] = 1 if product i is selected
        n = len(products)
        x = [model.NewBoolVar(f'x_{i}') for i in range(n)]
        
        # Scale prices and utilities to integers (CP-SAT works with integers)
        SCALE = 100
        prices = [int(p.price * SCALE) for p in products]
        utilities = [int(p.utility * 1000) for p in products]  # Higher precision for utility
        budget_scaled = int(budget * SCALE)
        
        # Constraint: total price <= budget
        model.Add(sum(x[i] * prices[i] for i in range(n)) <= budget_scaled)
        
        # Constraint: max items
        model.Add(sum(x) <= max_items)
        
        # Constraint: at most one item per single-item category
        category_to_indices: Dict[str, List[int]] = {}
        for i, p in enumerate(products):
            if p.category not in category_to_indices:
                category_to_indices[p.category] = []
            category_to_indices[p.category].append(i)
        
        for cat, indices in category_to_indices.items():
            if cat in self.SINGLE_ITEM_CATEGORIES:
                model.Add(sum(x[i] for i in indices) <= 1)
        
        # Constraint: required categories (if specified)
        if required_categories:
            for cat in required_categories:
                if cat in category_to_indices:
                    model.Add(sum(x[i] for i in category_to_indices[cat]) >= 1)
        
        # Objective: maximize total utility
        model.Maximize(sum(x[i] * utilities[i] for i in range(n)))
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.milp_timeout_ms / 1000.0
        
        status = solver.Solve(model)
        solve_time = (time.time() - start_time) * 1000
        
        if status == cp_model.OPTIMAL:
            selected = [products[i] for i in range(n) if solver.Value(x[i]) == 1]
            total_price = sum(p.price for p in selected)
            total_utility = sum(p.utility for p in selected)
            
            return OptimizationResult(
                status=OptStatus.OPTIMAL,
                bundle=selected,
                total_price=total_price,
                total_utility=total_utility,
                budget_used=total_price / budget if budget > 0 else 0,
                solve_time_ms=solve_time,
                method="milp"
            )
        
        elif status == cp_model.FEASIBLE:
            selected = [products[i] for i in range(n) if solver.Value(x[i]) == 1]
            total_price = sum(p.price for p in selected)
            total_utility = sum(p.utility for p in selected)
            
            return OptimizationResult(
                status=OptStatus.FEASIBLE,
                bundle=selected,
                total_price=total_price,
                total_utility=total_utility,
                budget_used=total_price / budget if budget > 0 else 0,
                solve_time_ms=solve_time,
                method="milp"
            )
        
        elif status == cp_model.INFEASIBLE:
            return OptimizationResult(
                status=OptStatus.INFEASIBLE,
                bundle=[],
                total_price=0,
                total_utility=0,
                budget_used=0,
                solve_time_ms=solve_time,
                method="milp"
            )
        
        else:  # Unknown or timeout
            return OptimizationResult(
                status=OptStatus.TIMEOUT,
                bundle=[],
                total_price=0,
                total_utility=0,
                budget_used=0,
                solve_time_ms=solve_time,
                method="milp"
            )
    
    def _greedy_optimize(self, products: List[Product], budget: float,
                         required_categories: Optional[List[str]],
                         max_items: int) -> OptimizationResult:
        """
        Fast greedy optimization with value-density ranking.
        """
        start_time = time.time()
        
        # Sort by utility/price ratio (value density)
        sorted_products = sorted(
            products,
            key=lambda p: p.utility / max(p.price, 1),
            reverse=True
        )
        
        selected = []
        remaining_budget = budget
        selected_categories: Dict[str, int] = {}
        
        # First pass: satisfy required categories
        if required_categories:
            for cat in required_categories:
                cat_products = [p for p in sorted_products 
                              if p.category == cat and p.price <= remaining_budget]
                if cat_products:
                    best = max(cat_products, key=lambda p: p.utility)
                    selected.append(best)
                    remaining_budget -= best.price
                    selected_categories[cat] = selected_categories.get(cat, 0) + 1
        
        # Second pass: fill remaining budget greedily
        for product in sorted_products:
            if len(selected) >= max_items:
                break
            if product in selected:
                continue
            if product.price > remaining_budget:
                continue
            
            # Check single-item category constraint
            if product.category in self.SINGLE_ITEM_CATEGORIES:
                if selected_categories.get(product.category, 0) >= 1:
                    continue
            
            selected.append(product)
            remaining_budget -= product.price
            selected_categories[product.category] = selected_categories.get(product.category, 0) + 1
        
        solve_time = (time.time() - start_time) * 1000
        
        total_price = sum(p.price for p in selected)
        total_utility = sum(p.utility for p in selected)
        
        return OptimizationResult(
            status=OptStatus.FEASIBLE if selected else OptStatus.INFEASIBLE,
            bundle=selected,
            total_price=total_price,
            total_utility=total_utility,
            budget_used=total_price / budget if budget > 0 else 0,
            solve_time_ms=solve_time,
            method="greedy"
        )
    
    def explain_selection(self, result: OptimizationResult) -> str:
        """Generate human-readable explanation of the bundle."""
        if not result.bundle:
            return "No products could be selected within the given constraints."
        
        lines = [
            f"📦 Bundle ({len(result.bundle)} items, ${result.total_price:.2f})",
            f"   Method: {result.method.upper()}, Status: {result.status.value}",
            f"   Budget utilization: {result.budget_used * 100:.1f}%",
            "",
            "Selected items:"
        ]
        
        for p in result.bundle:
            lines.append(f"   • {p.name}")
            lines.append(f"     ${p.price:.2f} | {p.category} | utility: {p.utility:.3f}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    print("🧪 Testing Bundle Optimizer...")
    
    # Create test products
    products = [
        Product("1", "ASUS ROG Laptop RTX 4070", 1399, "laptops", 0.92),
        Product("2", "Dell XPS 15", 1199, "laptops", 0.88),
        Product("3", "LG 27\" 4K Monitor", 399, "monitors", 0.85),
        Product("4", "Samsung 32\" Curved", 349, "monitors", 0.82),
        Product("5", "Logitech MX Keys", 99, "keyboards", 0.78),
        Product("6", "Corsair K70 RGB", 149, "keyboards", 0.83),
        Product("7", "Logitech G Pro X", 89, "mice", 0.80),
        Product("8", "Razer DeathAdder", 69, "mice", 0.76),
        Product("9", "SteelSeries Arctis 7", 149, "headsets", 0.84),
        Product("10", "HyperX Cloud II", 79, "headsets", 0.75),
    ]
    
    optimizer = BundleOptimizer()
    
    # Test 1: Small problem (MILP)
    print("\n📊 Test 1: Budget $1500")
    result = optimizer.optimize(products, budget=1500, user_prefs={})
    print(optimizer.explain_selection(result))
    print(f"   Solve time: {result.solve_time_ms:.2f}ms")
    
    # Test 2: Smaller budget
    print("\n📊 Test 2: Budget $500")
    result = optimizer.optimize(products, budget=500, user_prefs={})
    print(optimizer.explain_selection(result))
    
    # Test 3: Required categories
    print("\n📊 Test 3: Budget $800 with required [monitors, keyboards]")
    result = optimizer.optimize(
        products, 
        budget=800, 
        user_prefs={},
        required_categories=['monitors', 'keyboards']
    )
    print(optimizer.explain_selection(result))
    
    print("\n✅ Bundle optimizer test complete!")
