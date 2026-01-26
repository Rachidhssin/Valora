# 🧭 Budget Pathfinder Agent

> **ReAct-style AI agent that finds creative affordability paths when users face budget shortfalls**

The Budget Pathfinder Agent is the "wow factor" of FinBundle's hackathon demo. When a user wants a product but can't quite afford it, this agent uses AI-powered reasoning to find 3 creative, actionable paths to make the purchase possible.

## 🎯 Overview

Traditional e-commerce shows "insufficient funds" and ends there. FinBundle's agent instead:

1. **Analyzes** the user's financial situation (AFIG profile)
2. **Explores** multiple affordability strategies using specialized tools
3. **Recommends** the 3 best paths tailored to the user's profile
4. **Explains** the trade-offs for each path

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Budget Pathfinder Agent                   │
├─────────────────────────────────────────────────────────────┤
│  ReAct Loop (Think → Act → Observe)                         │
│  ┌─────────┐    ┌──────────┐    ┌───────────┐              │
│  │  THINK  │───►│   ACT    │───►│  OBSERVE  │───┐          │
│  │         │    │ (tools)  │    │           │   │          │
│  └─────────┘    └──────────┘    └───────────┘   │          │
│       ▲                                          │          │
│       └──────────────────────────────────────────┘          │
├─────────────────────────────────────────────────────────────┤
│  Tools Layer                                                 │
│  ┌──────────────┐ ┌────────────────┐ ┌─────────────────┐   │
│  │Cart Removals │ │Income Projection│ │Installment Plans│   │
│  └──────────────┘ └────────────────┘ └─────────────────┘   │
│  ┌──────────────────┐ ┌───────────────┐                     │
│  │Refurb Alternatives│ │ Bundle Swaps  │                     │
│  └──────────────────┘ └───────────────┘                     │
├─────────────────────────────────────────────────────────────┤
│  External Services                                           │
│  ┌──────────┐    ┌──────────┐                               │
│  │ Groq API │    │  Qdrant  │                               │
│  │ (LLM)    │    │ (Vector) │                               │
│  └──────────┘    └──────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Components

### `agent/tools.py` - The 5 Agent Tools

| Tool | Purpose | Output |
|------|---------|--------|
| `check_cart_removals` | Find optional items in cart to remove | Items sorted by optionality |
| `check_income_projection` | Calculate save-and-wait timeline | Weeks to save, weekly savings |
| `check_installment_plans` | Find payment plan options | Affirm/Klarna/PayPal plans |
| `check_refurbished_alternatives` | Search for cheaper alternatives | Open-box/refurb products |
| `check_bundle_swaps` | Replace expensive items with budget versions | Swap suggestions |

### `agent/budget_agent.py` - The ReAct Agent

The main agent orchestrates tools using the ReAct pattern:

- **Groq API** with `llama-3.1-8b-instant` for reasoning
- **Function calling** for structured tool invocation
- **Rule-based fallback** when LLM is unavailable
- **Token tracking** for cost monitoring

## 🚀 Quick Start

### Prerequisites

```bash
pip install groq qdrant-client python-dotenv
```

### Environment Variables

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here
QDRANT_URL=http://localhost:6333  # Optional
```

### Basic Usage

```python
import asyncio
from agent.budget_agent import BudgetPathfinderAgent

async def main():
    agent = BudgetPathfinderAgent(verbose=True)
    
    result = await agent.find_affordability_paths(
        product={
            "name": "MacBook Pro M3",
            "price": 2499,
            "category": "laptops"
        },
        user_afig={
            "income_tier": "medium",
            "risk_tolerance": 0.6,
            "brand_sensitivity": 0.5
        },
        current_cart=[
            {"name": "USB-C Hub", "price": 45, "category": "accessories"},
            {"name": "Mouse", "price": 89, "category": "mice"}
        ],
        budget=1500
    )
    
    print(f"Status: {result['status']}")
    print(f"Gap: ${result['gap']:.0f}")
    
    for i, path in enumerate(result['paths'], 1):
        print(f"\nPath {i}: {path['path_type']}")
        print(f"  Summary: {path['summary']}")
        print(f"  Action: {path['action']}")
        print(f"  Trade-off: {path['trade_off']}")

asyncio.run(main())
```

### Run the Test

```bash
python -m agent.budget_agent
```

## 📊 Standardized Output Format

All tools return a consistent format:

```python
{
    "viable": True,                    # Is this path feasible?
    "path_type": "refurbished",        # Type of solution
    "summary": "Save $200 with...",    # One-line summary
    "action": "Choose the refurb...",  # What user should do
    "trade_off": "May have minor...",  # What user gives up
    "savings": 200,                    # Dollars saved (if applicable)
    # ... additional tool-specific fields
}
```

### Path Types

| Type | Description |
|------|-------------|
| `cart_removal` | Remove optional items from cart |
| `save_and_wait` | Save from income over weeks |
| `installment` | Split payment over months |
| `refurbished` | Buy open-box/refurbished alternative |
| `bundle_swap` | Replace items with cheaper versions |

## 🔧 Configuration

### Income Tiers

The agent uses income tiers to calculate savings projections:

```python
INCOME_CONFIGS = {
    "low": IncomeConfig(weekly_income=400, savings_rate=0.15),
    "medium": IncomeConfig(weekly_income=600, savings_rate=0.20),
    "high": IncomeConfig(weekly_income=1000, savings_rate=0.25)
}
```

### Category Optionality

Items are scored by how "optional" they are for cart removal:

```python
CATEGORY_OPTIONALITY = {
    "mice": 0.8,        # Very optional
    "keyboards": 0.75,
    "headphones": 0.7,
    "webcams": 0.85,
    "monitors": 0.5,
    "accessories": 0.9,  # Most optional
    "laptops": 0.1,      # Essential
    "smartphones": 0.1   # Essential
}
```

## 🧪 Testing

Run the test suite:

```bash
# All tests
pytest tests/test_agent.py -v

# Specific test class
pytest tests/test_agent.py::TestCheckCartRemovals -v

# With coverage
pytest tests/test_agent.py --cov=agent --cov-report=term-missing
```

## 🎭 Demo Scenarios

### Scenario 1: Student Budget

```python
result = await agent.find_affordability_paths(
    product={"name": "MacBook Air", "price": 1299, "category": "laptops"},
    user_afig={"income_tier": "low", "risk_tolerance": 0.3},
    current_cart=[
        {"name": "AirPods Pro", "price": 249, "category": "headphones"},
        {"name": "Magic Mouse", "price": 99, "category": "mice"}
    ],
    budget=800
)
# Expected paths:
# 1. Cart Removal: Remove AirPods Pro ($249) + Mouse ($99) = $348 freed
# 2. Refurbished: Find certified refurbished at $999
# 3. Save & Wait: Save $120/week → 4 weeks to close gap
```

### Scenario 2: Flexible Buyer

```python
result = await agent.find_affordability_paths(
    product={"name": "4K Monitor", "price": 699, "category": "monitors"},
    user_afig={"income_tier": "high", "risk_tolerance": 0.8},
    current_cart=[],
    budget=500
)
# Expected paths:
# 1. Refurbished: Open-box at $499
# 2. Installment: 4 months × $175 via Affirm
# 3. Save & Wait: 1 week with high income
```

## 🚨 Error Handling

The agent handles various error conditions:

| Error | Handling |
|-------|----------|
| Groq rate limit | Exponential backoff with 2 retries |
| Tool execution failure | Returns error in result, continues |
| No paths found | Returns `"status": "no_solutions"` |
| Budget >= Price | Returns `"status": "no_gap"` |
| API timeout | 30s timeout per agent run |

## 📈 Metrics & Tracing

Access detailed agent traces for debugging:

```python
result = await agent.find_affordability_paths(...)

# Get formatted trace
trace = agent.get_formatted_trace(result['conversation'])
print(trace)
# 🤔 Step 1: Analyzing budget shortfall of $999...
# 🔧 Step 2: Using check_cart_removals
# 📊 Result: Found 2 removable items totaling $134

# Get token usage
usage = agent.get_token_usage()
print(f"Total tokens: {usage['total_tokens']}")
print(f"Estimated cost: ${usage['estimated_cost']:.4f}")
```

## 🔌 API Integration

The agent is designed for easy API integration:

```python
from fastapi import FastAPI
from agent.budget_agent import BudgetPathfinderAgent

app = FastAPI()
agent = BudgetPathfinderAgent()

@app.post("/api/find-paths")
async def find_paths(request: PathRequest):
    result = await agent.find_affordability_paths(
        product=request.product,
        user_afig=request.user_afig,
        current_cart=request.cart,
        budget=request.budget
    )
    return result
```

## 🔮 Future Enhancements

- [ ] Add `check_competitor_prices` tool
- [ ] Add `check_cashback_offers` tool
- [ ] Multi-agent collaboration for complex scenarios
- [ ] Learning from user feedback
- [ ] Price history integration

## 📝 License

MIT License - see [LICENSE](../LICENSE)

---

**Built for FinBundle @ Hackathon 2024** 🚀
