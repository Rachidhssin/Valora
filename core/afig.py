"""
AFIG - Adaptive Financial Intent Graph
Multi-layer intent reconciliation with PostgreSQL storage
Three layers: Stable, Situational, and Behavioral
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from dotenv import load_dotenv

load_dotenv()

# Try to import psycopg2, fall back to mock storage if not available
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("⚠️ psycopg2 not installed, using in-memory storage")


@dataclass
class StableLayer:
    """Long-term financial characteristics (changes rarely)."""
    income_tier: str = "medium"  # low, medium, high
    risk_tolerance: float = 0.5  # 0-1 scale
    brand_affinity: Dict[str, float] = field(default_factory=dict)  # brand -> preference score
    category_preferences: Dict[str, float] = field(default_factory=dict)
    credit_score_tier: str = "good"  # poor, fair, good, excellent
    confidence: float = 0.3  # How confident we are in this layer


@dataclass
class SituationalLayer:
    """Session-specific context (changes per mission)."""
    mission: str = ""  # "gaming setup", "home office", etc.
    timeline: str = "flexible"  # urgent, soon, flexible
    event_context: str = ""  # "black friday", "back to school", etc.
    budget_override: Optional[float] = None
    specific_requirements: list = field(default_factory=list)
    confidence: float = 0.5


@dataclass
class BehavioralLayer:
    """Real-time signals (high frequency, high noise)."""
    recent_clicks: list = field(default_factory=list)  # Last N product clicks
    price_jumps: list = field(default_factory=list)  # Price range explorations
    dwell_times: Dict[str, float] = field(default_factory=dict)  # category -> avg dwell
    search_patterns: list = field(default_factory=list)
    cart_actions: list = field(default_factory=list)  # add/remove history
    confidence: float = 0.2  # Lower because noisy
    last_updated: str = ""


class AFIG:
    """
    Adaptive Financial Intent Graph
    Reconciles three layers of user intent with Bayesian updates
    """
    
    # Layer weights for reconciliation
    LAYER_WEIGHTS = {
        'stable': 0.3,
        'situational': 0.4,
        'behavioral': 0.3
    }
    
    # Evidence thresholds for Bayesian updates
    LLR_THRESHOLD = 0.693  # log(2) - requires 2:1 evidence
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.stable = StableLayer()
        self.situational = SituationalLayer()
        self.behavioral = BehavioralLayer()
        self._conn = None
        
        self._init_storage()
        self._load()
    
    def _init_storage(self):
        """Initialize PostgreSQL storage."""
        if not POSTGRES_AVAILABLE:
            return
        
        try:
            self._conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "finbundle"),
                user=os.getenv("POSTGRES_USER", "user"),
                password=os.getenv("POSTGRES_PASSWORD", "password"),
                connect_timeout=1
            )
            
            with self._conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS afig_profiles (
                        user_id VARCHAR(255) PRIMARY KEY,
                        stable_layer JSONB,
                        situational_layer JSONB,
                        behavioral_layer JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self._conn.commit()
        except Exception as e:
            print(f"⚠️ PostgreSQL connection failed: {e}")
            self._conn = None
    
    def _load(self):
        """Load profile from storage."""
        if not self._conn:
            return
        
        try:
            with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM afig_profiles WHERE user_id = %s",
                    (self.user_id,)
                )
                row = cur.fetchone()
                
                if row:
                    if row['stable_layer']:
                        data = row['stable_layer']
                        self.stable = StableLayer(**data)
                    if row['situational_layer']:
                        data = row['situational_layer']
                        self.situational = SituationalLayer(**data)
                    if row['behavioral_layer']:
                        data = row['behavioral_layer']
                        self.behavioral = BehavioralLayer(**data)
        except Exception as e:
            print(f"⚠️ Error loading profile: {e}")
    
    def _save(self):
        """Persist profile to storage."""
        if not self._conn:
            return
        
        try:
            with self._conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO afig_profiles (user_id, stable_layer, situational_layer, behavioral_layer, updated_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE SET
                        stable_layer = EXCLUDED.stable_layer,
                        situational_layer = EXCLUDED.situational_layer,
                        behavioral_layer = EXCLUDED.behavioral_layer,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    self.user_id,
                    json.dumps(asdict(self.stable)),
                    json.dumps(asdict(self.situational)),
                    json.dumps(asdict(self.behavioral))
                ))
                self._conn.commit()
        except Exception as e:
            print(f"⚠️ Error saving profile: {e}")
    
    def reconcile(self) -> Dict[str, Any]:
        """
        Reconcile all three layers into a unified intent profile.
        Uses weighted average with confidence adjustment.
        
        Returns:
            Dict with reconciled preferences and archetype classification
        """
        # Calculate effective weights (confidence-adjusted)
        stable_weight = self.LAYER_WEIGHTS['stable'] * self.stable.confidence
        situational_weight = self.LAYER_WEIGHTS['situational'] * self.situational.confidence
        behavioral_weight = self.LAYER_WEIGHTS['behavioral'] * self.behavioral.confidence
        
        total_weight = stable_weight + situational_weight + behavioral_weight
        if total_weight == 0:
            total_weight = 1  # Avoid division by zero
        
        # Normalize weights
        stable_weight /= total_weight
        situational_weight /= total_weight
        behavioral_weight /= total_weight
        
        # Determine price sensitivity from behavioral signals
        price_sensitivity = self._compute_price_sensitivity()
        
        # Determine archetype
        archetype = self._determine_archetype(price_sensitivity)
        
        # Compute effective budget modifier
        budget_modifier = self._compute_budget_modifier(archetype)
        
        return {
            "user_id": self.user_id,
            "archetype": archetype,
            "income_tier": self.stable.income_tier,
            "risk_tolerance": self.stable.risk_tolerance,
            "price_sensitivity": price_sensitivity,
            "budget_modifier": budget_modifier,
            "mission": self.situational.mission,
            "timeline": self.situational.timeline,
            "brand_preferences": self.stable.brand_affinity,
            "category_preferences": self.stable.category_preferences,
            "layer_weights": {
                "stable": round(stable_weight, 3),
                "situational": round(situational_weight, 3),
                "behavioral": round(behavioral_weight, 3)
            },
            "confidence_scores": {
                "stable": self.stable.confidence,
                "situational": self.situational.confidence,
                "behavioral": self.behavioral.confidence
            }
        }
    
    def _compute_price_sensitivity(self) -> float:
        """Compute price sensitivity from behavioral signals."""
        # Base from stable layer
        base_sensitivity = 1.0 - self.stable.risk_tolerance
        
        # Adjust from behavioral patterns
        if self.behavioral.price_jumps:
            # If user frequently looks at cheaper alternatives, increase sensitivity
            jumps = self.behavioral.price_jumps[-10:]  # Last 10 jumps
            up_count = sum(1 for j in jumps if j > 0)
            down_count = sum(1 for j in jumps if j < 0)
            
            if down_count > up_count:
                base_sensitivity = min(1.0, base_sensitivity + 0.15)
            elif up_count > down_count:
                base_sensitivity = max(0.0, base_sensitivity - 0.15)
        
        return round(base_sensitivity, 3)
    
    def _determine_archetype(self, price_sensitivity: float) -> str:
        """Classify user into an archetype for personalization."""
        if price_sensitivity > 0.7:
            return "budget_conscious"
        elif price_sensitivity < 0.3:
            return "quality_seeker"
        elif self.situational.timeline == "urgent":
            return "convenience_buyer"
        elif self.stable.risk_tolerance > 0.7:
            return "early_adopter"
        else:
            return "value_balanced"
    
    def _compute_budget_modifier(self, archetype: str) -> float:
        """Compute budget stretch/shrink factor."""
        modifiers = {
            "budget_conscious": 0.85,  # Recommend below budget
            "quality_seeker": 1.15,    # Can stretch budget
            "convenience_buyer": 1.0,  # Stick to budget
            "early_adopter": 1.1,      # Willing to pay more
            "value_balanced": 0.95     # Slight savings preference
        }
        return modifiers.get(archetype, 1.0)
    
    def update_stable(self, updates: Dict[str, Any], evidence_strength: float = 0.5):
        """
        Update stable layer with Bayesian evidence accumulation.
        Only updates if evidence exceeds LLR threshold.
        """
        # Compute log-likelihood ratio
        llr = evidence_strength * 2  # Simplified LLR
        
        if llr < self.LLR_THRESHOLD:
            return  # Not enough evidence
        
        if 'income_tier' in updates:
            self.stable.income_tier = updates['income_tier']
        if 'risk_tolerance' in updates:
            self.stable.risk_tolerance = max(0, min(1, updates['risk_tolerance']))
        if 'brand_affinity' in updates:
            for brand, score in updates['brand_affinity'].items():
                current = self.stable.brand_affinity.get(brand, 0.5)
                # Exponential moving average
                self.stable.brand_affinity[brand] = 0.7 * current + 0.3 * score
        if 'category_preferences' in updates:
            for cat, score in updates['category_preferences'].items():
                current = self.stable.category_preferences.get(cat, 0.5)
                self.stable.category_preferences[cat] = 0.7 * current + 0.3 * score
        
        # Increase confidence
        self.stable.confidence = min(1.0, self.stable.confidence + 0.05)
        self._save()
    
    def update_situational(self, updates: Dict[str, Any]):
        """Update situational layer (session context)."""
        if 'mission' in updates:
            self.situational.mission = updates['mission']
        if 'timeline' in updates:
            self.situational.timeline = updates['timeline']
        if 'event_context' in updates:
            self.situational.event_context = updates['event_context']
        if 'budget_override' in updates:
            self.situational.budget_override = updates['budget_override']
        if 'specific_requirements' in updates:
            self.situational.specific_requirements = updates['specific_requirements']
        
        self.situational.confidence = 0.8  # High confidence for explicit input
        self._save()
    
    def update_behavioral(self, signal: Dict[str, Any]):
        """
        Update behavioral layer with real-time signal.
        Designed to handle window shopping without corrupting profile.
        """
        signal_type = signal.get('type', '')
        
        if signal_type == 'click':
            product = signal.get('product', {})
            self.behavioral.recent_clicks.append({
                'product_id': product.get('id'),
                'category': product.get('category'),
                'price': product.get('price'),
                'timestamp': datetime.now().isoformat()
            })
            # Keep last 50 clicks
            self.behavioral.recent_clicks = self.behavioral.recent_clicks[-50:]
        
        elif signal_type == 'price_jump':
            delta = signal.get('delta', 0)
            self.behavioral.price_jumps.append(delta)
            self.behavioral.price_jumps = self.behavioral.price_jumps[-20:]
        
        elif signal_type == 'dwell':
            category = signal.get('category', '')
            dwell_time = signal.get('seconds', 0)
            if category:
                current = self.behavioral.dwell_times.get(category, 0)
                self.behavioral.dwell_times[category] = (current + dwell_time) / 2
        
        elif signal_type == 'search':
            query = signal.get('query', '')
            if query:
                self.behavioral.search_patterns.append(query)
                self.behavioral.search_patterns = self.behavioral.search_patterns[-20:]
        
        elif signal_type == 'cart_action':
            action = {
                'action': signal.get('action'),  # add/remove
                'product_id': signal.get('product_id'),
                'timestamp': datetime.now().isoformat()
            }
            self.behavioral.cart_actions.append(action)
            self.behavioral.cart_actions = self.behavioral.cart_actions[-30:]
        
        self.behavioral.last_updated = datetime.now().isoformat()
        
        # Recalculate behavioral confidence based on signal volume
        signal_count = (
            len(self.behavioral.recent_clicks) +
            len(self.behavioral.price_jumps) +
            len(self.behavioral.cart_actions)
        )
        self.behavioral.confidence = min(0.8, 0.1 + signal_count * 0.02)
        
        self._save()
    
    def reset_behavioral(self):
        """Reset behavioral layer (new session)."""
        self.behavioral = BehavioralLayer()
        self._save()
    
    def get_category_affinity(self, category: str) -> float:
        """Get user's affinity for a category (0-1)."""
        # Check stable preferences
        stable_pref = self.stable.category_preferences.get(category, 0.5)
        
        # Check behavioral signals
        behavioral_pref = 0.5
        if self.behavioral.recent_clicks:
            category_clicks = sum(
                1 for c in self.behavioral.recent_clicks
                if c.get('category') == category
            )
            behavioral_pref = min(1.0, 0.5 + category_clicks * 0.05)
        
        # Weighted combination
        return 0.6 * stable_pref + 0.4 * behavioral_pref
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()


# Convenience functions for testing
if __name__ == "__main__":
    # Test AFIG without PostgreSQL
    print("🧪 Testing AFIG...")
    
    afig = AFIG(user_id="test_user_001")
    
    # Set up situational context
    afig.update_situational({
        "mission": "gaming setup",
        "timeline": "soon",
        "budget_override": 1500
    })
    
    # Simulate some behavioral signals
    afig.update_behavioral({
        "type": "click",
        "product": {"id": "prod_001", "category": "gpus", "price": 599}
    })
    afig.update_behavioral({
        "type": "price_jump",
        "delta": -100  # Looking at cheaper option
    })
    afig.update_behavioral({
        "type": "search",
        "query": "rtx 4070 deals"
    })
    
    # Get reconciled profile
    profile = afig.reconcile()
    
    print("\n📊 Reconciled Profile:")
    for key, value in profile.items():
        print(f"   {key}: {value}")
    
    print("\n✅ AFIG test complete!")
