# 🛒 Valora

**Valora: An Adaptive, Privacy-Aware Financial Intent Engine for E-Commerce**

Valora is not just a search engine; it is a **Financial DecisionOS** for modern commerce. It fundamentally shifts the paradigm from "keyword matching" to **"Financial Intent Reconciliation."** By leveraging a novel three-tier intent graph (AFIG) and a Constraint Programming solver, Valora delivers mathematically optimized product bundles that respect user budgets down to the cent.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-18.2-61DAFB.svg?style=flat&logo=react&logoColor=black)
![Qdrant](https://img.shields.io/badge/Qdrant-v1.13+-d91d52.svg?style=flat&logo=qdrant&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg?style=flat&logo=fastapi&logoColor=white)
![OR-Tools](https://img.shields.io/badge/OR--Tools-9.7+-4285F4.svg?style=flat&logo=google&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Llama--3-f55036.svg?style=flat)



## 🎯 1. Project Overview & Objectives

### The Problem
Traditional e-commerce filtering is broken. A user searching for a "video editing setup for $2000" is forced to manually search for a laptop, monitor, and mouse separately, doing mental math to stay within budget. This cognitive load leads to decision paralysis and cart abandonment.

### The Solution: Valora
Valora introduces **Financial Intent Recognition** as a core architectural component.

#### Key Objectives:
1.  **Adaptive Financial Intent Graph (AFIG)**:
    *   **What it is**: A probabilistic graphical model that reconciles three layers of user intent without using persistent PII.
    *   **How it works**: It continuously updates a user's profile (Stable, Situational, Behavioral) based on real-time signals like dwell time and price volatility interactions.
    *   **Goal**: To dynamically adjust search ranking weights based on whether a user is a "Value Seeker" or a "Quality Maximizer."

2.  **Constraint-Based Bundle Optimization**:
    *   **What it is**: Instead of greedy heuristics, we use **Google OR-Tools CP-SAT (Constraint Programming)** to solve the bundling problem as a Mixed-Integer Linear Program (MILP).
    *   **Goal**: To find the *mathematically optimal* combination of products that maximizes utility while strictly adhering to the user's budget.

3.  **Privacy-First Architecture**:
    *   **What it is**: All personalization happens via local vector reconciliation.
    *   **Goal**: To provide hyper-personalization without compromising user privacy.

---

## 🏗️ 2. Deep Architecture & Hierarchy

Valora employs a **Three-Path Architecture** to optimize for latency vs. complexity.

### High-Level System Architecture

```mermaid
graph TD
    User[User] -->|React Frontend| FE[Gateway: Valora Web App]
    FE -->|JSON/REST| API[FastAPI Orchestrator]
    
    subgraph "Core Decision Engine"
        API --> Router{Three-Path Router}
        
        Router -->|Low Complexity| Path1[⚡ Fast Path]
        Router -->|Med Complexity| Path2[🧠 Smart Path]
        Router -->|High Complexity| Path3[🧩 Deep Path]
        
        Path1 --"KV Lookup"--> Cache[(Redis/Postgres)]
        Path2 --"Vector Search"--> Hybrid[Hybrid Search Engine]
        Path3 --"Graph Analysis"--> AFIG[AFIG Engine]
        Path3 --"MILP Solver"--> Opt[Bundle Optimizer]
    end
    
    subgraph "Intelligence Layer"
        Hybrid --"ACORN Filter"--> Qdrant[(Qdrant Vector DB)]
        Opt --"Candidate Retrieval"--> Qdrant
        AFIG --"Intent Profile"--> DB[(User Intent DB)]
    end
```

### System Component Breakdown

1.  **Front-End Layer (React + Vite)**
    *   Handles user interactions and visualizes complex data like the analytics dashboard.
    *   Manages ephemeral state for instantaneous feedback.

2.  **Orchestration Layer (FastAPI)**
    *   **Router**: Acts as a traffic controller, deciding if a query needs a simple cache lookup, a smart vector search, or a deep optimization process.
    *   **AFIG Engine**: Manages the user's financial state and preferences.

3.  **Retrieval Layer (Qdrant)**
    *   **Hybrid Search**: Combines keyword matching with semantic understanding.
    *   **Filtering**: Applies hard constraints layout constraints before ranking.

4.  **Optimization Layer (OR-Tools)**
    *   **Solver**: Takes thousands of candidate products and finds the single best combination that fits the budget.

---

## 🔄 3. Data Flow & ReAct Agents

Valora is not just a search engine; it includes autonomous agents that help users negotiate affordability.

### A. End-to-End Data Flow

From user keystroke to final product recommendation, data flows through strictly defined pipelined stages.

```mermaid
sequenceDiagram
    participant U as User
    participant G as Gateway (API)
    participant E as Router
    participant S as Search Engine
    participant Q as Qdrant
    participant O as Bundle Optimizer

    U->>G: Search "Pro Gaming Setup < $2000"
    G->>E: Calculate Complexity Score
    E-->>S: Route to Deep Path (Score > 0.6)
    
    Note over S,Q: Phase 1: Retrieval
    S->>Q: Parallel Queries (384-dim vectors)
    Q-->>S: Return Top 50 for [GPU, CPU, Monitor]
    
    Note over S,O: Phase 2: Optimization
    S->>O: Solve Mixed-Integer Linear Program
    O-->>S: Optimal Bundle (Cost: $1985)
    
    S->>G: Return Bundle + AFIG Metadata
    G->>U: Display "Perfect Match"
```

### B. The Budget Pathfinder Agent (ReAct)

When a user cannot afford a product (`Price > Budget`), the **Budget Pathfinder Agent** activates. It uses the **ReAct (Reasoning + Acting)** pattern to autonomously find a solution.

**How Qdrant Enables This**: The agent checks "Refurbished Alternatives" by querying Qdrant with specific payload filters (`condition: refurbished`) and price range constraints (`price < gap`).

```mermaid
stateDiagram-v2
    [*] --> THINK: Price > Budget
    
    state THINK {
        [*] --> Analyze
        Analyze --> SelectTools
    }
    
    THINK --> ACT: Call Tools
    
    state ACT {
        [*] --> Tool1
        Tool1 --> QdrantQuery: check_refurbished
        Tool1 --> CartAnalysis: check_removals
        QdrantQuery --> ToolResult
    }
    
    ACT --> OBSERVE: Process Results
    
    state OBSERVE {
        ToolResult --> Evaluate
        Evaluate --> [*]: Solution Found?
    }
    
    OBSERVE --> THINK: No -> Retry (Max 5)
    OBSERVE --> [*]: Yes -> Suggest 3 Paths
```

*   **THINK**: "The user is short $200. I should look for refurbished models or see if they can remove a non-essential item."
*   **ACT**: Calls `check_refurbished_alternatives(category="gpu", max_price=400)`.
*   **OBSERVE**: "I found an Open-Box RTX 3060 for $350. This closes the gap."

---

## 🧠 4. Qdrant Integration: The Technical Deep Dive

We use Qdrant as a **Computational Retrieval Engine**, pushing logic to the database to minimize latency.

### A. Hybrid Search Strategy

Valora performs "Hybrid Search" by combining two distinct signals:
1.  **Dense Vectors (Semantic)**: Captures the *meaning* of a query (e.g., "fast computer" maps to "high-performance processor").
2.  **Sparse/Keyword Filters (Precise)**: Captures *constraints* map to metadata (e.g., "monitor" must physically be a "monitor").

```mermaid
sequenceDiagram
    participant Engine as Search Engine
    participant Embedder as CLIP/MiniLM
    participant Qdrant as Qdrant Node
    
    Engine->>Embedder: Encode "gaming laptop for streaming"
    Embedder-->>Engine: Generate Vector (384-dim)
    
    Engine->>Qdrant: Query(Vector, Filters)
    note right of Qdrant: 1. Apply Hard Filters (Price < Budget)<br/>2. Apply ACORN Traversal<br/>3. Re-rank by Relevance
    
    Qdrant-->>Engine: Top Candidates
```

### B. ACORN Filtering (Approximate COnstrained Random Neighbors)

Standard vector search struggles when you apply strict filters (like specific budget ranges) because the search graph becomes disconnected. Valora utilizes **ACORN**, a special traversal algorithm in Qdrant 1.13+.

*   **Concept**: Instead of filtering *after* finding neighbors (which results in zero results), ACORN navigates the graph *while respecting constraints*.
*   **Benefit**: This guarantees that even if a user's budget filters out 95% of the products, we still find the absolute best matches among the remaining 5%.

### C. Multimodal Data Schema

We store all data in a unified collection to allow seamless switching between text and image search.

```mermaid
classDiagram
    class ProductCollection {
        +UUID product_id
        +Float price
        +Keyword category
        +Float rating
        +Vector text_vector
        +Vector image_vector
    }
    note for ProductCollection "Single Collection for Text & Image Search"
```

*   **Text Search**: Uses the `text_vector` generated by Sentence Transformers.
*   **Visual Search**: Uses the `image_vector` generated by CLIP.
*   **Filtering**: All searches can be filtered by `price`, `category`, and `rating` simultaneously.

---

## 🛠️ 5. Tech Stack & Dependencies

| Component | Technology | Version | Justification |
|:---|:---|:---|:---|
| **Frontend** | React | `^18.2.0` | Concurrent rendering for smooth UI transitions |
| | Vite | `^5.0.0` | High-performance build tool |
| | Tailwind CSS | `^3.4.0` | Utility-first styling for rapid development |
| | Recharts | `^2.10.0` | Visualization library for the Analytics Dashboard |
| **Backend** | FastAPI | `0.109.0` | High-performance AsyncIO web framework |
| | Pydantic | `2.5.0` | Robust data validation |
| **Vector DB** | **Qdrant** | `1.13.0` | Advanced vector search with ACORN filtering |
| **Solver** | **Google OR-Tools** | `9.7.0` | Industry-standard Constraint Programming solver |
| **AI** | **Groq** | `0.4.0` | Ultra-fast LLM inference for explanations |

---

## 🚀 6. Setup & Installation Guide

To run Valora locally from scratch, follow these detailed steps.

### Prerequisites
*   **Python 3.10+** - [Download Python](https://www.python.org/downloads/)
*   **Node.js 18+** - [Download Node.js](https://nodejs.org/)
*   **Qdrant Cloud Account** - [Sign up at Qdrant](https://cloud.qdrant.io/) (free tier available)
*   **Groq API Key** - [Get API Key](https://console.groq.com/) (for LLM-powered explanations)

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/Valora.git
cd Valora
```

---

### Step 2: Backend Setup

#### 2.1 Create a Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Activate it (macOS/Linux)
source venv/bin/activate
```

#### 2.2 Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### 2.3 Configure Environment Variables

Create a `.env` file in the project root directory with the following content:

```env
# Qdrant Configuration
QDRANT_URL=https://your-cluster-id.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key

# Groq LLM Configuration
GROQ_API_KEY=your-groq-api-key

# Optional: PostgreSQL (for enhanced product data)
DATABASE_URL=postgresql://user:password@localhost:5432/valora
```

#### 2.4 Generate Embeddings (First-Time Setup)

Generate text embeddings for the product catalog:

```bash
python scripts/generate_embeddings.py
```

This will create `text_embeddings.npy` in the `data/` directory using the `all-MiniLM-L6-v2` model.

#### 2.5 Upload Data to Qdrant

Upload products and embeddings to your Qdrant instance:

```bash
python scripts/upload_to_qdrant.py
```

#### 2.6 Start the FastAPI Backend Server

```bash
# Run on default port 8123
uvicorn api.main:app --host 0.0.0.0 --port 8123 --reload
```

The API will be available at `http://localhost:8123`. You can view the interactive API docs at `http://localhost:8123/docs`.

---

### Step 3: Frontend Setup

Open a **new terminal** and navigate to the frontend directory:

#### 3.1 Install Node.js Dependencies

```bash
cd frontend
npm install
```

#### 3.2 Start the Development Server

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## 📖 7. Usage Scenarios & Examples

### Scenario A: "The Budget Gamer" (Smart Path)
*   **User Action**: Searches for "$1000 gaming setup".
*   **System Logic**: The AFIG engine detects a "Budget Conscious" profile. The search engine applies strict price filters in Qdrant before ranking.
*   **Result**: The user sees a curated list of high-value components that fit exactly within the $1000 limit, preventing overspending.

### Scenario B: "The Complete Studio" (Deep Path)
*   **User Action**: Searches for "Streaming setup for $2500".
*   **System Logic**: The Router detects a complex, multi-category intent. It retrieves top candidates for cameras, mics, and lights, then uses the Bundle Optimizer to mathematically solve for the highest quality combination under $2500.
*   **Result**: A complete, compatible bundle is presented, saving the user hours of research.

### Scenario C: Analytics Dashboard
*   **User Action**: Clicks the Analytics icon.
*   **System Logic**: The backend aggregates real-time signals to calculate metrics.
*   **Result**: Visual graphs display **Engagement Scores**, **Budget Compliance Rates**, and **Speed Metrics**, proving the system's effectiveness.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
