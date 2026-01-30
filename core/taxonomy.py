"""
Category Taxonomy & Disambiguation System

Solves semantic overlap problems where ambiguous terms like "screen" or "keyboard"
match multiple unrelated product categories (monitors vs laptops, computer vs musical).
"""

from typing import Dict, List, Optional, Set, Tuple
import re


class CategoryTaxonomy:
    """
    Smart category disambiguation based on query context.
    
    Handles:
    1. Ambiguous terms → category inference
    2. Component conflicts → parent product priority
    3. Exclusion terms → filter out wrong categories
    """
    
    # Disambiguation rules: term → list of conditions
    # Each condition: {'if_contains': [...], 'then_category': '...', 'exclude': [...]}
    DISAMBIGUATION_RULES: Dict[str, List[Dict]] = {
        # Screen disambiguation
        'screen': [
            {'if_contains': ['laptop', 'notebook', 'macbook'], 'then_category': 'laptops', 'exclude': ['monitors']},
            {'if_contains': ['phone', 'mobile', 'iphone', 'android', 'smartphone'], 'then_category': 'phones', 'exclude': ['monitors', 'laptops']},
            {'if_contains': ['tv', 'television'], 'then_category': 'tvs', 'exclude': ['monitors']},
            {'if_contains': ['protector', 'guard', 'film'], 'then_category': 'accessories', 'exclude': ['monitors', 'laptops']},
            {'if_contains': [], 'then_category': 'monitors', 'exclude': ['laptops', 'phones']}  # Default
        ],
        'display': [
            {'if_contains': ['laptop', 'notebook'], 'then_category': 'laptops', 'exclude': ['monitors']},
            {'if_contains': ['phone', 'mobile'], 'then_category': 'phones', 'exclude': ['monitors']},
            {'if_contains': [], 'then_category': 'monitors', 'exclude': []}
        ],
        'monitor': [
            {'if_contains': ['baby'], 'then_category': 'baby_monitors', 'exclude': ['monitors']},
            {'if_contains': ['health', 'heart', 'blood'], 'then_category': 'health_devices', 'exclude': ['monitors']},
            {'if_contains': [], 'then_category': 'monitors', 'exclude': []}
        ],
        
        # Keyboard disambiguation
        'keyboard': [
            {'if_contains': ['piano', 'music', 'musical', 'midi', 'synthesizer', 'synth', 'keys'], 'then_category': 'musical_instruments', 'exclude': ['keyboards', 'computer_accessories']},
            {'if_contains': ['gaming', 'mechanical', 'wireless', 'bluetooth', 'rgb', 'usb', 'typing', 'computer'], 'then_category': 'keyboards', 'exclude': ['musical_instruments']},
            {'if_contains': [], 'then_category': 'keyboards', 'exclude': ['musical_instruments']}  # Default to computer
        ],
        'keys': [
            {'if_contains': ['piano', 'music', 'keyboard'], 'then_category': 'musical_instruments', 'exclude': []},
            {'if_contains': [], 'then_category': None, 'exclude': []}  # Ambiguous, no default
        ],
        
        # Mouse disambiguation
        'mouse': [
            {'if_contains': ['gaming', 'wireless', 'optical', 'computer', 'dpi', 'usb'], 'then_category': 'mice', 'exclude': []},
            {'if_contains': ['mickey', 'disney', 'toy', 'kids'], 'then_category': 'toys', 'exclude': ['mice']},
            {'if_contains': ['trap', 'pest'], 'then_category': None, 'exclude': ['mice', 'electronics']},
            {'if_contains': [], 'then_category': 'mice', 'exclude': []}
        ],
        
        # Speaker disambiguation  
        'speaker': [
            {'if_contains': ['bluetooth', 'wireless', 'portable', 'smart', 'soundbar'], 'then_category': 'speakers', 'exclude': []},
            {'if_contains': ['car', 'vehicle', 'auto'], 'then_category': 'car_audio', 'exclude': []},
            {'if_contains': [], 'then_category': 'speakers', 'exclude': []}
        ],
        
        # Charger disambiguation
        'charger': [
            {'if_contains': ['phone', 'mobile', 'iphone', 'android', 'wireless', 'usb', 'fast'], 'then_category': 'phone_accessories', 'exclude': []},
            {'if_contains': ['laptop', 'notebook', 'macbook'], 'then_category': 'laptop_accessories', 'exclude': []},
            {'if_contains': ['car', 'vehicle'], 'then_category': 'car_accessories', 'exclude': []},
            {'if_contains': ['battery', 'aa', 'aaa'], 'then_category': 'battery_chargers', 'exclude': []},
            {'if_contains': [], 'then_category': 'phone_accessories', 'exclude': []}
        ],
        
        # Cable disambiguation
        'cable': [
            {'if_contains': ['hdmi', 'displayport', 'vga', 'dvi'], 'then_category': 'video_cables', 'exclude': []},
            {'if_contains': ['usb', 'type-c', 'lightning', 'charging'], 'then_category': 'charging_cables', 'exclude': []},
            {'if_contains': ['ethernet', 'cat5', 'cat6', 'network'], 'then_category': 'network_cables', 'exclude': []},
            {'if_contains': ['audio', 'aux', 'rca'], 'then_category': 'audio_cables', 'exclude': []},
            {'if_contains': [], 'then_category': 'cables', 'exclude': []}
        ],
        
        # Case disambiguation
        'case': [
            {'if_contains': ['phone', 'iphone', 'samsung', 'mobile'], 'then_category': 'phone_cases', 'exclude': ['laptop_bags']},
            {'if_contains': ['laptop', 'notebook', 'macbook', 'sleeve'], 'then_category': 'laptop_bags', 'exclude': ['phone_cases']},
            {'if_contains': ['airpods', 'earbuds', 'headphone'], 'then_category': 'audio_accessories', 'exclude': []},
            {'if_contains': ['pc', 'computer', 'tower', 'atx'], 'then_category': 'pc_cases', 'exclude': []},
            {'if_contains': [], 'then_category': 'cases', 'exclude': []}
        ],
        
        # Adapter disambiguation
        'adapter': [
            {'if_contains': ['hdmi', 'displayport', 'vga', 'video'], 'then_category': 'video_adapters', 'exclude': []},
            {'if_contains': ['usb', 'hub', 'type-c'], 'then_category': 'usb_adapters', 'exclude': []},
            {'if_contains': ['power', 'ac', 'dc', 'charger'], 'then_category': 'power_adapters', 'exclude': []},
            {'if_contains': ['wifi', 'wireless', 'network', 'bluetooth'], 'then_category': 'network_adapters', 'exclude': []},
            {'if_contains': [], 'then_category': 'adapters', 'exclude': []}
        ],
    }
    
    # Component → Parent product mapping
    # When searching for a component, prefer results from parent products
    COMPONENT_PARENT_MAP: Dict[str, List[str]] = {
        'screen': ['monitors', 'laptops', 'phones', 'tvs'],
        'display': ['monitors', 'laptops', 'phones'],
        'battery': ['laptops', 'phones', 'tablets'],
        'keyboard': ['keyboards', 'laptops'],
        'touchpad': ['laptops'],
        'webcam': ['webcams', 'laptops'],
        'speaker': ['speakers', 'laptops', 'phones'],
        'microphone': ['microphones', 'headsets', 'laptops'],
        'camera': ['cameras', 'phones', 'laptops'],
        'lens': ['cameras', 'camera_lenses'],
        'ram': ['memory', 'laptops', 'desktops'],
        'ssd': ['storage', 'laptops', 'desktops'],
        'hdd': ['storage', 'laptops', 'desktops'],
        'gpu': ['graphics_cards', 'laptops', 'desktops'],
        'cpu': ['processors', 'laptops', 'desktops'],
    }
    
    # Category aliases for normalization
    CATEGORY_ALIASES: Dict[str, str] = {
        'screens': 'monitors',
        'displays': 'monitors',
        'computer monitors': 'monitors',
        'keyboards': 'keyboards',
        'computer keyboards': 'keyboards',
        'mechanical keyboards': 'keyboards',
        'gaming keyboards': 'keyboards',
        'musical keyboards': 'musical_instruments',
        'piano keyboards': 'musical_instruments',
        'mice': 'mice',
        'computer mice': 'mice',
        'gaming mice': 'mice',
        'laptops': 'laptops',
        'notebooks': 'laptops',
        'phones': 'phones',
        'smartphones': 'phones',
        'mobile phones': 'phones',
        'tvs': 'tvs',
        'televisions': 'tvs',
    }
    
    @classmethod
    def disambiguate_query(cls, query: str) -> Tuple[Optional[str], List[str], List[str]]:
        """
        Analyze query and determine target category, boost categories, and exclusions.
        
        Args:
            query: User search query
            
        Returns:
            Tuple of (primary_category, boost_categories, exclude_categories)
        """
        query_lower = query.lower()
        words = set(re.findall(r'\b\w+\b', query_lower))
        
        primary_category = None
        boost_categories: List[str] = []
        exclude_categories: Set[str] = set()
        
        # Check each disambiguation term
        for term, rules in cls.DISAMBIGUATION_RULES.items():
            if term in words or term in query_lower:
                # Find matching rule
                for rule in rules:
                    conditions = rule.get('if_contains', [])
                    
                    # Check if any condition word is in query
                    if not conditions or any(cond in query_lower for cond in conditions):
                        category = rule.get('then_category')
                        excludes = rule.get('exclude', [])
                        
                        if category:
                            if primary_category is None:
                                primary_category = category
                            if category not in boost_categories:
                                boost_categories.append(category)
                        
                        exclude_categories.update(excludes)
                        break  # Use first matching rule
        
        # Handle component conflicts
        primary_category, boost_categories, exclude_categories = cls._resolve_component_conflicts(
            query_lower, primary_category, boost_categories, exclude_categories
        )
        
        return primary_category, boost_categories, list(exclude_categories)
    
    @classmethod
    def _resolve_component_conflicts(
        cls, 
        query: str, 
        primary: Optional[str],
        boosts: List[str],
        excludes: Set[str]
    ) -> Tuple[Optional[str], List[str], Set[str]]:
        """
        Resolve conflicts when query mentions both component and parent product.
        
        Example: "laptop screen" → prioritize laptops, exclude standalone monitors
        """
        words = set(re.findall(r'\b\w+\b', query))
        
        # Check for parent product mentions
        parent_mentions = []
        for word in words:
            if word in ['laptop', 'laptops', 'notebook']:
                parent_mentions.append('laptops')
            elif word in ['phone', 'phones', 'smartphone', 'mobile']:
                parent_mentions.append('phones')
            elif word in ['tablet', 'tablets', 'ipad']:
                parent_mentions.append('tablets')
            elif word in ['tv', 'television']:
                parent_mentions.append('tvs')
            elif word in ['desktop', 'pc', 'computer']:
                parent_mentions.append('desktops')
        
        # If parent product mentioned, prioritize it
        if parent_mentions:
            # Override primary category to parent
            primary = parent_mentions[0]
            boosts = parent_mentions + [b for b in boosts if b not in parent_mentions]
            
            # Exclude standalone component categories
            for component, parents in cls.COMPONENT_PARENT_MAP.items():
                if component in query:
                    # Exclude categories that are standalone components
                    standalone = [p for p in parents if p not in parent_mentions]
                    # Only exclude if they're standalone products (not sub-components)
                    if 'monitors' in standalone and 'laptops' in parent_mentions:
                        excludes.add('monitors')
                    if 'keyboards' in standalone and 'laptops' in parent_mentions:
                        excludes.add('keyboards')
        
        return primary, boosts, excludes
    
    @classmethod
    def normalize_category(cls, category: str) -> str:
        """Normalize category name to canonical form."""
        category_lower = category.lower().strip()
        return cls.CATEGORY_ALIASES.get(category_lower, category_lower)
    
    @classmethod
    def get_related_categories(cls, category: str) -> List[str]:
        """Get related categories for broader search."""
        category = cls.normalize_category(category)
        
        related_map = {
            'monitors': ['displays', 'screens', 'computer_monitors'],
            'keyboards': ['mechanical_keyboards', 'gaming_keyboards', 'wireless_keyboards'],
            'mice': ['gaming_mice', 'wireless_mice', 'trackballs'],
            'laptops': ['notebooks', 'ultrabooks', 'gaming_laptops'],
            'phones': ['smartphones', 'mobile_phones', 'cell_phones'],
            'headphones': ['earphones', 'earbuds', 'headsets'],
            'speakers': ['bluetooth_speakers', 'smart_speakers', 'soundbars'],
        }
        
        return related_map.get(category, [])
    
    @classmethod
    def should_filter_result(cls, product_category: str, exclude_categories: List[str], 
                            product_name: str = None) -> bool:
        """
        Check if a product should be filtered out based on exclusions.
        
        Uses both category AND product name to catch items with generic categories
        like "All Electronics" that are actually phones/laptops.
        """
        if not exclude_categories:
            return False
        
        # Check category directly
        normalized = cls.normalize_category(product_category)
        if normalized in exclude_categories or product_category.lower() in exclude_categories:
            return True
        
        # Check product name for excluded product types
        # This catches "Samsung Galaxy Phone" in "All Electronics" category
        if product_name:
            name_lower = product_name.lower()
            
            # Map exclusion categories to name keywords
            exclusion_keywords = {
                'phones': ['phone', 'smartphone', 'iphone', 'galaxy', 'pixel', 'oneplus', 'mobile phone', 'cell phone'],
                'laptops': ['laptop', 'notebook', 'macbook', 'chromebook', 'ultrabook'],
                'tablets': ['tablet', 'ipad'],
                'tvs': ['tv', 'television', ' lcd tv', 'oled tv', 'smart tv'],
                'musical_instruments': ['piano', 'synthesizer', 'midi keyboard', 'musical keyboard', 'digital piano', '88 key', '61 key'],
            }
            
            for exclude_cat in exclude_categories:
                keywords = exclusion_keywords.get(exclude_cat, [])
                if any(kw in name_lower for kw in keywords):
                    return True
        
        return False


def disambiguate_search(query: str) -> Dict:
    """
    Convenience function for search disambiguation.
    
    Returns dict with:
    - primary_category: Main category to filter by (or None)
    - boost_categories: Categories to boost in scoring
    - exclude_categories: Categories to filter out
    - is_ambiguous: Whether the query contains ambiguous terms
    """
    taxonomy = CategoryTaxonomy()
    primary, boosts, excludes = taxonomy.disambiguate_query(query)
    
    # Check if query contains known ambiguous terms
    query_lower = query.lower()
    ambiguous_terms = set(CategoryTaxonomy.DISAMBIGUATION_RULES.keys())
    query_words = set(re.findall(r'\b\w+\b', query_lower))
    is_ambiguous = bool(query_words & ambiguous_terms)
    
    return {
        'primary_category': primary,
        'boost_categories': boosts,
        'exclude_categories': excludes,
        'is_ambiguous': is_ambiguous,
        'detected_terms': list(query_words & ambiguous_terms)
    }
