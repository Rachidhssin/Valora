"""
Budget Pathfinder Agent
========================
ReAct-style agent that finds creative ways to make products affordable.
Uses Groq LLM for reasoning with function calling.

The agent follows the ReAct (Reasoning + Acting) pattern:
1. THINK: Analyze the situation and decide what to do
2. ACT: Call a tool to gather information
3. OBSERVE: Process the tool result
4. Repeat until 3 viable paths are found or max iterations reached

Features:
- Groq LLM integration with function calling
- 5 specialized tools for finding affordability paths
- Rate limit handling with exponential backoff
- Comprehensive error handling and logging
- Conversation trace for debugging/demo
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from dotenv import load_dotenv

from agent.tools import AgentTools

load_dotenv()

# Try to import Groq
try:
    from groq import AsyncGroq, RateLimitError
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    RateLimitError = Exception  # Fallback


class PathType(Enum):
    """Types of affordability paths the agent can find."""
    CART_REMOVAL = "cart_removal"
    SAVE_AND_WAIT = "save_and_wait"
    INSTALLMENT = "installment"
    REFURBISHED = "refurbished"
    BUNDLE_SWAP = "bundle_swap"
    NO_PATH = "no_path"


@dataclass
class ConversationEntry:
    """A single entry in the agent's conversation trace."""
    step: int
    entry_type: str  # "think", "action", "observation"
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None
    tool_result: Optional[Dict] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentResult:
    """Result from the Budget Pathfinder Agent."""
    status: str  # 'paths_found', 'no_solutions', 'affordable', 'error', 'timeout'
    gap: float
    paths: List[Dict[str, Any]]
    agent_steps: int
    conversation: List[Dict[str, Any]]
    token_usage: Dict[str, int] = field(default_factory=lambda: {"prompt": 0, "completion": 0})
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status,
            'gap': self.gap,
            'paths': self.paths,
            'agent_steps': self.agent_steps,
            'conversation': self.conversation,
            'token_usage': self.token_usage,
            'error_message': self.error_message
        }


class BudgetPathfinderAgent:
    """
    ReAct agent that finds creative affordability paths.
    
    Uses Groq LLM with function calling to explore solutions systematically.
    The agent thinks, acts (calls tools), observes results, and repeats
    until it finds 3 viable paths or reaches max iterations.
    
    Attributes:
        max_iterations: Maximum ReAct loop iterations (default: 5)
        model: Groq model to use (default: llama-3.1-8b-instant)
        verbose: Enable detailed logging for demos
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        verbose: bool = False,
        max_iterations: int = 5,
        model: str = "llama-3.1-8b-instant"
    ):
        """
        Initialize the Budget Pathfinder Agent.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            verbose: Enable verbose logging for demos
            max_iterations: Maximum ReAct loop iterations
            model: Groq model to use
        """
        self.verbose = verbose
        self.max_iterations = max_iterations
        self.model = model
        self.tools_instance = AgentTools(verbose=verbose)
        self._client = None
        self.token_usage = {"prompt": 0, "completion": 0}
        
        if GROQ_AVAILABLE:
            key = api_key or os.getenv("GROQ_API_KEY")
            if key:
                self._client = AsyncGroq(api_key=key)
            else:
                print("⚠️ GROQ_API_KEY not set, agent will use fallback mode")
        else:
            print("⚠️ groq package not installed, agent will use fallback mode")
    
    async def find_affordability_paths(
        self,
        product: Dict[str, Any],
        user_afig: Dict[str, Any],
        current_cart: List[Dict],
        budget: float
    ) -> Dict[str, Any]:
        """
        Main entry point: Find creative affordability paths for a product.
        
        This method implements the full ReAct loop:
        1. Check if product is already affordable
        2. Build system prompt with context
        3. Run Think → Act → Observe loop
        4. Collect and rank viable paths
        5. Return top 3 paths
        
        Args:
            product: Product user wants {name, price, category}
            user_afig: User context from AFIG {income_tier, risk_tolerance, ...}
            current_cart: Current cart items
            budget: User's budget
            
        Returns:
            Dict with:
            - status: 'paths_found' | 'no_solutions' | 'affordable' | 'error'
            - gap: Budget shortfall amount
            - paths: List of viable affordability paths (max 3)
            - agent_steps: Number of iterations used
            - conversation: Full ReAct trace for debugging
        """
        try:
            # Calculate gap
            price = product.get('price', 0)
            gap = price - budget
            
            # Early exit if affordable
            if gap <= 0:
                if self.verbose:
                    print("✅ Product is already affordable!")
                return AgentResult(
                    status="affordable",
                    gap=0,
                    paths=[],
                    agent_steps=0,
                    conversation=[]
                ).to_dict()
            
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"🤖 BUDGET PATHFINDER AGENT ACTIVATED")
                print(f"{'='*60}")
                print(f"Product: {product.get('name', 'Unknown')} (${price:.0f})")
                print(f"Budget: ${budget:.0f}")
                print(f"Gap: ${gap:.0f}")
                print(f"{'='*60}\n")
            
            # Run with timeout protection
            result = await asyncio.wait_for(
                self._run_react_loop(product, user_afig, current_cart, budget, gap),
                timeout=15.0  # 15 second max
            )
            
            return result.to_dict()
        
        except asyncio.TimeoutError:
            print("⚠️ Agent timed out after 15 seconds")
            # Fall back to rule-based agent
            fallback = await self._run_rule_based_agent(product, user_afig, current_cart, budget, gap)
            return fallback.to_dict()
        
        except Exception as e:
            print(f"❌ Agent error: {e}")
            return AgentResult(
                status="error",
                gap=gap if 'gap' in dir() else 0,
                paths=[],
                agent_steps=0,
                conversation=[],
                error_message=str(e)
            ).to_dict()
    
    async def _run_react_loop(
        self,
        product: Dict,
        user_afig: Dict,
        current_cart: List[Dict],
        budget: float,
        gap: float
    ) -> AgentResult:
        """
        Execute the ReAct (Reasoning + Acting) loop.
        
        This is the core agent loop that:
        1. Builds context and system prompt
        2. Calls LLM with function definitions
        3. Executes tool calls
        4. Collects viable paths
        5. Stops when 3 paths found or max iterations reached
        """
        # Reset token tracking
        self.token_usage = {"prompt": 0, "completion": 0}
        
        # Check if LLM is available
        if not self._client:
            if self.verbose:
                print("⚠️ LLM not available, using rule-based fallback")
            return await self._run_rule_based_agent(product, user_afig, current_cart, budget, gap)
        
        # Build system prompt
        system_prompt = self._build_system_prompt(product, gap, budget, user_afig)
        
        # Initialize conversation
        messages = [{"role": "system", "content": system_prompt}]
        
        paths_found = []
        conversation_history = []
        iteration = 0
        
        # ReAct loop
        while iteration < self.max_iterations:
            iteration += 1
            
            if self.verbose:
                print(f"\n🤔 Agent Iteration {iteration}/{self.max_iterations}")
            
            try:
                # 1. THINK: Agent decides what to do
                response = await self._call_llm_with_retry(messages)
                assistant_message = response.choices[0].message
                
                # Track token usage
                if hasattr(response, 'usage') and response.usage:
                    self.token_usage["prompt"] += response.usage.prompt_tokens
                    self.token_usage["completion"] += response.usage.completion_tokens
                
                # Log thinking
                if assistant_message.content:
                    if self.verbose:
                        print(f"💭 Think: {assistant_message.content[:100]}...")
                    conversation_history.append({
                        "step": iteration,
                        "type": "think",
                        "content": assistant_message.content
                    })
                
                # 2. ACT: Check if agent wants to use tools
                if assistant_message.tool_calls:
                    # Add assistant message to conversation
                    messages.append({
                        "role": "assistant",
                        "content": assistant_message.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in assistant_message.tool_calls
                        ]
                    })
                    
                    # Process each tool call
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        if self.verbose:
                            print(f"🔧 Action: {tool_name}({json.dumps(tool_args)})")
                        
                        # 3. OBSERVE: Execute tool
                        tool_result = await self._execute_tool(
                            tool_name,
                            tool_args,
                            user_afig,
                            current_cart,
                            budget,
                            gap
                        )
                        
                        if self.verbose:
                            print(f"📊 Observation: {tool_result.get('summary', 'No result')}")
                        
                        # Add tool result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": json.dumps(tool_result)
                        })
                        
                        conversation_history.append({
                            "step": iteration,
                            "type": "action",
                            "tool": tool_name,
                            "args": tool_args,
                            "result": tool_result
                        })
                        
                        # Collect viable paths
                        if tool_result.get("viable"):
                            paths_found.append(tool_result)
                            if self.verbose:
                                print(f"✅ Found viable path: {tool_result['path_type']}")
                else:
                    # No tool calls - agent finished thinking
                    if self.verbose:
                        print("✅ Agent completed reasoning")
                    break
                
                # Stop if we found 3 good paths
                if len(paths_found) >= 3:
                    if self.verbose:
                        print(f"✅ Found {len(paths_found)} paths, stopping")
                    break
                    
            except RateLimitError as e:
                print(f"⚠️ Rate limit hit on iteration {iteration}")
                conversation_history.append({
                    "step": iteration,
                    "type": "error",
                    "content": f"Rate limit error: {str(e)}"
                })
                break
                
            except Exception as e:
                print(f"❌ Error in iteration {iteration}: {e}")
                conversation_history.append({
                    "step": iteration,
                    "type": "error",
                    "content": str(e)
                })
                break
        
        # If no paths found through LLM, try rule-based fallback
        if not paths_found:
            if self.verbose:
                print("⚠️ No paths from LLM, trying rule-based fallback")
            fallback = await self._run_rule_based_agent(product, user_afig, current_cart, budget, gap)
            paths_found = fallback.paths
            conversation_history.extend(fallback.conversation)
        
        # Rank and deduplicate paths
        ranked_paths = self._rank_paths(paths_found, user_afig)
        
        status = "paths_found" if ranked_paths else "no_solutions"
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"✅ AGENT SUMMARY: {len(ranked_paths)} paths in {iteration} steps")
            for i, path in enumerate(ranked_paths, 1):
                print(f"   {i}. {path['summary']}")
            print(f"{'='*60}\n")
        
        return AgentResult(
            status=status,
            gap=gap,
            paths=ranked_paths[:3],
            agent_steps=iteration,
            conversation=conversation_history,
            token_usage=self.token_usage
        )
    
    def _build_system_prompt(
        self,
        product: Dict,
        gap: float,
        budget: float,
        user_afig: Dict
    ) -> str:
        """
        Build an effective system prompt for the agent.
        
        The prompt includes:
        - Clear task description
        - Situation context
        - User profile
        - Available tools and their purposes
        - Strategy guidance
        - Rules and constraints
        """
        income_tier = user_afig.get('income_tier', 'unknown')
        risk_tolerance = user_afig.get('risk_tolerance', 0.5)
        brand_sensitivity = user_afig.get('brand_sensitivity', 0.5)
        
        return f"""You are a Budget Pathfinder Agent. Your job is to help users afford products they want but currently cannot afford.

SITUATION:
- User wants: {product.get('name', 'Unknown Product')} (${product.get('price', 0):.0f})
- User's budget: ${budget:.0f}
- Budget shortfall: ${gap:.0f}
- Product category: {product.get('category', 'unknown')}

USER PROFILE:
- Income tier: {income_tier}
- Risk tolerance: {'high' if risk_tolerance > 0.7 else 'moderate' if risk_tolerance > 0.3 else 'low'}
- Brand sensitivity: {'high' if brand_sensitivity > 0.6 else 'moderate'}

YOUR TASK:
Find 3 creative, realistic ways for the user to afford this product. Think step-by-step and use the available tools strategically.

AVAILABLE TOOLS:
1. check_cart_removals - Find items in cart that could be removed to free budget
2. check_income_projection - Calculate weeks to save based on income tier
3. check_installment_plans - Find payment plan options to spread cost
4. check_refurbished_alternatives - Search for cheaper refurbished/open-box options
5. check_bundle_swaps - Replace expensive cart items with budget alternatives

STRATEGY:
- Start with quick wins (cart removals, refurbished alternatives)
- Then explore time-based solutions (saving, installments)
- Combine approaches if needed (remove item + wait 2 weeks)
- Prioritize paths that work TODAY over long waits
- Consider user's income tier when suggesting solutions

RULES:
1. Each path must be ACTIONABLE and REALISTIC
2. Prefer creative solutions over just "wait and save"
3. Stop when you find 3 viable paths
4. Be concise - think in 1-2 sentences, not paragraphs
5. NEVER suggest illegal, unethical, or predatory lending
6. Always call tools to get real data, don't make up numbers

Start by analyzing the situation and deciding which tool to use first."""
    
    def _get_tool_definitions(self) -> List[Dict]:
        """
        Return OpenAI-compatible function definitions for Groq.
        These define the tools available to the agent.
        """
        return self.tools_instance.get_tool_definitions()
    
    async def _call_llm(self, messages: List[Dict]) -> Any:
        """
        Call Groq API with function calling enabled.
        
        Args:
            messages: Conversation history
            
        Returns:
            Groq API response
        """
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self._get_tool_definitions(),
            tool_choice="auto",  # Let agent decide
            max_tokens=800,
            temperature=0.7  # Some creativity but not random
        )
        
        return response
    
    async def _call_llm_with_retry(
        self,
        messages: List[Dict],
        max_retries: int = 2
    ) -> Any:
        """
        Call LLM with exponential backoff for rate limits.
        
        Args:
            messages: Conversation history
            max_retries: Maximum retry attempts
            
        Returns:
            Groq API response
            
        Raises:
            RateLimitError: If rate limit exceeded after all retries
        """
        for attempt in range(max_retries + 1):
            try:
                response = await self._call_llm(messages)
                return response
            
            except RateLimitError as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # 1s, 2s
                    print(f"⚠️ Rate limit hit, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ Rate limit exceeded after {max_retries} retries")
                    raise
            
            except Exception as e:
                print(f"❌ LLM call failed: {e}")
                raise
    
    async def _execute_tool(
        self,
        tool_name: str,
        args: Dict,
        user_afig: Dict,
        current_cart: List[Dict],
        budget: float,
        gap: float
    ) -> Dict[str, Any]:
        """
        Route tool execution to AgentTools instance.
        
        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments from LLM
            user_afig: User context
            current_cart: Current cart items
            budget: User's budget
            gap: Budget shortfall
            
        Returns:
            Tool result dictionary
        """
        tool_methods = {
            "check_cart_removals": self.tools_instance.check_cart_removals,
            "check_income_projection": self.tools_instance.check_income_projection,
            "check_installment_plans": self.tools_instance.check_installment_plans,
            "check_refurbished_alternatives": self.tools_instance.check_refurbished_alternatives,
            "check_bundle_swaps": self.tools_instance.check_bundle_swaps
        }
        
        method = tool_methods.get(tool_name)
        if not method:
            return {
                "viable": False,
                "error": f"Unknown tool: {tool_name}",
                "summary": "Tool not found"
            }
        
        try:
            # Call tool with full context
            result = await method(
                args=args,
                user_afig=user_afig,
                current_cart=current_cart,
                budget=budget,
                gap=gap
            )
            
            # Validate result format
            required_fields = ["viable", "summary"]
            for field in required_fields:
                if field not in result:
                    result[field] = False if field == "viable" else "Unknown"
            
            return result
        
        except Exception as e:
            print(f"❌ Tool execution error: {e}")
            return {
                "viable": False,
                "error": str(e),
                "summary": f"Tool '{tool_name}' failed: {str(e)[:100]}"
            }
    
    async def _run_rule_based_agent(
        self,
        product: Dict,
        user_afig: Dict,
        current_cart: List[Dict],
        budget: float,
        gap: float
    ) -> AgentResult:
        """
        Fallback rule-based agent when LLM is unavailable.
        
        Systematically tries each tool and collects viable paths.
        """
        conversation_history = [{"step": 1, "type": "think", "content": "Using rule-based fallback agent"}]
        paths_found = []
        
        # Strategy 1: Check cart removals (if cart has items)
        if current_cart:
            result = await self.tools_instance.check_cart_removals(
                args={"min_savings_needed": gap * 0.5},
                user_afig=user_afig,
                current_cart=current_cart,
                budget=budget,
                gap=gap
            )
            conversation_history.append({
                "step": 1,
                "type": "action",
                "tool": "check_cart_removals",
                "result": result
            })
            if result.get("viable"):
                paths_found.append(result)
        
        # Strategy 2: Check refurbished alternatives
        category = product.get("category", "laptops")
        result = await self.tools_instance.check_refurbished_alternatives(
            args={"product_category": category, "max_price": budget},
            user_afig=user_afig,
            current_cart=current_cart,
            budget=budget,
            gap=gap
        )
        conversation_history.append({
            "step": 2,
            "type": "action",
            "tool": "check_refurbished_alternatives",
            "result": result
        })
        if result.get("viable"):
            paths_found.append(result)
        
        # Strategy 3: Check installment plans
        price = product.get("price", 0)
        result = await self.tools_instance.check_installment_plans(
            args={"product_price": price},
            user_afig=user_afig,
            budget=budget,
            gap=gap
        )
        conversation_history.append({
            "step": 3,
            "type": "action",
            "tool": "check_installment_plans",
            "result": result
        })
        if result.get("viable"):
            paths_found.append(result)
        
        # Strategy 4: Check income projection (save and wait)
        result = await self.tools_instance.check_income_projection(
            args={"target_amount": gap},
            user_afig=user_afig,
            budget=budget,
            gap=gap
        )
        conversation_history.append({
            "step": 4,
            "type": "action",
            "tool": "check_income_projection",
            "result": result
        })
        if result.get("viable"):
            paths_found.append(result)
        
        # Strategy 5: Check bundle swaps (if cart has items)
        if current_cart:
            result = await self.tools_instance.check_bundle_swaps(
                args={"savings_target": gap * 0.7},
                user_afig=user_afig,
                current_cart=current_cart,
                budget=budget,
                gap=gap
            )
            conversation_history.append({
                "step": 5,
                "type": "action",
                "tool": "check_bundle_swaps",
                "result": result
            })
            if result.get("viable"):
                paths_found.append(result)
        
        # Rank and return
        ranked_paths = self._rank_paths(paths_found, user_afig)
        status = "paths_found" if ranked_paths else "no_solutions"
        
        return AgentResult(
            status=status,
            gap=gap,
            paths=ranked_paths[:3],
            agent_steps=len([c for c in conversation_history if c["type"] == "action"]),
            conversation=conversation_history
        )
    
    def _rank_paths(self, paths: List[Dict], user_afig: Dict) -> List[Dict]:
        """
        Rank paths by desirability for the user.
        
        Considers:
        - Path type (immediate solutions preferred)
        - Savings amount
        - User's risk tolerance
        - Wait time
        """
        if not paths:
            return []
        
        def score_path(path: Dict) -> float:
            score = 0.0
            path_type = path.get("path_type", "")
            
            # Base scores by path type (prefer immediate solutions)
            type_scores = {
                "refurbished": 10,
                "cart_removal": 8,
                "bundle_swap": 7,
                "installment": 5,
                "save_and_wait": 3
            }
            score += type_scores.get(path_type, 0)
            
            # Bonus for savings
            savings = path.get("savings", 0)
            score += min(savings / 100, 5)  # Up to 5 points for savings
            
            # Penalize long waits
            if path_type == "save_and_wait":
                weeks = path.get("weeks", 0)
                score -= min(weeks, 5)  # Penalty for waiting
            
            # Consider user risk tolerance for installments
            risk = user_afig.get("risk_tolerance", 0.5)
            if path_type == "installment":
                score += risk * 3  # Risk-tolerant users like installments
            
            return score
        
        # Deduplicate by path type
        seen_types = set()
        unique_paths = []
        for path in paths:
            ptype = path.get("path_type", "unknown")
            if ptype not in seen_types:
                seen_types.add(ptype)
                unique_paths.append(path)
        
        # Sort by score
        ranked = sorted(unique_paths, key=score_path, reverse=True)
        return ranked
    
    def get_formatted_trace(self, conversation: List[Dict]) -> str:
        """
        Format conversation trace for UI display.
        
        Args:
            conversation: List of conversation entries
            
        Returns:
            Formatted string for display
        """
        trace_lines = []
        for entry in conversation:
            step = entry.get("step", 0)
            entry_type = entry.get("type", "")
            
            if entry_type == "think":
                content = entry.get("content", "")[:100]
                trace_lines.append(f"🤔 Step {step}: {content}...")
            
            elif entry_type == "action":
                tool = entry.get("tool", "unknown")
                result = entry.get("result", {})
                summary = result.get("summary", "No summary")
                trace_lines.append(f"🔧 Step {step}: Using {tool}")
                trace_lines.append(f"📊 Result: {summary}")
            
            elif entry_type == "error":
                content = entry.get("content", "")
                trace_lines.append(f"❌ Step {step}: Error - {content}")
        
        return "\n".join(trace_lines)
    
    def get_token_usage(self) -> Dict[str, Any]:
        """
        Get token usage statistics.
        
        Returns:
            Dict with token counts and estimated cost
        """
        total = self.token_usage["prompt"] + self.token_usage["completion"]
        return {
            "total_tokens": total,
            "prompt_tokens": self.token_usage["prompt"],
            "completion_tokens": self.token_usage["completion"],
            "estimated_cost": total * 0.00001  # Rough estimate
        }


# =============================================================================
# TEST RUNNER
# =============================================================================

async def _test_agent():
    """Test the Budget Pathfinder Agent with a realistic scenario."""
    print("🧪 Testing Budget Pathfinder Agent...\n")
    
    agent = BudgetPathfinderAgent(verbose=True)
    
    product = {
        "name": "MacBook Pro M3",
        "price": 2499,
        "category": "laptops"
    }
    
    user_afig = {
        "income_tier": "medium",
        "risk_tolerance": 0.6,
        "brand_sensitivity": 0.5
    }
    
    current_cart = [
        {"name": "Logitech MX Master 3", "price": 89, "category": "mice", "optional": True},
        {"name": "USB-C Hub", "price": 45, "category": "accessories"}
    ]
    
    budget = 1500
    
    print(f"📊 Test Scenario:")
    print(f"   Product: {product['name']} (${product['price']})")
    print(f"   Budget: ${budget}")
    print(f"   Gap: ${product['price'] - budget}")
    print(f"   Cart items: {len(current_cart)}")
    
    result = await agent.find_affordability_paths(
        product=product,
        user_afig=user_afig,
        current_cart=current_cart,
        budget=budget
    )
    
    print(f"\n📊 Result: {result['status']}")
    print(f"   Gap: ${result['gap']:.0f}")
    print(f"   Paths found: {len(result['paths'])}")
    print(f"   Agent steps: {result['agent_steps']}")
    
    for i, path in enumerate(result['paths'], 1):
        print(f"\n   Path {i}: {path['path_type'].upper()}")
        print(f"      Summary: {path['summary']}")
        print(f"      Action: {path['action']}")
        print(f"      Trade-off: {path['trade_off']}")
    
    print("\n✅ Agent test complete!")


if __name__ == "__main__":
    asyncio.run(_test_agent())
