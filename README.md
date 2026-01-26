# 💎 Valora

Valora is an **AI-driven, privacy-centric commerce decision engine** that transforms the way users navigate complex purchasing decisions. Moving beyond simple keyword search, Valora employs a sophisticated **Adaptive Financial Intent Graph (AFIG)** to understand the deeper psychological and situational drivers behind every purchase.

By synthesizing real-time budget constraints with deeply mapped product relationships, Valora empowers users to discover optimal product bundles that don't just fit their needs—but also their financial reality.

### 🌟 Why Valora?
- **Intelligent Intent Reconciliation**: Leveraging a three-layer graph (Stable, Situational, and Behavioral) to predict what users *really* want, even when they can't articulate it.
- **Dynamic Three-Path Routing**: An optimized orchestration layer that balances speed and precision, routing queries through **Fast**, **Smart**, or **Deep** processing paths based on complexity.
- **Autonomous Budget Pathfinding**: An integrated ReAct agent that acts as a financial concierge, navigating price trade-offs and affordability tools to ensure every recommendation is viable.
- **Privacy-Aware Architecture**: Built from the ground up to respect user data, ensuring that personalized recommendations never come at the cost of personal security.

## 👥 Team Members

- **Rachid Hssin**
- **Arwa Benaoun**
- **Maryem Besbes**
- **Mohamed Rayen Hamed**

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite, Tailwind CSS, Framer Motion, Zustand |
| **Backend** | FastAPI, Pydantic, Uvicorn, Python 3.10+ |
| **Vector DB** | Qdrant Cloud |
| **LLM** | Groq (Llama-3.1-8B) |
| **Optimizer** | OR-Tools CP-SAT |

## 🚀 Setup & Run Instructions

### Prerequisites
- Python 3.10+
- Node.js & npm
- [Groq API Key](https://console.groq.com/)
- [Qdrant Cloud Account](https://cloud.qdrant.io/)

### 1. Backend Setup
```bash
# Clone the repository
# git clone <repo-url>
cd Valora

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Copy .env.example to .env and add your API keys
# cp .env.example .env (Linux/Mac)
# copy .env.example .env (Windows)
```

### 3. Start Backend API
```bash
# Run the FastAPI server
cd api
uvicorn main:app --reload --port 8000
```

### 4. Frontend Setup
```bash
cd ../frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:5173`.


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
