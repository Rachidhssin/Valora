"""
Budget Pathfinder Agent
ReAct agent that finds creative ways to make products affordable
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from dotenv import load_dotenv

from agent.tools import AgentTools, ToolResult

load_dotenv()

try:
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class PathType(Enum):
    CART_REMOVAL = "cart_removal"
    REFURBISHED = "refurbished"
    FINANCING = "financing"
    BUNDLE = "bundle"
    WAIT_FOR_SALE = "wait_for_sale"
    NO_PATH = "no_path"


@dataclass
class AffordabilityPath:
    """A single affordability solution path."""
    viable: bool
    path_type: PathType
    summary: str
    action: str
    trade_off: str
    savings: float = 0.0
    details: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'viable': self.viable,
            'path_type': self.path_type.value,
            'summary': self.summary,
            'action': self.action,
            'trade_off': self.trade_off,
            'savings': self.savings,
            'details': self.details or {}
        }


@dataclass
class AgentResult:
    """Result from the Budget Pathfinder Agent."""
    status: str  # 'paths_found', 'no_paths', 'error'
    gap: float  # Budget gap
    paths: List[AffordabilityPath]
    reasoning_trace: List[str]
    iterations: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status,
            'gap': self.gap,
            'paths': [p.to_dict() for p in self.paths],
            'reasoning_trace': self.reasoning_trace,
            'iterations': self.iterations
        }


class BudgetPathfinderAgent:
    """
    ReAct agent that finds creative affordability paths.
    Uses Groq LLM for reasoning with tool calling.
    """
    
    MAX_ITERATIONS = 5
    MODEL = "llama-3.1-8b-instant"  # Fast, free-tier Groq model
    
    SYSTEM_PROMPT = """You are a Budget Pathfinder Agent helping users afford products within their budget.

Your job is to analyze the budget gap and find creative solutions using the available tools.

Available tools:
1. check_cart_removals - Find items to remove from cart to free up budget
2. find_refurb_alternatives - Find refurbished/open-box options at lower prices
3. suggest_financing - Get financing options to spread payments
4. find_bundle_discounts - Find bundle deals for savings
5. check_upcoming_sales - Check for upcoming sales or price drops

Strategy:
1. First assess the gap size and user context
2. Try the most relevant tools based on the situation
3. Rank solutions by viability and trade-offs
4. Return at most 3 best paths

For each tool, respond with:
THOUGHT: [your reasoning]
ACTION: [tool_name]
ACTION_INPUT: [json parameters]

After gathering information, respond with:
THOUGHT: [final analysis]
ANSWER: [json with paths]

Be concise and practical. Focus on actionable solutions."""
    
    def __init__(self):
        self.tools = AgentTools()
        self._client = None
        
        if GROQ_AVAILABLE:
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                self._client = AsyncGroq(api_key=api_key)
    
    async def find_affordability_paths(self,
                                       product: Dict[str, Any],
                                       user_afig: Dict[str, Any],
                                       current_cart: List[Dict],
                                       budget: float,
                                       skip_llm: bool = False) -> Dict[str, Any]:
        """
        Find ways to make a product affordable.
        
        Args:
            product: Product user wants to add
            user_afig: Reconciled AFIG context
            current_cart: Current cart items
            budget: User's budget
            
        Returns:
            Dict with affordability paths
        """
        price = product.get('price', 0)
        cart_total = sum(item.get('price', 0) for item in current_cart)
        gap = (price + cart_total) - budget
        
        # If no gap, product is affordable
        if gap <= 0:
            return {
                'status': 'no_gap',
                'gap': 0,
                'paths': [],
                'message': 'Product fits within budget'
            }
        
        # Build context for agent
        context = {
            'product': product,
            'product_price': price,
            'cart_total': cart_total,
            'budget': budget,
            'gap': gap,
            'user_archetype': user_afig.get('archetype', 'value_balanced'),
            'timeline': user_afig.get('timeline', 'flexible'),
            'risk_tolerance': user_afig.get('risk_tolerance', 0.5)
        }
        
        # Run agent loop
        if self._client and not skip_llm:
            result = await self._run_llm_agent(context, current_cart)
        else:
            # Fallback to rule-based agent
            result = await self._run_rule_based_agent(context, current_cart)
        
        return result.to_dict()
    
    async def _run_llm_agent(self, context: Dict, cart: List[Dict]) -> AgentResult:
        """Run LLM-based ReAct agent."""
        reasoning_trace = []
        paths = []
        iterations = 0
        
        # Initial prompt
        user_prompt = f"""Find affordability paths for this situation:

Product: {context['product'].get('name', 'Unknown')}
Product Price: ${context['product_price']:.2f}
Current Cart Total: ${context['cart_total']:.2f}
Budget: ${context['budget']:.2f}
Gap to Close: ${context['gap']:.2f}

User Profile:
- Archetype: {context['user_archetype']}
- Timeline: {context['timeline']}
- Risk Tolerance: {context['risk_tolerance']:.2f}

Current Cart Items: {len(cart)} items

Find up to 3 viable paths to make this purchase affordable."""

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        while iterations < self.MAX_ITERATIONS:
            iterations += 1
            
            try:
                response = await self._client.chat.completions.create(
                    model=self.MODEL,
                    messages=messages,
                    max_tokens=500,
                    temperature=0.3
                )
                
                content = response.choices[0].message.content
                reasoning_trace.append(f"[Iteration {iterations}] {content[:200]}...")
                
                # Parse response
                if "ANSWER:" in content:
                    # Agent is done, parse final answer
                    answer_part = content.split("ANSWER:")[-1].strip()
                    paths = self._parse_paths(answer_part, context)
                    break
                
                elif "ACTION:" in content:
                    # Execute tool
                    tool_result = self._execute_tool_from_response(content, context, cart)
                    
                    # Add observation to conversation
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user", 
                        "content": f"OBSERVATION: {tool_result.message}\nDATA: {json.dumps(tool_result.data)[:500]}"
                    })
                else:
                    # No clear action, push for answer
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": "Based on your analysis, provide your ANSWER with the best affordability paths."
                    })
                    
            except Exception as e:
                reasoning_trace.append(f"[Error] {str(e)}")
                break
        
        # If no paths found through LLM, fallback to rule-based
        if not paths:
            fallback = await self._run_rule_based_agent(context, cart)
            paths = fallback.paths
            reasoning_trace.extend(fallback.reasoning_trace)
        
        status = 'paths_found' if paths else 'no_paths'
        
        return AgentResult(
            status=status,
            gap=context['gap'],
            paths=paths,
            reasoning_trace=reasoning_trace,
            iterations=iterations
        )
    
    async def _run_rule_based_agent(self, context: Dict, cart: List[Dict]) -> AgentResult:
        """Fallback rule-based agent when LLM is unavailable."""
        reasoning_trace = ["Using rule-based fallback agent"]
        paths = []
        gap = context['gap']
        product = context['product']
        
        # Strategy 1: Check refurbished alternatives
        refurb_result = self.tools.find_refurb_alternatives(product, max_price=context['budget'] - context['cart_total'])
        if refurb_result.success:
            best_alt = refurb_result.data.get('alternatives', [{}])[0]
            if best_alt.get('savings', 0) >= gap * 0.5:  # Covers at least half the gap
                paths.append(AffordabilityPath(
                    viable=True,
                    path_type=PathType.REFURBISHED,
                    summary=f"Get {best_alt.get('type', 'refurbished')} version and save ${best_alt.get('savings', 0):.2f}",
                    action=f"Choose the {best_alt.get('type', 'refurbished')} option at ${best_alt.get('price', 0):.2f}",
                    trade_off=best_alt.get('condition_notes', 'May have minor wear'),
                    savings=best_alt.get('savings', 0),
                    details=best_alt
                ))
                reasoning_trace.append(f"Found refurb alternative saving ${best_alt.get('savings', 0):.2f}")
        
        # Strategy 2: Check cart removals
        if cart:
            cart_result = self.tools.check_cart_removals(cart, context['budget'], context['product_price'])
            if cart_result.success and cart_result.data.get('suggestions'):
                best_removal = cart_result.data['suggestions'][0]
                if best_removal.get('closes_gap') or best_removal.get('price', 0) >= gap * 0.7:
                    paths.append(AffordabilityPath(
                        viable=True,
                        path_type=PathType.CART_REMOVAL,
                        summary=f"Remove {best_removal['item'].get('name', 'item')} to free up ${best_removal.get('price', 0):.2f}",
                        action="Remove the suggested item from your cart",
                        trade_off=f"Lose utility of {best_removal['item'].get('name', 'item')}",
                        savings=best_removal.get('price', 0),
                        details=best_removal
                    ))
                    reasoning_trace.append(f"Found cart item to remove: ${best_removal.get('price', 0):.2f}")
        
        # Strategy 3: Financing options
        if context.get('timeline') != 'urgent':
            financing_result = self.tools.suggest_financing(context['product_price'])
            if financing_result.success:
                best_option = financing_result.data.get('recommended', {})
                if best_option.get('extra_cost', 999) < gap * 0.2:  # Low extra cost
                    paths.append(AffordabilityPath(
                        viable=True,
                        path_type=PathType.FINANCING,
                        summary=f"Pay ${best_option.get('monthly_payment', 0):.2f}/month via {best_option.get('provider', 'installments')}",
                        action=f"Choose {best_option.get('provider', 'financing')} at checkout",
                        trade_off=f"Total cost: ${best_option.get('total_cost', 0):.2f} ({best_option.get('apr', 'varies')} APR)",
                        savings=0,  # Not really savings, but spreads cost
                        details=best_option
                    ))
                    reasoning_trace.append(f"Found financing option: {best_option.get('provider')}")
        
        # Strategy 4: Wait for sale
        if context.get('timeline') == 'flexible':
            sale_result = self.tools.check_upcoming_sales(product, days_willing_to_wait=30)
            if sale_result.success:
                best_sale = sale_result.data.get('best_option', {})
                if best_sale.get('potential_savings', 0) >= gap * 0.5:
                    paths.append(AffordabilityPath(
                        viable=True,
                        path_type=PathType.WAIT_FOR_SALE,
                        summary=f"Wait {best_sale.get('days_until', 0)} days for {best_sale.get('event', 'sale')}",
                        action=f"Set alert for {best_sale.get('event', 'upcoming sale')}",
                        trade_off=f"Wait {best_sale.get('days_until', 0)} days, savings not guaranteed",
                        savings=best_sale.get('potential_savings', 0),
                        details=best_sale
                    ))
                    reasoning_trace.append(f"Found upcoming sale: {best_sale.get('event')}")
        
        # Sort paths by savings (descending)
        paths.sort(key=lambda p: p.savings, reverse=True)
        paths = paths[:3]  # Keep top 3
        
        status = 'paths_found' if paths else 'no_paths'
        
        return AgentResult(
            status=status,
            gap=gap,
            paths=paths,
            reasoning_trace=reasoning_trace,
            iterations=1
        )
    
    def _execute_tool_from_response(self, response: str, context: Dict, cart: List[Dict]) -> ToolResult:
        """Parse and execute tool from LLM response."""
        try:
            # Extract action and input
            lines = response.split('\n')
            action = None
            action_input = {}
            
            for line in lines:
                if line.startswith('ACTION:'):
                    action = line.replace('ACTION:', '').strip().lower()
                elif line.startswith('ACTION_INPUT:'):
                    input_str = line.replace('ACTION_INPUT:', '').strip()
                    try:
                        action_input = json.loads(input_str)
                    except:
                        action_input = {}
            
            if not action:
                return ToolResult(False, {}, "Could not parse action from response")
            
            # Execute the appropriate tool
            if action == 'check_cart_removals':
                return self.tools.check_cart_removals(
                    cart, 
                    context['budget'], 
                    context['product_price']
                )
            elif action == 'find_refurb_alternatives':
                return self.tools.find_refurb_alternatives(
                    context['product'],
                    max_price=context['budget'] - context['cart_total']
                )
            elif action == 'suggest_financing':
                return self.tools.suggest_financing(
                    context['product_price'],
                    user_context={'credit_score_tier': 'good'}
                )
            elif action == 'find_bundle_discounts':
                return self.tools.find_bundle_discounts(
                    cart + [context['product']],
                    context['product'].get('category', '')
                )
            elif action == 'check_upcoming_sales':
                days = action_input.get('days_willing_to_wait', 30)
                return self.tools.check_upcoming_sales(context['product'], days)
            else:
                return ToolResult(False, {}, f"Unknown tool: {action}")
                
        except Exception as e:
            return ToolResult(False, {}, f"Tool execution error: {str(e)}")
    
    def _parse_paths(self, answer_str: str, context: Dict) -> List[AffordabilityPath]:
        """Parse paths from LLM answer string."""
        paths = []
        
        try:
            # Try to parse as JSON
            data = json.loads(answer_str)
            if isinstance(data, list):
                for item in data[:3]:
                    paths.append(AffordabilityPath(
                        viable=item.get('viable', True),
                        path_type=PathType(item.get('path_type', 'no_path')),
                        summary=item.get('summary', ''),
                        action=item.get('action', ''),
                        trade_off=item.get('trade_off', ''),
                        savings=item.get('savings', 0)
                    ))
            elif isinstance(data, dict) and 'paths' in data:
                for item in data['paths'][:3]:
                    paths.append(AffordabilityPath(
                        viable=item.get('viable', True),
                        path_type=PathType(item.get('path_type', 'no_path')),
                        summary=item.get('summary', ''),
                        action=item.get('action', ''),
                        trade_off=item.get('trade_off', ''),
                        savings=item.get('savings', 0)
                    ))
        except:
            # If JSON parsing fails, return empty list
            pass
        
        return paths


# Async test helper
async def _test_agent():
    print("🧪 Testing Budget Pathfinder Agent...")
    
    agent = BudgetPathfinderAgent()
    
    product = {
        'id': 'prod_001',
        'name': 'ASUS ROG Laptop RTX 4070',
        'category': 'laptops',
        'brand': 'ASUS',
        'price': 1499
    }
    
    cart = [
        {'id': 'cart_1', 'name': 'Gaming Mouse', 'price': 89, 'utility': 0.7},
        {'id': 'cart_2', 'name': 'Mechanical Keyboard', 'price': 149, 'utility': 0.8},
    ]
    
    user_afig = {
        'archetype': 'value_balanced',
        'timeline': 'flexible',
        'risk_tolerance': 0.5
    }
    
    budget = 1200
    
    print(f"\n📊 Test scenario:")
    print(f"   Product: {product['name']} (${product['price']})")
    print(f"   Cart total: ${sum(c['price'] for c in cart)}")
    print(f"   Budget: ${budget}")
    print(f"   Gap: ${product['price'] + sum(c['price'] for c in cart) - budget}")
    
    result = await agent.find_affordability_paths(product, user_afig, cart, budget)
    
    print(f"\n📊 Result: {result['status']}")
    print(f"   Gap: ${result['gap']:.2f}")
    print(f"   Paths found: {len(result['paths'])}")
    
    for i, path in enumerate(result['paths'], 1):
        print(f"\n   Path {i}: {path['path_type']}")
        print(f"      Summary: {path['summary']}")
        print(f"      Action: {path['action']}")
        print(f"      Trade-off: {path['trade_off']}")
        if path['savings']:
            print(f"      Savings: ${path['savings']:.2f}")
    
    print("\n✅ Agent test complete!")


if __name__ == "__main__":
    asyncio.run(_test_agent())
