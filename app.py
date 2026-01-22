"""
FinBundle Streamlit UI
AI-powered Smart Product Discovery with Budget Intelligence
"""
import streamlit as st
import asyncio
import time
import json
from typing import Dict, Any, List

# Page configuration
st.set_page_config(
    page_title="FinBundle - Smart Discovery",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium look
st.markdown("""
<style>
    /* Dark theme with vibrant accents */
    .stApp {
        background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%);
    }
    
    /* Headers */
    h1 {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }
    
    /* Metric cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1rem;
        backdrop-filter: blur(10px);
    }
    
    /* Product cards */
    .product-card {
        background: linear-gradient(145deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .product-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    
    /* Path badges */
    .path-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .path-fast { background: linear-gradient(90deg, #00c853, #69f0ae); color: #000; }
    .path-smart { background: linear-gradient(90deg, #2196f3, #03a9f4); color: #fff; }
    .path-deep { background: linear-gradient(90deg, #9c27b0, #e040fb); color: #fff; }
    
    /* Agent path cards */
    .agent-path {
        background: rgba(156, 39, 176, 0.1);
        border-left: 4px solid #9c27b0;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    /* Bundle summary */
    .bundle-summary {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2));
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(102, 126, 234, 0.4);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: transform 0.2s;
    }
    
    .stButton > button:hover {
        transform: scale(1.02);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'last_result' not in st.session_state:
    st.session_state.last_result = None
if 'cart' not in st.session_state:
    st.session_state.cart = []


# Helper functions
def run_async(coro):
    """Run async coroutine in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def get_path_badge(path: str) -> str:
    """Get colored badge HTML for path."""
    return f'<span class="path-badge path-{path}">{path}</span>'


def format_price(price: float) -> str:
    """Format price with dollar sign."""
    return f"${price:,.2f}"


# Initialize engine (lazy load)
@st.cache_resource
def get_engine():
    """Get or create the FinBundle engine."""
    try:
        from core.search_engine import FinBundleEngine
        return FinBundleEngine()
    except ImportError as e:
        st.error(f"⚠️ Could not initialize engine: {e}")
        return None


# --- Sidebar ---
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    user_id = st.text_input(
        "User ID",
        value="demo_user",
        help="Your unique identifier for personalized recommendations"
    )
    
    budget = st.slider(
        "💰 Your Budget",
        min_value=100,
        max_value=5000,
        value=1000,
        step=50,
        format="$%d"
    )
    
    st.divider()
    
    # Metrics from last search
    st.markdown("### 📊 Last Search Metrics")
    
    if st.session_state.last_result:
        metrics = st.session_state.last_result.get('metrics', {})
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Latency", f"{metrics.get('total_latency_ms', 0):.0f}ms")
        with col2:
            path = metrics.get('path_used', 'N/A').upper()
            st.metric("Path", path)
        
        cache_hit = st.session_state.last_result.get('cache_hit', False)
        st.metric("Cache Hit", "✓ Yes" if cache_hit else "✗ No")
    else:
        st.caption("Run a search to see metrics")
    
    st.divider()
    
    # Cart summary
    st.markdown("### 🛒 Cart")
    
    if st.session_state.cart:
        cart_total = sum(item.get('price', 0) for item in st.session_state.cart)
        st.write(f"{len(st.session_state.cart)} items • {format_price(cart_total)}")
        
        for i, item in enumerate(st.session_state.cart):
            cols = st.columns([3, 1])
            with cols[0]:
                st.caption(f"{item.get('name', 'Item')[:20]}...")
            with cols[1]:
                if st.button("✕", key=f"remove_{i}"):
                    st.session_state.cart.pop(i)
                    st.rerun()
        
        if st.button("Clear Cart", use_container_width=True):
            st.session_state.cart = []
            st.rerun()
    else:
        st.caption("Cart is empty")
    
    st.divider()
    
    # About
    st.markdown("### About")
    st.caption("""
    **FinBundle v3**
    
    Smart discovery with:
    - 🧠 AFIG intent reconciliation
    - ⚡ Three-path routing
    - 🤖 AI affordability agent
    - 🎯 Bundle optimization
    """)


# --- Main Content ---
st.markdown("# 🛒 FinBundle")
st.markdown("#### AI-Powered Smart Product Discovery")

st.markdown("---")

# Search input
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input(
        "🔍 What are you looking for?",
        placeholder="e.g., gaming laptop, complete home office setup, budget keyboard and mouse",
        label_visibility="collapsed"
    )
with col2:
    search_clicked = st.button("Search", type="primary", use_container_width=True)

# Quick search suggestions
st.markdown("**Quick searches:** ", unsafe_allow_html=True)
quick_cols = st.columns(5)
quick_searches = [
    "Gaming laptop",
    "Home office setup",
    "Budget keyboard",
    "4K monitor",
    "Complete gaming rig"
]
for i, (col, term) in enumerate(zip(quick_cols, quick_searches)):
    with col:
        if st.button(term, key=f"quick_{i}", use_container_width=True):
            query = term
            search_clicked = True

st.markdown("---")

# Execute search
if search_clicked and query:
    engine = get_engine()
    
    if engine:
        with st.spinner("🔍 Searching..."):
            start = time.time()
            
            result = run_async(engine.search(
                query=query,
                user_id=user_id,
                budget=budget,
                cart=st.session_state.cart
            ))
            
            st.session_state.last_result = result
            st.session_state.search_history.append({
                'query': query,
                'budget': budget,
                'timestamp': time.time()
            })
        
        # Display results
        metrics = result.get('metrics', {})
        path = metrics.get('path_used', 'unknown')
        
        # Success banner
        st.success(f"✅ Found results via **{path.upper()}** path in **{metrics.get('total_latency_ms', 0):.0f}ms**")
        
        # Path indicator
        st.markdown(f"<p>{get_path_badge(path)} {metrics.get('route_reason', '')}</p>", unsafe_allow_html=True)
        
        # Results based on path
        if path == 'fast':
            st.markdown("### ⚡ Quick Results")
            results = result.get('results', [])
            
            if results:
                cols = st.columns(3)
                for i, item in enumerate(results[:6]):
                    with cols[i % 3]:
                        with st.container():
                            st.markdown(f"**{item.get('name', 'Product')}**")
                            st.write(f"💰 {format_price(item.get('price', 0))}")
                            st.write(f"⭐ {item.get('rating', 'N/A')}")
                            if st.button("Add to Cart", key=f"add_fast_{i}"):
                                st.session_state.cart.append(item)
                                st.rerun()
            else:
                st.info("No precomputed results. Try a more specific search for better results.")
        
        elif path == 'smart':
            st.markdown("### 🧠 Smart Recommendations")
            results = result.get('results', [])
            
            if results:
                # Display as cards
                for i, item in enumerate(results[:9]):
                    with st.container():
                        cols = st.columns([3, 1, 1, 1])
                        
                        with cols[0]:
                            st.markdown(f"**{item.get('name', 'Product')}**")
                            st.caption(f"{item.get('category', '')} • {item.get('brand', '')}")
                        
                        with cols[1]:
                            st.write(f"💰 {format_price(item.get('price', 0))}")
                        
                        with cols[2]:
                            st.write(f"⭐ {item.get('rating', 0)}/5")
                            st.caption(f"Score: {item.get('utility', 0):.2f}")
                        
                        with cols[3]:
                            if st.button("Add", key=f"add_smart_{i}"):
                                st.session_state.cart.append(item)
                                st.toast(f"Added {item.get('name', 'item')[:20]} to cart")
                        
                        st.markdown("---")
            else:
                st.info("No results found. Try adjusting your budget or search terms.")
        
        else:  # deep
            st.markdown("### 🎯 Optimized Bundle")
            
            bundle = result.get('bundle', {})
            bundle_items = bundle.get('bundle', [])
            
            if bundle_items:
                # Bundle summary card
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total", format_price(bundle.get('total_price', 0)))
                
                with col2:
                    budget_pct = bundle.get('budget_used', 0) * 100
                    delta = f"{budget_pct - 100:.1f}%" if budget_pct > 100 else None
                    st.metric("Budget Used", f"{budget_pct:.0f}%", delta=delta)
                
                with col3:
                    st.metric("Items", len(bundle_items))
                
                with col4:
                    st.metric("Method", bundle.get('method', 'N/A').upper())
                
                st.markdown("---")
                
                # Bundle items
                st.markdown("#### 📦 Bundle Items")
                
                explanations = {e.get('product_id'): e.get('explanation', '') for e in result.get('explanations', [])}
                
                for item in bundle_items:
                    with st.expander(f"**{item.get('name', 'Item')}** — {format_price(item.get('price', 0))}", expanded=False):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write(f"**Category:** {item.get('category', 'N/A')}")
                            st.write(f"**Utility Score:** {item.get('utility', 0):.3f}")
                            
                            # Explanation
                            exp = explanations.get(item.get('id'), '')
                            if exp:
                                st.info(f"💡 {exp}")
                        
                        with col2:
                            if st.button("Add to Cart", key=f"add_bundle_{item.get('id')}"):
                                st.session_state.cart.append(item)
                                st.toast(f"Added to cart!")
                
                # Bundle explanation
                bundle_exp = result.get('bundle_explanation', '')
                if bundle_exp:
                    st.markdown("#### 💡 Why This Bundle")
                    st.success(bundle_exp)
            
            # Agent paths
            agent_result = result.get('agent_paths')
            
            if agent_result and agent_result.get('status') == 'paths_found':
                st.markdown("---")
                st.markdown("### 🤖 AI Affordability Assistant")
                
                gap = agent_result.get('gap', 0)
                if gap > 0:
                    st.warning(f"💸 Budget gap detected: **{format_price(gap)}** over budget")
                
                paths = agent_result.get('paths', [])
                
                if paths:
                    st.markdown("**Here are some ways to make this affordable:**")
                    
                    for i, path in enumerate(paths, 1):
                        with st.container():
                            path_type = path.get('path_type', 'unknown').replace('_', ' ').title()
                            
                            st.markdown(f"""
                            <div class="agent-path">
                                <strong>Option {i}: {path_type}</strong><br>
                                <p>{path.get('summary', '')}</p>
                                <p><strong>Action:</strong> {path.get('action', '')}</p>
                                <p><em>Trade-off: {path.get('trade_off', '')}</em></p>
                                {f"<p>💰 Potential savings: <strong>{format_price(path.get('savings', 0))}</strong></p>" if path.get('savings') else ""}
                            </div>
                            """, unsafe_allow_html=True)
        
        # Debug expander
        with st.expander("🔧 Debug: Raw Response"):
            st.json(result)
    
    else:
        st.error("Search engine not available. Please check the installation.")

elif not query and search_clicked:
    st.warning("Please enter a search query")


# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: rgba(255,255,255,0.5); padding: 2rem;">
    Built with ❤️ using <strong>Qdrant</strong>, <strong>Groq</strong>, and <strong>OR-Tools</strong><br>
    <small>FinBundle v3 • Smart Commerce Discovery Engine</small>
</div>
""", unsafe_allow_html=True)
