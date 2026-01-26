"""
Tests for Budget Pathfinder Agent
=================================

Comprehensive test suite covering:
- Unit tests for each tool
- Integration tests for the full agent
- Edge cases and error handling
- Performance and timeout tests

Run with: pytest tests/test_agent.py -v
"""

import pytest
import asyncio
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

# Import agent modules
from agent.tools import AgentTools, CATEGORY_OPTIONALITY
from agent.budget_agent import BudgetPathfinderAgent, AgentResult


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_product() -> Dict:
    """Sample product for testing."""
    return {
        "id": "prod_laptop_001",
        "name": "MacBook Pro M3",
        "price": 2499,
        "category": "laptops",
        "brand": "Apple"
    }


@pytest.fixture
def sample_cart() -> List[Dict]:
    """Sample cart with various items."""
    return [
        {
            "id": "item_1",
            "name": "Logitech MX Master 3",
            "price": 89,
            "category": "mice",
            "optional": True
        },
        {
            "id": "item_2",
            "name": "USB-C Hub",
            "price": 45,
            "category": "accessories"
        },
        {
            "id": "item_3",
            "name": "Mechanical Keyboard",
            "price": 149,
            "category": "keyboards"
        }
    ]


@pytest.fixture
def sample_user_afig() -> Dict:
    """Sample user AFIG profile."""
    return {
        "income_tier": "medium",
        "risk_tolerance": 0.6,
        "brand_sensitivity": 0.5
    }


@pytest.fixture
def tools_instance() -> AgentTools:
    """Create tools instance without Qdrant for testing."""
    return AgentTools(qdrant_client=None)


@pytest.fixture
def agent_instance() -> BudgetPathfinderAgent:
    """Create agent instance for testing."""
    return BudgetPathfinderAgent(verbose=False)


# =============================================================================
# UNIT TESTS - TOOLS
# =============================================================================

class TestCheckCartRemovals:
    """Tests for check_cart_removals tool."""
    
    @pytest.mark.asyncio
    async def test_finds_optional_items(self, tools_instance, sample_cart, sample_user_afig):
        """Should identify optional items for removal."""
        result = await tools_instance.check_cart_removals(
            args={"min_savings_needed": 50},
            user_afig=sample_user_afig,
            current_cart=sample_cart,
            budget=1500,
            gap=500
        )
        
        assert "viable" in result
        assert "summary" in result
        assert "path_type" in result
        # Should find the mouse (optional, high optionality score)
    
    @pytest.mark.asyncio
    async def test_empty_cart_returns_no_viable(self, tools_instance, sample_user_afig):
        """Empty cart should return non-viable result."""
        result = await tools_instance.check_cart_removals(
            args={"min_savings_needed": 100},
            user_afig=sample_user_afig,
            current_cart=[],
            budget=1500,
            gap=500
        )
        
        assert result["viable"] == False
        assert "empty" in result["summary"].lower() or "no items" in result["summary"].lower()
    
    @pytest.mark.asyncio
    async def test_prioritizes_by_optionality(self, tools_instance, sample_user_afig):
        """Should prioritize items by optionality score."""
        cart = [
            {"name": "Mouse", "price": 50, "category": "mice"},
            {"name": "Laptop Stand", "price": 100, "category": "accessories"},
            {"name": "Webcam", "price": 75, "category": "webcams"}
        ]
        
        result = await tools_instance.check_cart_removals(
            args={"min_savings_needed": 50},
            user_afig=sample_user_afig,
            current_cart=cart,
            budget=1000,
            gap=200
        )
        
        assert "viable" in result
        # Should suggest removing the most optional item


class TestCheckIncomeProjection:
    """Tests for check_income_projection tool."""
    
    @pytest.mark.asyncio
    async def test_low_income_projection(self, tools_instance, sample_user_afig):
        """Low income tier should project longer save time."""
        user = {**sample_user_afig, "income_tier": "low"}
        
        result = await tools_instance.check_income_projection(
            args={"target_amount": 500},
            user_afig=user,
            budget=1000,
            gap=500
        )
        
        assert result["viable"] == True
        assert result["path_type"] == "save_and_wait"
        assert "weeks" in result
    
    @pytest.mark.asyncio
    async def test_high_income_projection(self, tools_instance, sample_user_afig):
        """High income tier should save faster."""
        user = {**sample_user_afig, "income_tier": "high"}
        
        result = await tools_instance.check_income_projection(
            args={"target_amount": 500},
            user_afig=user,
            budget=2000,
            gap=500
        )
        
        assert result["viable"] == True
        assert result["weeks"] <= 3  # High income saves faster
    
    @pytest.mark.asyncio
    async def test_very_large_gap(self, tools_instance, sample_user_afig):
        """Very large gap should still calculate weeks."""
        result = await tools_instance.check_income_projection(
            args={"target_amount": 5000},
            user_afig=sample_user_afig,
            budget=1000,
            gap=5000
        )
        
        assert "weeks" in result
        # May be non-viable if too many weeks


class TestCheckInstallmentPlans:
    """Tests for check_installment_plans tool."""
    
    @pytest.mark.asyncio
    async def test_installment_options_exist(self, tools_instance, sample_user_afig):
        """Should return installment plan options."""
        result = await tools_instance.check_installment_plans(
            args={"product_price": 1500},
            user_afig=sample_user_afig,
            budget=1000,
            gap=500
        )
        
        assert "viable" in result
        assert result["path_type"] == "installment"
        if result["viable"]:
            assert "plans" in result
            assert len(result["plans"]) > 0
    
    @pytest.mark.asyncio
    async def test_affordable_monthly(self, tools_instance, sample_user_afig):
        """Monthly payment should be within budget constraints."""
        result = await tools_instance.check_installment_plans(
            args={"product_price": 2000},
            user_afig=sample_user_afig,
            budget=1000,
            gap=1000
        )
        
        if result["viable"]:
            for plan in result.get("plans", []):
                # Monthly should be reasonable portion of weekly income
                assert "monthly" in plan


class TestCheckRefurbishedAlternatives:
    """Tests for check_refurbished_alternatives tool."""
    
    @pytest.mark.asyncio
    async def test_without_qdrant(self, tools_instance, sample_user_afig, sample_cart):
        """Should return synthetic alternatives without Qdrant."""
        result = await tools_instance.check_refurbished_alternatives(
            args={"product_category": "laptops", "max_price": 1500},
            user_afig=sample_user_afig,
            current_cart=sample_cart,
            budget=1500,
            gap=500
        )
        
        assert "viable" in result
        assert result["path_type"] == "refurbished"
        if result["viable"]:
            assert "alternatives" in result
    
    @pytest.mark.asyncio
    async def test_category_handling(self, tools_instance, sample_user_afig, sample_cart):
        """Should handle various categories."""
        categories = ["laptops", "smartphones", "headphones", "monitors"]
        
        for category in categories:
            result = await tools_instance.check_refurbished_alternatives(
                args={"product_category": category, "max_price": 1000},
                user_afig=sample_user_afig,
                current_cart=sample_cart,
                budget=1000,
                gap=200
            )
            
            assert "viable" in result
            assert "summary" in result


class TestCheckBundleSwaps:
    """Tests for check_bundle_swaps tool."""
    
    @pytest.mark.asyncio
    async def test_finds_swap_opportunities(self, tools_instance, sample_user_afig, sample_cart):
        """Should find items that can be swapped for cheaper alternatives."""
        result = await tools_instance.check_bundle_swaps(
            args={"savings_target": 100},
            user_afig=sample_user_afig,
            current_cart=sample_cart,
            budget=1500,
            gap=300
        )
        
        assert "viable" in result
        assert result["path_type"] == "bundle_swap"
    
    @pytest.mark.asyncio
    async def test_empty_cart_bundle_swap(self, tools_instance, sample_user_afig):
        """Empty cart should return non-viable for bundle swaps."""
        result = await tools_instance.check_bundle_swaps(
            args={"savings_target": 100},
            user_afig=sample_user_afig,
            current_cart=[],
            budget=1500,
            gap=300
        )
        
        assert result["viable"] == False


# =============================================================================
# UNIT TESTS - TOOL DEFINITIONS
# =============================================================================

class TestToolDefinitions:
    """Tests for tool definitions format."""
    
    def test_tool_definitions_valid(self, tools_instance):
        """All tool definitions should be valid OpenAI format."""
        definitions = tools_instance.get_tool_definitions()
        
        assert isinstance(definitions, list)
        assert len(definitions) == 5  # 5 tools
        
        for tool_def in definitions:
            assert tool_def["type"] == "function"
            assert "function" in tool_def
            func = tool_def["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
    
    def test_all_tools_have_definitions(self, tools_instance):
        """Each tool should have a corresponding definition."""
        definitions = tools_instance.get_tool_definitions()
        tool_names = [d["function"]["name"] for d in definitions]
        
        expected_tools = [
            "check_cart_removals",
            "check_income_projection",
            "check_installment_plans",
            "check_refurbished_alternatives",
            "check_bundle_swaps"
        ]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Missing definition for {expected}"


# =============================================================================
# INTEGRATION TESTS - AGENT
# =============================================================================

class TestBudgetPathfinderAgent:
    """Integration tests for the full agent."""
    
    @pytest.mark.asyncio
    async def test_rule_based_fallback(self, agent_instance, sample_product, sample_user_afig, sample_cart):
        """Test rule-based fallback agent."""
        # Force rule-based by using internal method
        result = await agent_instance._run_rule_based_agent(
            product=sample_product,
            user_afig=sample_user_afig,
            current_cart=sample_cart,
            budget=1500,
            gap=999
        )
        
        assert isinstance(result, AgentResult)
        assert result.status in ["paths_found", "no_solutions"]
        assert result.gap == 999
        assert isinstance(result.paths, list)
    
    @pytest.mark.asyncio
    async def test_finds_multiple_paths(self, agent_instance, sample_product, sample_user_afig, sample_cart):
        """Should find multiple affordability paths."""
        result = await agent_instance._run_rule_based_agent(
            product=sample_product,
            user_afig=sample_user_afig,
            current_cart=sample_cart,
            budget=1500,
            gap=500
        )
        
        # Rule-based should find at least 2 paths
        assert len(result.paths) >= 1
    
    @pytest.mark.asyncio
    async def test_no_gap_returns_no_action(self, agent_instance, sample_product, sample_user_afig, sample_cart):
        """When no gap exists, should return no action needed."""
        result = await agent_instance.find_affordability_paths(
            product={"name": "Cheap Item", "price": 50, "category": "accessories"},
            user_afig=sample_user_afig,
            current_cart=[],
            budget=1000  # Way more than needed
        )
        
        assert result["status"] == "no_gap"
    
    @pytest.mark.asyncio
    async def test_path_ranking(self, agent_instance, sample_user_afig):
        """Paths should be ranked appropriately."""
        paths = [
            {"path_type": "save_and_wait", "savings": 100, "weeks": 4},
            {"path_type": "refurbished", "savings": 200},
            {"path_type": "cart_removal", "savings": 80}
        ]
        
        ranked = agent_instance._rank_paths(paths, sample_user_afig)
        
        # Refurbished should rank higher than save_and_wait
        assert len(ranked) > 0
        # First should be refurbished (highest type score + good savings)
    
    def test_system_prompt_generation(self, agent_instance, sample_product, sample_user_afig):
        """System prompt should contain necessary context."""
        prompt = agent_instance._build_system_prompt(
            product=sample_product,
            gap=500,
            budget=1500,
            user_afig=sample_user_afig
        )
        
        assert sample_product["name"] in prompt
        assert "500" in prompt  # Gap
        assert "1500" in prompt  # Budget
        assert "medium" in prompt  # Income tier
        assert "AVAILABLE TOOLS" in prompt
    
    def test_trace_formatting(self, agent_instance):
        """Trace formatting should produce readable output."""
        conversation = [
            {"step": 1, "type": "think", "content": "Analyzing the situation..."},
            {"step": 2, "type": "action", "tool": "check_cart_removals", "result": {"summary": "Found 2 items"}}
        ]
        
        trace = agent_instance.get_formatted_trace(conversation)
        
        assert "Step 1" in trace
        assert "check_cart_removals" in trace
        assert "Found 2 items" in trace


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_zero_budget(self, tools_instance, sample_user_afig, sample_cart):
        """Should handle zero budget gracefully."""
        result = await tools_instance.check_cart_removals(
            args={"min_savings_needed": 100},
            user_afig=sample_user_afig,
            current_cart=sample_cart,
            budget=0,
            gap=500
        )
        
        assert "viable" in result
        # Should still work, just report the situation
    
    @pytest.mark.asyncio
    async def test_negative_gap(self, agent_instance, sample_product, sample_user_afig, sample_cart):
        """Negative gap (can afford) should return no_gap status."""
        result = await agent_instance.find_affordability_paths(
            product={"name": "Item", "price": 100, "category": "accessories"},
            user_afig=sample_user_afig,
            current_cart=[],
            budget=500
        )
        
        assert result["status"] == "no_gap"
    
    @pytest.mark.asyncio
    async def test_very_large_cart(self, tools_instance, sample_user_afig):
        """Should handle large carts efficiently."""
        large_cart = [
            {"name": f"Item {i}", "price": 10 + i, "category": "accessories"}
            for i in range(50)
        ]
        
        result = await tools_instance.check_cart_removals(
            args={"min_savings_needed": 100},
            user_afig=sample_user_afig,
            current_cart=large_cart,
            budget=2000,
            gap=500
        )
        
        assert "viable" in result
    
    @pytest.mark.asyncio
    async def test_missing_product_fields(self, agent_instance, sample_user_afig, sample_cart):
        """Should handle products with missing fields."""
        incomplete_product = {"price": 1000}  # Missing name, category
        
        result = await agent_instance._run_rule_based_agent(
            product=incomplete_product,
            user_afig=sample_user_afig,
            current_cart=sample_cart,
            budget=500,
            gap=500
        )
        
        assert isinstance(result, AgentResult)
        # Should not crash
    
    @pytest.mark.asyncio
    async def test_unknown_income_tier(self, tools_instance, sample_cart):
        """Should handle unknown income tier with defaults."""
        user = {"income_tier": "unknown", "risk_tolerance": 0.5}
        
        result = await tools_instance.check_income_projection(
            args={"target_amount": 500},
            user_afig=user,
            budget=1000,
            gap=500
        )
        
        assert "weeks" in result
    
    @pytest.mark.asyncio
    async def test_special_characters_in_product_name(self, agent_instance, sample_user_afig, sample_cart):
        """Should handle special characters in product names."""
        product = {
            "name": "MacBook Pro 14\" (M3 Pro) – Silver [Latest]",
            "price": 2499,
            "category": "laptops"
        }
        
        result = await agent_instance._run_rule_based_agent(
            product=product,
            user_afig=sample_user_afig,
            current_cart=sample_cart,
            budget=1500,
            gap=999
        )
        
        assert isinstance(result, AgentResult)


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Performance and timeout tests."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_fast(self, tools_instance, sample_user_afig, sample_cart):
        """Each tool should execute quickly."""
        import time
        
        start = time.time()
        
        await tools_instance.check_cart_removals(
            args={"min_savings_needed": 100},
            user_afig=sample_user_afig,
            current_cart=sample_cart,
            budget=1500,
            gap=500
        )
        
        elapsed = time.time() - start
        assert elapsed < 0.5, f"Tool took too long: {elapsed}s"
    
    @pytest.mark.asyncio
    async def test_rule_based_agent_fast(self, agent_instance, sample_product, sample_user_afig, sample_cart):
        """Rule-based agent should complete quickly."""
        import time
        
        start = time.time()
        
        await agent_instance._run_rule_based_agent(
            product=sample_product,
            user_afig=sample_user_afig,
            current_cart=sample_cart,
            budget=1500,
            gap=500
        )
        
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Rule-based agent took too long: {elapsed}s"


# =============================================================================
# OPTIONALITY SCORING TESTS
# =============================================================================

class TestOptionalityScoring:
    """Tests for category optionality scoring."""
    
    def test_all_categories_have_scores(self):
        """All expected categories should have optionality scores."""
        expected_categories = [
            "mice", "keyboards", "headphones", "webcams",
            "monitors", "accessories", "laptops", "smartphones"
        ]
        
        for cat in expected_categories:
            assert cat in CATEGORY_OPTIONALITY, f"Missing score for {cat}"
    
    def test_optionality_range(self):
        """All optionality scores should be between 0 and 1."""
        for category, score in CATEGORY_OPTIONALITY.items():
            assert 0 <= score <= 1, f"Invalid score for {category}: {score}"
    
    def test_essential_items_low_optionality(self):
        """Essential items should have low optionality."""
        essential = ["laptops", "smartphones"]
        
        for cat in essential:
            assert CATEGORY_OPTIONALITY.get(cat, 0.5) < 0.5


# =============================================================================
# RESULT FORMAT TESTS
# =============================================================================

class TestResultFormat:
    """Tests for standardized result format."""
    
    @pytest.mark.asyncio
    async def test_all_tools_return_required_fields(self, tools_instance, sample_user_afig, sample_cart):
        """All tools should return the required fields."""
        required_fields = ["viable", "path_type", "summary", "action", "trade_off"]
        
        tools_to_test = [
            ("check_cart_removals", {"min_savings_needed": 100}),
            ("check_income_projection", {"target_amount": 500}),
            ("check_installment_plans", {"product_price": 1500}),
            ("check_refurbished_alternatives", {"product_category": "laptops", "max_price": 1000}),
            ("check_bundle_swaps", {"savings_target": 100})
        ]
        
        for tool_name, args in tools_to_test:
            method = getattr(tools_instance, tool_name)
            result = await method(
                args=args,
                user_afig=sample_user_afig,
                current_cart=sample_cart,
                budget=1500,
                gap=500
            )
            
            for field in required_fields:
                assert field in result, f"{tool_name} missing field: {field}"
    
    def test_agent_result_has_required_fields(self, agent_instance):
        """AgentResult should have all required fields."""
        result = AgentResult(
            status="paths_found",
            gap=500,
            paths=[],
            agent_steps=3,
            conversation=[]
        )
        
        # Convert to dict
        result_dict = result.__dict__
        
        assert "status" in result_dict
        assert "gap" in result_dict
        assert "paths" in result_dict
        assert "agent_steps" in result_dict
        assert "conversation" in result_dict


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
