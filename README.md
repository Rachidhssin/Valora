# 🛒 FinBundle v3

An adaptive, privacy-aware commerce decision engine with React frontend and FastAPI backend.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![React](https://img.shields.io/badge/React-18+-61DAFB.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Cost](https://img.shields.io/badge/Cost-$0-brightgreen.svg)

## 🏆 Key Innovations

| Innovation | Description |
|------------|-------------|
| **AFIG** | Adaptive Financial Intent Graph with 3-layer reconciliation |
| **Three-Path Router** | Fast (<100ms) / Smart (<300ms) / Deep (<1500ms) |
| **Budget Pathfinder Agent** | ReAct agent with 5 affordability tools |
| **Hybrid Bundle Optimizer** | OR-Tools CP-SAT + greedy fallback |

## 🚀 Quick Start

### Backend Setup
```bash
cd finbundle

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Add your API keys to .env

# Generate data
python scripts/generate_mock_data.py
python scripts/generate_embeddings.py
python scripts/upload_to_qdrant.py

# Start API server
cd api
uvicorn main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Open http://localhost:5173 in your browser.

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend                           │
│   ┌─────────┐  ┌────────────┐  ┌─────────────────────────┐  │
│   │ Sidebar │  │ SearchBar  │  │    SearchResults        │  │
│   │ • Cart  │  │            │  │ • ProductGrid           │  │
│   │ • Budget│  └────────────┘  │ • BundleItems           │  │
│   │ • Metrics│                  │ • AgentPaths            │  │
│   └─────────┘                   └─────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │ API Calls
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                           │
│   POST /api/search  │  GET /api/user/{id}/profile           │
│   GET /api/categories  │  POST /api/user/{id}/signal        │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   FinBundle Engine                           │
│   AFIG → Router → Qdrant → Feasibility → Optimizer → Agent  │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
finbundle/
├── api/                    # FastAPI backend
│   └── main.py
├── core/                   # Core engine
├── retrieval/              # Search & cache
├── optimization/           # Bundle optimizer
├── agent/                  # Budget agent
├── explanation/            # LLM explainer
├── frontend/               # React app
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── store/          # Zustand state
│   │   ├── App.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
├── scripts/                # Data generation
└── tests/                  # Integration tests
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, Tailwind, Framer Motion, Zustand |
| Backend | FastAPI, Pydantic, Uvicorn |
| Vector DB | Qdrant Cloud |
| LLM | Groq Llama-3.1-8B |
| Optimizer | OR-Tools CP-SAT |
| Database | PostgreSQL |

## 🧪 Testing

```bash
# Backend tests
python tests/test_integration.py

# Run demo scenarios
python scripts/demo_scenarios.py
```

## 📄 License

MIT License
