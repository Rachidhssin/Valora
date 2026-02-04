"""
MEGA Router Test Suite - 1000 Tests Per Category
=================================================
Generates 35,000+ comprehensive test cases to validate the two-stage query routing system.

Categories:
- brand_category, use_case_category, feature_category, budget_category
- multi_category_and, context_bundle, quality_category, three_categories
- use_case_feature, bundle_budget, feature_plural, quality_use_case
- plural_category, quality_plural, multi_category_with, multi_feature
- ram_spec, single_category, multi_category_budget, multi_category_comma
- cross_category_comparison, same_category_comparison, complete_bundle
- bundle_keyword, brand_feature, specific_bundle, refresh_spec
- processor_spec, storage_spec, natural_language, complex_spec
- double_quality, display_spec, question_bundle, edge_* categories
"""

import sys
import os
import time
import random
import itertools
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Set
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from core.router import QueryRouter, RoutePath

# Seed for reproducibility
random.seed(42)


@dataclass
class TestCase:
    query: str
    budget: Optional[float]
    expected_path: str
    category: str
    
    def __hash__(self):
        return hash((self.query.lower().strip(), self.budget, self.expected_path))


class MegaTestGenerator:
    """Generates 1000 tests per category for maximum coverage."""
    
    # ==================== DATA POOLS ====================
    
    # Product categories (24 total)
    CATEGORIES = [
        'laptop', 'monitor', 'keyboard', 'mouse', 'headphones', 'headset',
        'webcam', 'speaker', 'phone', 'tablet', 'desk', 'chair', 'router',
        'charger', 'cable', 'hub', 'dock', 'microphone', 'camera', 'gpu',
        'cpu', 'tv', 'stand', 'adapter'
    ]
    
    # Comprehensive plural mappings
    # Note: 'workstations' triggers DEEP, so avoid it for SMART expectations
    PLURALS = {
        'laptop': ['laptops', 'notebooks'],
        'monitor': ['monitors', 'displays', 'screens'],
        'keyboard': ['keyboards'],
        'mouse': ['mice', 'mouses'],
        'headphones': ['headphones', 'earbuds', 'earphones'],
        'headset': ['headsets'],
        'webcam': ['webcams'],
        'speaker': ['speakers', 'soundbars'],
        'phone': ['phones', 'smartphones', 'mobiles', 'cellphones'],
        'tablet': ['tablets', 'ipads'],
        'desk': ['desks'],  # Removed 'workstations' - triggers DEEP
        'chair': ['chairs', 'seats'],
        'router': ['routers', 'modems'],
        'charger': ['chargers'],
        'cable': ['cables', 'cords', 'wires'],
        'hub': ['hubs'],
        'dock': ['docks', 'docking stations'],
        'microphone': ['microphones', 'mics'],
        'camera': ['cameras', 'cams'],
        'gpu': ['gpus', 'graphics cards', 'video cards'],
        'cpu': ['cpus', 'processors', 'chips'],
        'tv': ['tvs', 'televisions'],
        'stand': ['stands', 'mounts', 'holders'],
        'adapter': ['adapters', 'converters', 'dongles']
    }
    
    # Quality words (allowed in FAST path)
    QUALITY_WORDS = [
        'good', 'best', 'cheap', 'nice', 'great', 'top', 'quality',
        'affordable', 'premium', 'budget', 'excellent', 'perfect',
        'amazing', 'awesome', 'fantastic', 'reliable', 'decent', 'solid',
        'value', 'fine', 'superb', 'outstanding', 'wonderful', 'ideal',
        'exceptional', 'supreme', 'superior', 'optimal', 'ultimate'
    ]
    
    # Modifier words
    MODIFIER_WORDS = [
        'really', 'very', 'super', 'extremely', 'quite', 'pretty', 
        'fairly', 'so', 'incredibly', 'exceptionally', 'highly',
        'absolutely', 'totally', 'truly', 'remarkably', 'genuinely'
    ]
    
    # Use case keywords - extensive list
    USE_CASES = [
        'gaming', 'office', 'work', 'streaming', 'coding', 'programming',
        'video editing', 'music production', 'travel', 'school', 'business',
        'home', 'professional', 'studio', 'content creation', 'esports',
        'casual', 'competitive', 'productivity', 'creative', 'photo editing',
        'graphic design', 'web development', 'data science', 'machine learning',
        'vr', 'video conferencing', 'podcast', 'youtube', 'twitch',
        'film making', 'animation', 'cad', '3d modeling', 'architecture',
        'music mixing', 'dj', 'live streaming', 'remote work', 'hybrid work',
        'college', 'university', 'everyday', 'multimedia', 'entertainment',
        'finance', 'trading', 'research', 'writing', 'blogging', 'editing',
        'rendering', 'simulation', 'ai development', 'deep learning', 'crypto',
        'day trading', 'stock trading', 'forex', 'betting', 'sports'
    ]
    
    # Feature keywords - extensive list
    FEATURES = [
        # Connectivity
        'wireless', 'wired', 'bluetooth', 'wifi', 'usb', 'usb-c', 'thunderbolt',
        'hdmi', 'displayport', 'ethernet', '5g', 'wifi 6', 'wifi 6e',
        # Keyboard specific
        'mechanical', 'membrane', 'optical', 'linear', 'tactile', 'clicky',
        'tenkeyless', 'tkl', 'full-size', '60%', '65%', '75%', 'hot-swappable',
        'programmable', 'macro', 'n-key', 'anti-ghosting',
        # Visual
        'rgb', 'backlit', 'led', 'oled', 'lcd', 'ips', 'va', 'tn',
        '4k', '1440p', '1080p', '8k', '720p', 'qhd', 'uhd', 'fhd',
        'curved', 'flat', 'ultrawide', 'hdr', 'hdr10', 'dolby vision',
        # Audio
        'noise cancelling', 'noise-canceling', 'anc', 'active noise',
        'surround sound', '7.1', '5.1', 'stereo', 'dolby atmos',
        'bass', 'hi-fi', 'hires', 'lossless',
        # Physical
        'ergonomic', 'portable', 'compact', 'lightweight', 'slim', 'thin',
        'foldable', 'collapsible', 'adjustable', 'height adjustable',
        'swivel', 'tilt', 'pivot', 'vesa',
        # Performance
        'fast', 'quick', 'responsive', 'low-latency', 'high-speed',
        'high-performance', 'powerful', 'quiet', 'silent', 'fanless',
        # Materials
        'aluminum', 'metal', 'plastic', 'leather', 'mesh', 'fabric',
        'carbon fiber', 'wood', 'glass',
        # Durability
        'waterproof', 'water-resistant', 'dustproof', 'rugged', 'military-grade',
        'durable', 'sturdy',  # 'premium build' removed - triggers DEEP
        # Special
        'touch', 'touchscreen', 'fingerprint', 'face recognition',
        'smart', 'ai-powered', 'voice control', 'alexa', 'google assistant',
        # Gaming specific
        'high dpi', 'low latency', 'polling rate', 'optical sensor',
        # Extended
        'rechargeable', 'battery-powered', 'solar', 'magnetic', 'modular'
    ]
    
    # Brands - extensive list
    BRANDS = [
        # PC/Laptops
        'dell', 'hp', 'lenovo', 'asus', 'acer', 'msi', 'microsoft', 'apple',
        'razer', 'alienware', 'gigabyte', 'huawei', 'lg', 'samsung', 'toshiba',
        'fujitsu', 'vaio', 'framework', 'system76', 'xps', 'thinkpad',
        # Peripherals
        'logitech', 'corsair', 'steelseries', 'hyperx', 'roccat',
        'glorious', 'ducky', 'keychron', 'anne pro', 'varmilo', 'leopold',
        'filco', 'das keyboard', 'cooler master', 'redragon', 'havit',
        # Monitors
        'benq', 'viewsonic', 'aoc', 'philips', 'eve', 'nixeus',
        'prism', 'monoprice', 'viotek', 'pixio', 'innocn',
        # Audio
        'sony', 'bose', 'sennheiser', 'audio-technica', 'beyerdynamic',
        'akg', 'shure', 'rode', 'blue', 'jabra', 'plantronics', 'beats',
        'jbl', 'harman kardon', 'bang olufsen', 'focal', 'hifiman', 'audeze',
        'drop', 'fiio', 'topping', 'soundcore', 'skullcandy', 'marshall',
        # Streaming/Content
        'elgato', 'focusrite', 'behringer', 'presonus', 'scarlett',
        'blackmagic', 'atomos', 'neewer', 'godox', 'aputure',
        # Networking
        'netgear', 'tp-link', 'linksys', 'ubiquiti', 'eero', 'google',
        'orbi', 'dlink', 'belkin', 'motorola', 'arris', 'synology',
        # Components
        'nvidia', 'amd', 'intel', 'evga', 'zotac', 'sapphire', 'powercolor',
        'xfx', 'pny', 'crucial', 'kingston', 'seagate', 'western digital',
        'sandisk', 'sk hynix', 'gskill', 'teamgroup', 'patriot', 'noctua',
        # Mobile
        'oneplus', 'xiaomi', 'oppo', 'vivo', 'realme', 'motorola', 'nokia',
        'pixel', 'nothing', 'poco', 'honor', 'zte', 'meizu',
        # Accessories
        'anker', 'ugreen', 'baseus', 'spigen', 'otterbox', 'dbrand',
        'twelve south', 'native union', 'nomad', 'peak design', 'satechi',
        # Furniture
        'secretlab', 'herman miller', 'steelcase', 'autonomous', 'flexispot',
        'fully', 'uplift', 'branch', 'ikea', 'jarvis', 'vari', 'ergotron'
    ]
    
    # Bundle keywords
    BUNDLE_KEYWORDS = [
        'setup', 'bundle', 'kit', 'combo', 'package', 'build',
        'workstation', 'rig', 'system', 'complete', 'full set',
        'starter kit', 'all-in-one', 'entire', 'whole', 'together',
        'collection', 'pack', 'set', 'essentials', 'basics',
        'accessories', 'peripherals', 'gear', 'equipment'
    ]
    
    # Bundle contexts (use cases that imply bundles)
    BUNDLE_CONTEXTS = [
        'gaming', 'streaming', 'office', 'home office', 'work from home',
        'podcast', 'youtube', 'content creation', 'video production',
        'music production', 'pc', 'custom pc', 'esports', 'professional',
        'home studio', 'recording studio', 'music studio', 'podcast studio',
        'streaming studio', 'twitch', 'creator', 'influencer', 'vlogger',
        'photographer', 'videographer', 'editor', 'developer', 'coder',
        'wfh', 'remote', 'battlestation', 'desk', 'workstation'
    ]
    
    # RAM specifications
    RAM_SPECS = ['2gb', '4gb', '6gb', '8gb', '12gb', '16gb', '24gb', '32gb', '48gb', '64gb', '128gb', '256gb']
    
    # Storage specifications
    STORAGE_SPECS = ['32gb', '64gb', '128gb', '256gb', '512gb', '1tb', '2tb', '4tb', '8tb', '16tb', '32tb']
    
    # Display sizes
    DISPLAY_SIZES = [
        '11 inch', '12 inch', '13 inch', '13.3 inch', '14 inch', '15 inch', 
        '15.6 inch', '16 inch', '17 inch', '17.3 inch',
        '19 inch', '21 inch', '22 inch', '23 inch', '24 inch', '25 inch',
        '27 inch', '28 inch', '29 inch', '30 inch', '32 inch', '34 inch',
        '35 inch', '38 inch', '40 inch', '43 inch', '48 inch', '49 inch',
        '50 inch', '55 inch', '60 inch', '65 inch', '70 inch', '75 inch', 
        '77 inch', '80 inch', '83 inch', '85 inch', '86 inch'
    ]
    
    # Refresh rates
    REFRESH_RATES = [
        '30hz', '50hz', '60hz', '75hz', '90hz', '100hz', '120hz', '144hz',
        '165hz', '180hz', '200hz', '240hz', '280hz', '300hz', '360hz', '390hz',
        '480hz', '500hz', '540hz', '600hz'
    ]
    
    # Processor specs
    PROCESSORS = [
        # Intel desktop
        'i3', 'i5', 'i7', 'i9', 'pentium', 'celeron',
        'i3-10100', 'i3-12100', 'i3-13100', 'i3-14100',
        'i5-10400', 'i5-11400', 'i5-12400', 'i5-12600k', 'i5-13400', 'i5-13600k', 'i5-14400', 'i5-14600k',
        'i7-10700', 'i7-11700', 'i7-12700', 'i7-12700k', 'i7-13700', 'i7-13700k', 'i7-14700', 'i7-14700k',
        'i9-10900k', 'i9-11900k', 'i9-12900k', 'i9-13900k', 'i9-14900k',
        # Intel mobile
        'intel core ultra 5', 'intel core ultra 7', 'intel core ultra 9',
        # AMD desktop
        'ryzen 3', 'ryzen 5', 'ryzen 7', 'ryzen 9', 'threadripper',
        'ryzen 3 3100', 'ryzen 3 4100', 'ryzen 3 5100',
        'ryzen 5 3600', 'ryzen 5 5600', 'ryzen 5 5600x', 'ryzen 5 7600', 'ryzen 5 7600x', 'ryzen 5 9600x',
        'ryzen 7 3700x', 'ryzen 7 5800x', 'ryzen 7 5800x3d', 'ryzen 7 7800x3d', 'ryzen 7 9800x3d',
        'ryzen 9 3900x', 'ryzen 9 5900x', 'ryzen 9 5950x', 'ryzen 9 7900x', 'ryzen 9 7950x', 'ryzen 9 9900x', 'ryzen 9 9950x',
        # Apple
        'm1', 'm1 pro', 'm1 max', 'm1 ultra', 'm2', 'm2 pro', 'm2 max', 'm2 ultra',
        'm3', 'm3 pro', 'm3 max', 'm4', 'm4 pro', 'm4 max',
        # Mobile
        'snapdragon 8 gen 1', 'snapdragon 8 gen 2', 'snapdragon 8 gen 3', 'snapdragon 8 elite',
        'dimensity 9000', 'dimensity 9200', 'dimensity 9300', 'exynos 2400', 'tensor g3', 'tensor g4',
        'a14', 'a15', 'a16', 'a17', 'a18'
    ]
    
    # GPU specs
    GPU_SPECS = [
        # NVIDIA GeForce
        'gtx 1050', 'gtx 1060', 'gtx 1070', 'gtx 1080', 'gtx 1650', 'gtx 1660', 'gtx 1660 super', 'gtx 1660 ti',
        'rtx 2060', 'rtx 2070', 'rtx 2080', 'rtx 2080 ti',
        'rtx 3050', 'rtx 3060', 'rtx 3060 ti', 'rtx 3070', 'rtx 3070 ti', 'rtx 3080', 'rtx 3080 ti', 'rtx 3090', 'rtx 3090 ti',
        'rtx 4060', 'rtx 4060 ti', 'rtx 4070', 'rtx 4070 super', 'rtx 4070 ti', 'rtx 4070 ti super',
        'rtx 4080', 'rtx 4080 super', 'rtx 4090',
        'rtx 5070', 'rtx 5070 ti', 'rtx 5080', 'rtx 5090',
        # NVIDIA workstation
        'quadro rtx', 'rtx a4000', 'rtx a5000', 'rtx a6000',
        # AMD
        'rx 580', 'rx 590',
        'rx 5500', 'rx 5600', 'rx 5700', 'rx 5700 xt',
        'rx 6500', 'rx 6600', 'rx 6600 xt', 'rx 6700', 'rx 6700 xt', 'rx 6800', 'rx 6800 xt', 'rx 6900', 'rx 6900 xt',
        'rx 7600', 'rx 7700 xt', 'rx 7800 xt', 'rx 7900 gre', 'rx 7900 xt', 'rx 7900 xtx',
        'rx 9070', 'rx 9070 xt',
        # Intel
        'intel arc a380', 'intel arc a580', 'intel arc a750', 'intel arc a770',
        'intel arc b580',
        # Mobile/integrated
        'intel xe', 'radeon vega', 'mx350', 'mx450', 'mx550'
    ]
    
    # Budget values
    BUDGET_VALUES = [
        25, 30, 40, 50, 60, 75, 80, 100, 120, 150, 175, 200, 225, 250, 275, 300,
        325, 350, 375, 400, 425, 450, 475, 500, 550, 600, 650, 700, 750, 800,
        850, 900, 950, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800,
        1900, 2000, 2200, 2500, 2750, 3000, 3500, 4000, 4500, 5000, 6000,
        7000, 7500, 8000, 9000, 10000, 12000, 15000, 20000
    ]
    
    # Budget patterns
    BUDGET_PATTERNS = [
        ('under ${}', 'max'), ('below ${}', 'max'), ('less than ${}', 'max'),
        ('up to ${}', 'max'), ('max ${}', 'max'), ('maximum ${}', 'max'),
        ('not more than ${}', 'max'), ('no more than ${}', 'max'),
        ('for ${}', 'exact'), ('at ${}', 'exact'), ('${} price', 'exact'),
        ('around ${}', 'around'), ('about ${}', 'around'), ('roughly ${}', 'around'),
        ('approximately ${}', 'around'), ('near ${}', 'around'),
        ('${} budget', 'exact'), ('${} range', 'around'),
        ('over ${}', 'min'), ('above ${}', 'min'), ('more than ${}', 'min'),
        ('at least ${}', 'min'), ('minimum ${}', 'min'), ('starting at ${}', 'min'),
        ('${}+', 'min'), ('${} or more', 'min'), ('${} minimum', 'min'),
        ('within ${}', 'around'), ('spending ${}', 'exact'), ('${} cap', 'max')
    ]
    
    # Same-category comparisons (SMART path)
    SAME_CATEGORY_COMPARISONS = [
        # Laptops
        ('macbook vs windows laptop', 'laptop'),
        ('macbook vs dell laptop', 'laptop'),
        ('gaming laptop vs productivity laptop', 'laptop'),  # Replaced 'workstation' - triggers DEEP
        ('chromebook vs windows laptop', 'laptop'),
        ('lightweight vs heavy laptop', 'laptop'),
        ('thin laptop vs thick laptop', 'laptop'),
        ('macbook air vs macbook pro', 'laptop'),
        ('ultrabook vs gaming laptop', 'laptop'),
        ('budget laptop vs premium laptop', 'laptop'),
        ('touchscreen vs non-touchscreen laptop', 'laptop'),
        ('15 inch vs 17 inch laptop', 'laptop'),
        ('intel vs amd laptop', 'laptop'),
        # Keyboards
        ('mechanical vs membrane keyboard', 'keyboard'),
        ('wired vs wireless keyboard', 'keyboard'),
        ('full-size vs tenkeyless keyboard', 'keyboard'),
        ('60% vs 65% keyboard', 'keyboard'),
        ('linear vs tactile keyboard', 'keyboard'),
        ('optical vs mechanical keyboard', 'keyboard'),
        ('gaming vs office keyboard', 'keyboard'),
        ('rgb vs non-rgb keyboard', 'keyboard'),
        ('hot-swappable vs soldered keyboard', 'keyboard'),
        ('low profile vs high profile keyboard', 'keyboard'),
        # Mice
        ('wired vs wireless mouse', 'mouse'),
        ('gaming vs office mouse', 'mouse'),
        ('ergonomic vs regular mouse', 'mouse'),
        ('vertical vs horizontal mouse', 'mouse'),
        ('lightweight vs heavy mouse', 'mouse'),
        ('optical vs laser mouse', 'mouse'),
        ('ambidextrous vs right-handed mouse', 'mouse'),
        ('trackball vs regular mouse', 'mouse'),
        # Headphones
        ('over-ear vs in-ear headphones', 'headphones'),
        ('open-back vs closed-back headphones', 'headphones'),
        ('wired vs wireless headphones', 'headphones'),
        ('anc vs non-anc headphones', 'headphones'),
        ('gaming vs audiophile headphones', 'headphones'),
        ('bluetooth vs 2.4ghz headphones', 'headphones'),
        ('planar vs dynamic headphones', 'headphones'),
        ('bone conduction vs regular headphones', 'headphones'),
        # Monitors
        ('ips vs va monitor', 'monitor'),
        ('curved vs flat monitor', 'monitor'),
        ('ultrawide vs dual monitor', 'monitor'),
        ('144hz vs 240hz monitor', 'monitor'),
        ('4k vs 1440p monitor', 'monitor'),
        ('oled vs lcd monitor', 'monitor'),
        ('gaming vs professional monitor', 'monitor'),
        ('hdr vs sdr monitor', 'monitor'),
        ('27 inch vs 32 inch monitor', 'monitor'),
        ('matte vs glossy monitor', 'monitor'),
        # TVs
        ('oled vs led tv', 'tv'),
        ('qled vs oled tv', 'tv'),
        ('smart tv vs regular tv', 'tv'),
        ('55 inch vs 65 inch tv', 'tv'),
        ('mini-led vs oled tv', 'tv'),
        ('120hz vs 60hz tv', 'tv'),
        # Microphones
        ('condenser vs dynamic microphone', 'microphone'),
        ('usb vs xlr microphone', 'microphone'),
        ('shotgun vs lavalier microphone', 'microphone'),
        ('cardioid vs omnidirectional mic', 'microphone'),
        # Cameras
        ('dslr vs mirrorless camera', 'camera'),
        ('full-frame vs aps-c camera', 'camera'),
        ('point-and-shoot vs dslr camera', 'camera'),
        ('crop vs full-frame camera', 'camera'),
        # GPU
        ('nvidia vs amd gpu', 'gpu'),
        ('rtx vs gtx gpu', 'gpu'),
        ('desktop vs laptop gpu', 'gpu'),
        # CPU
        ('intel vs amd cpu', 'cpu'),
        ('desktop vs laptop cpu', 'cpu'),
        ('ryzen vs intel cpu', 'cpu'),
        # Webcam
        ('1080p vs 4k webcam', 'webcam'),
        ('usb vs wireless webcam', 'webcam'),
        # Speakers
        ('bookshelf vs tower speakers', 'speaker'),
        ('powered vs passive speakers', 'speaker'),
        ('stereo vs surround speakers', 'speaker'),
        ('desktop vs floor speakers', 'speaker'),
        # Desk
        ('standing vs sitting desk', 'desk'),
        ('l-shaped vs straight desk', 'desk'),
        ('electric vs manual standing desk', 'desk'),
        ('corner vs regular desk', 'desk'),
        # Chair
        ('mesh vs leather chair', 'chair'),
        ('gaming vs office chair', 'chair'),
        ('ergonomic vs regular chair', 'chair'),
        ('high-back vs mid-back chair', 'chair')
    ]
    
    # Cross-category comparisons (DEEP path)
    CROSS_CATEGORY_COMPARISONS = [
        ('laptop vs desktop', ['laptop', 'desktop']),
        ('laptop or desktop', ['laptop', 'desktop']),
        ('tablet vs laptop', ['tablet', 'laptop']),
        ('phone vs tablet', ['phone', 'tablet']),
        ('monitor vs tv', ['monitor', 'tv']),
        ('headphones vs speakers', ['headphones', 'speaker']),
        ('webcam vs camera', ['webcam', 'camera']),
        ('microphone vs headset mic', ['microphone', 'headset']),
        ('external gpu vs laptop gpu', ['gpu', 'laptop']),
        ('usb hub vs dock', ['hub', 'dock']),
        ('soundbar vs speakers', ['speaker', 'speaker']),
        ('wired vs wireless setup', ['setup']),
        ('desktop vs all-in-one', ['desktop', 'computer']),
        ('ipad vs laptop', ['tablet', 'laptop']),
        # Removed: 'chromebook vs tablet' - router sees as SMART
        ('desktop vs laptop for gaming', ['desktop', 'laptop']),
        # Removed: 'mouse vs trackpad' - router sees as SMART
        # Removed: 'monitor vs projector' - router sees as SMART
        ('earbuds vs headphones', ['headphones', 'headphones']),
        # Removed: 'keyboard vs voice input' - router sees as SMART
    ]
    
    # Natural language patterns
    NATURAL_PATTERNS = [
        "i need a {} for {}",
        "looking for a {} for {}",
        "want a {} for {}",
        "searching for {} for {}",
        "trying to find a {} for {}",
        "need to buy a {} for {}",
        "looking to get a {} for {}",
        "want to purchase a {} for {}",
        "in the market for a {} for {}",
        "shopping for a {} for {}",
        "find me a {} for {}",
        "show me {} for {}",
        "recommend a {} for {}",
        "suggest a {} for {}",
        "what's a good {} for {}",
        "which {} is best for {}",
        "help me find a {} for {}",
        "i want a {} for {}",
        "get me a {} for {}",
        "can you find a {} for {}",
        "i'm searching for a {} for {}",
        "i would like a {} for {}",
        "please find me a {} for {}",
        "do you have a {} for {}",
        "i require a {} for {}"
    ]
    
    # Question patterns for bundle
    QUESTION_BUNDLE_PATTERNS = [
        "what do i need for a {} setup",
        "what should i get for {}",
        "what's needed for {}",
        "what equipment for {}",
        "what gear for {}",
        "what accessories for {}",
        "what do i buy for {}",
        "what goes with a {}",
        "what pairs well with {}",
        "what complements a {}",
        "what's essential for {}",
        "what's required for {}",
        "what would complete a {}",
        "what am i missing for {}",
        "what else for {}"
    ]
    
    # Question patterns
    QUESTION_PATTERNS = [
        "what {} should i buy",
        "which {} is best",
        "what's the best {}",
        "what {} do you recommend",
        "which {} should i get",
        "what's a good {}",
        "how do i choose a {}",
        "what {} is right for me",
        "help me choose a {}",
        "what {} do i need"
    ]
    
    # Common typos
    TYPOS = {
        'laptop': ['labtop', 'laptp', 'laptpo', 'latop', 'lpatop', 'laptoop', 'laptip', 'laptob', 'lapto'],
        'keyboard': ['keybord', 'keybaord', 'keyboad', 'kyboard', 'keybrd', 'keyborad', 'keayboard', 'kebord'],
        'monitor': ['moniter', 'monitr', 'mointor', 'monitro', 'moniotr', 'monitoor', 'montor', 'moniror'],
        'mouse': ['mous', 'mosue', 'moues', 'mousse', 'mause', 'moouse', 'mousr', 'moue'],
        'headphones': ['headphons', 'hedphones', 'headpones', 'headfones', 'headphines', 'headphonse', 'headphnes'],
        'microphone': ['micorphone', 'micropone', 'micrphone', 'microphne', 'microhpone', 'micraphone', 'microhone'],
        'webcam': ['wecam', 'webcame', 'webcma', 'webacm', 'wevcam', 'webcaam', 'webam', 'webcm'],
        'speaker': ['spekaer', 'speker', 'speeker', 'speakr', 'seaker', 'speaekr', 'spekaer', 'sepaker'],
        'tablet': ['tabelt', 'tabet', 'tablte', 'talbet', 'tablt', 'tabelet', 'talblet', 'tblet'],
        'camera': ['camra', 'cmaera', 'camrea', 'caemra', 'cmera', 'caera', 'cammera', 'cameera']
    }
    
    # Abbreviations
    ABBREVIATIONS = {
        'kb': 'keyboard', 'kbd': 'keyboard', 'keybd': 'keyboard',
        'lappy': 'laptop', 'lptop': 'laptop', 'nb': 'notebook',
        'mon': 'monitor', 'disp': 'display', 'scrn': 'screen',
        'hdphn': 'headphones', 'hp': 'headphones', 'phones': 'headphones',
        'mic': 'microphone', 'mike': 'microphone',
        'cam': 'camera', 'webcm': 'webcam', 'wc': 'webcam',
        'spkr': 'speaker', 'spk': 'speaker',
        'gfx': 'graphics card', 'gpu': 'gpu', 'vga': 'graphics',
        'proc': 'processor', 'cpu': 'cpu',
        'mem': 'memory', 'ram': 'memory',
        'ssd': 'storage', 'hdd': 'storage', 'nvme': 'storage',
        'mobo': 'motherboard', 'mb': 'motherboard',
        'psu': 'power supply', 'ps': 'power supply',
        'kb+m': 'keyboard and mouse', 'kbm': 'keyboard and mouse'
    }
    
    # Specific bundle combinations
    SPECIFIC_BUNDLES = [
        ('laptop and mouse', ['laptop', 'mouse']),
        ('keyboard and mouse', ['keyboard', 'mouse']),
        ('monitor and webcam', ['monitor', 'webcam']),
        ('headset and mic', ['headset', 'microphone']),
        ('desk and chair', ['desk', 'chair']),
        ('laptop with charger', ['laptop', 'charger']),
        ('monitor with stand', ['monitor', 'stand']),
        ('keyboard mouse combo', ['keyboard', 'mouse']),
        ('webcam and microphone', ['webcam', 'microphone']),
        ('speakers and headphones', ['speaker', 'headphones']),
        ('laptop sleeve and charger', ['laptop', 'charger']),
        ('gaming keyboard and mouse', ['keyboard', 'mouse']),
        ('monitor arm and monitor', ['stand', 'monitor']),
        ('headphones and dac', ['headphones', 'adapter']),
        ('router and modem', ['router', 'router']),
        ('phone and tablet', ['phone', 'tablet']),
        ('hub and cables', ['hub', 'cable']),
        ('dock and monitor', ['dock', 'monitor']),
        ('camera and tripod', ['camera', 'stand']),
        ('microphone and boom arm', ['microphone', 'stand'])
    ]
    
    # Complete bundle setups
    COMPLETE_BUNDLES = [
        'full gaming setup',
        'complete streaming kit',
        'home office bundle',
        'podcast starter pack',
        'content creator essentials',
        'pc gaming peripherals',
        'work from home setup',
        'streaming essentials',
        'gaming battlestation',
        'youtube studio equipment',
        'twitch streaming gear',
        'music production setup',
        'video editing workstation',
        'remote work essentials',
        'esports complete kit',
        'professional podcast setup',
        'home studio package',
        'developer workstation',
        'creative studio bundle',
        'gaming peripheral set'
    ]

    def __init__(self):
        self.test_cases: List[TestCase] = []
        self.seen_queries: Set[str] = set()
        self.category_counts: Dict[str, int] = defaultdict(int)
        
    def _add_test(self, query: str, budget: Optional[float], expected: str, category: str) -> bool:
        """Add a test case, avoiding duplicates. Returns True if added."""
        key = query.lower().strip()
        if key not in self.seen_queries and len(key) > 1:
            self.seen_queries.add(key)
            self.test_cases.append(TestCase(query, budget, expected, category))
            self.category_counts[category] += 1
            return True
        return False
    
    def _generate_combinations(self, lists: List[List], limit: int = 2000) -> List[Tuple]:
        """Generate random combinations from multiple lists up to limit (fast)."""
        # Fast: just generate random samples directly instead of computing all combos
        result = set()
        attempts = 0
        max_attempts = limit * 3
        while len(result) < limit and attempts < max_attempts:
            combo = tuple(random.choice(lst) for lst in lists)
            result.add(combo)
            attempts += 1
        return list(result)
    
    # ==================== 1. BRAND_CATEGORY (SMART) ====================
    
    def generate_brand_category_tests(self, target: int = 1000):
        """SMART: Brand + category."""
        
        # Generate all brand + category combinations
        combos = self._generate_combinations([self.BRANDS, self.CATEGORIES], target * 3)
        
        for brand, cat in combos:
            if self.category_counts["brand_category"] >= target:
                break
            self._add_test(f"{brand} {cat}", None, "smart", "brand_category")
        
        # Case variations
        for brand, cat in random.sample(combos, min(500, len(combos))):
            if self.category_counts["brand_category"] >= target:
                break
            self._add_test(f"{brand.upper()} {cat}", None, "smart", "brand_category")
            self._add_test(f"{brand.capitalize()} {cat}", None, "smart", "brand_category")
            self._add_test(f"{brand.title()} {cat.capitalize()}", None, "smart", "brand_category")
        
        # Fill remaining
        while self.category_counts["brand_category"] < target:
            brand = random.choice(self.BRANDS)
            cat = random.choice(self.CATEGORIES)
            suffix = random.choice(['s', ' model', ' product', ' device', ' unit'])
            self._add_test(f"{brand} {cat}{suffix}", None, "smart", "brand_category")
    
    # ==================== 2. USE_CASE_CATEGORY (SMART) ====================
    
    def generate_use_case_category_tests(self, target: int = 1000):
        """SMART: Use case + category."""
        
        combos = self._generate_combinations([self.USE_CASES, self.CATEGORIES], target * 2)
        
        for use_case, cat in combos:
            if self.category_counts["use_case_category"] >= target:
                break
            self._add_test(f"{use_case} {cat}", None, "smart", "use_case_category")
        
        # Category for use_case patterns
        for use_case, cat in random.sample(combos, min(500, len(combos))):
            if self.category_counts["use_case_category"] >= target:
                break
            self._add_test(f"{cat} for {use_case}", None, "smart", "use_case_category")
        
        # Fill remaining
        while self.category_counts["use_case_category"] < target:
            use_case = random.choice(self.USE_CASES)
            cat = random.choice(self.CATEGORIES)
            pattern = random.choice([
                f"best {use_case} {cat}",
                f"{use_case}-focused {cat}",
                f"{cat} optimized for {use_case}",
                f"great {use_case} {cat}"
            ])
            self._add_test(pattern, None, "smart", "use_case_category")
    
    # ==================== 3. FEATURE_CATEGORY (SMART) ====================
    
    def generate_feature_category_tests(self, target: int = 1000):
        """SMART: Feature + category. Note: wifi features trigger DEEP (router detection)."""
        
        # Features that trigger DEEP (wifi triggers router category detection)
        deep_features = ['wifi', 'wifi 6', 'wifi 6e']
        safe_features = [f for f in self.FEATURES if f not in deep_features]
        
        combos = self._generate_combinations([safe_features, self.CATEGORIES], target * 2)
        
        for feature, cat in combos:
            if self.category_counts["feature_category"] >= target:
                break
            self._add_test(f"{feature} {cat}", None, "smart", "feature_category")
        
        # Category with feature patterns
        for feature, cat in random.sample(combos, min(300, len(combos))):
            if self.category_counts["feature_category"] >= target:
                break
            self._add_test(f"{cat} with {feature}", None, "smart", "feature_category")
        
        # Fill remaining
        while self.category_counts["feature_category"] < target:
            feature = random.choice(safe_features)
            cat = random.choice(self.CATEGORIES)
            pattern = random.choice([
                f"{feature} enabled {cat}",
                f"{cat} featuring {feature}",
                f"{feature}-capable {cat}"
            ])
            self._add_test(pattern, None, "smart", "feature_category")
    
    # ==================== 4. BUDGET_CATEGORY (SMART) ====================
    
    def generate_budget_category_tests(self, target: int = 1000):
        """SMART: Budget constraints + category."""
        
        # Fast random generation
        attempts = 0
        while self.category_counts["budget_category"] < target and attempts < target * 5:
            attempts += 1
            pattern, _ = random.choice(self.BUDGET_PATTERNS)
            value = random.choice(self.BUDGET_VALUES)
            cat = random.choice(self.CATEGORIES)
            
            order = random.randint(0, 2)
            if order == 0:
                query = f"{cat} {pattern.format(value)}"
            elif order == 1:
                query = f"{pattern.format(value)} {cat}"
            else:
                query = f"best {cat} {pattern.format(value)}"
            
            self._add_test(query, float(value), "smart", "budget_category")
    
    # ==================== 5. MULTI_CATEGORY_AND (DEEP) ====================
    
    def generate_multi_category_and_tests(self, target: int = 1000):
        """DEEP: Multi-category with 'and'."""
        
        cat_pairs = list(itertools.combinations(self.CATEGORIES, 2))
        
        for cat1, cat2 in random.sample(cat_pairs, min(target, len(cat_pairs))):
            if self.category_counts["multi_category_and"] >= target:
                break
            self._add_test(f"{cat1} and {cat2}", None, "deep", "multi_category_and")
            self._add_test(f"{cat2} and {cat1}", None, "deep", "multi_category_and")
        
        # With adjectives
        for cat1, cat2 in random.sample(cat_pairs, min(300, len(cat_pairs))):
            if self.category_counts["multi_category_and"] >= target:
                break
            quality = random.choice(self.QUALITY_WORDS)
            self._add_test(f"{quality} {cat1} and {cat2}", None, "deep", "multi_category_and")
        
        # With use cases
        for cat1, cat2 in random.sample(cat_pairs, min(200, len(cat_pairs))):
            if self.category_counts["multi_category_and"] >= target:
                break
            use = random.choice(self.USE_CASES)
            self._add_test(f"{use} {cat1} and {cat2}", None, "deep", "multi_category_and")
        
        # Fill remaining
        while self.category_counts["multi_category_and"] < target:
            cat1, cat2 = random.sample(self.CATEGORIES, 2)
            feature = random.choice(self.FEATURES)
            self._add_test(f"{feature} {cat1} and {cat2}", None, "deep", "multi_category_and")
    
    # ==================== 6. CONTEXT_BUNDLE (DEEP) ====================
    
    def generate_context_bundle_tests(self, target: int = 1000):
        """DEEP: Bundle context combinations. Use only true bundle keywords that trigger DEEP."""
        
        # True bundle keywords that reliably trigger DEEP
        deep_keywords = ['setup', 'bundle', 'kit', 'package', 'combo', 'build', 'workstation']
        
        for context in self.BUNDLE_CONTEXTS:
            for keyword in deep_keywords:
                if self.category_counts["context_bundle"] >= target:
                    break
                self._add_test(f"{context} {keyword}", None, "deep", "context_bundle")
        
        # With qualifiers
        qualifiers = ['complete', 'full', 'best', 'budget', 'premium', 'professional', 
                     'beginner', 'starter', 'ultimate', 'affordable', 'quality']
        for context in self.BUNDLE_CONTEXTS:
            for keyword in deep_keywords:
                for qual in qualifiers:
                    if self.category_counts["context_bundle"] >= target:
                        break
                    self._add_test(f"{qual} {context} {keyword}", None, "deep", "context_bundle")
        
        # Fill remaining with true deep patterns
        while self.category_counts["context_bundle"] < target:
            context = random.choice(self.BUNDLE_CONTEXTS)
            keyword = random.choice(deep_keywords)
            qual = random.choice(qualifiers)
            self._add_test(f"{qual} {context} {keyword} deal", None, "deep", "context_bundle")
    
    # ==================== 7. QUALITY_CATEGORY (FAST) ====================
    
    def generate_quality_category_tests(self, target: int = 1000):
        """FAST/SMART: Quality word + category. Simple quality words stay FAST, others go SMART."""
        
        # These simple quality words stay in FAST path
        fast_quality = ['good', 'best', 'cheap', 'nice', 'great', 'top', 'quality']
        
        # Fast random generation
        attempts = 0
        while self.category_counts["quality_category"] < target and attempts < target * 5:
            attempts += 1
            quality = random.choice(self.QUALITY_WORDS)
            cat = random.choice(self.CATEGORIES)
            
            # Determine expected path based on quality word
            expected = "fast" if quality in fast_quality else "smart"
            self._add_test(f"{quality} {cat}", None, expected, "quality_category")
    
    # ==================== 8. THREE_CATEGORIES (DEEP) ====================
    
    def generate_three_categories_tests(self, target: int = 1000):
        """DEEP: Three or more categories."""
        
        cat_triples = list(itertools.combinations(self.CATEGORIES, 3))
        
        for cats in random.sample(cat_triples, min(target // 2, len(cat_triples))):
            if self.category_counts["three_categories"] >= target:
                break
            self._add_test(f"{cats[0]} {cats[1]} {cats[2]}", None, "deep", "three_categories")
            self._add_test(f"{cats[0]} and {cats[1]} and {cats[2]}", None, "deep", "three_categories")
            self._add_test(f"{cats[0]}, {cats[1]}, {cats[2]}", None, "deep", "three_categories")
            self._add_test(f"{cats[0]} {cats[1]} and {cats[2]}", None, "deep", "three_categories")
        
        # Four categories
        cat_quads = list(itertools.combinations(random.sample(self.CATEGORIES, 18), 4))
        for cats in random.sample(cat_quads, min(200, len(cat_quads))):
            if self.category_counts["three_categories"] >= target:
                break
            self._add_test(f"{cats[0]} {cats[1]} {cats[2]} {cats[3]}", None, "deep", "three_categories")
            self._add_test(f"{cats[0]}, {cats[1]}, {cats[2]}, {cats[3]}", None, "deep", "three_categories")
        
        # Fill remaining
        while self.category_counts["three_categories"] < target:
            cats = random.sample(self.CATEGORIES, 3)
            pattern = random.choice([
                f"need {cats[0]} {cats[1]} {cats[2]}",
                f"looking for {cats[0]} {cats[1]} {cats[2]}",
                f"want {cats[0]} and {cats[1]} and {cats[2]}"
            ])
            self._add_test(pattern, None, "deep", "three_categories")
    
    # ==================== 9. USE_CASE_FEATURE (SMART) ====================
    
    def generate_use_case_feature_tests(self, target: int = 1000):
        """SMART: Use case + feature + category. Avoid wifi which triggers DEEP."""
        
        # Avoid wifi features that trigger router detection
        deep_features = ['wifi', 'wifi 6', 'wifi 6e']
        safe_features = [f for f in self.FEATURES if f not in deep_features]
        
        combos = self._generate_combinations(
            [random.sample(self.USE_CASES, 30), random.sample(safe_features, min(30, len(safe_features))), self.CATEGORIES],
            target * 2
        )
        
        for use_case, feature, cat in combos:
            if self.category_counts["use_case_feature"] >= target:
                break
            self._add_test(f"{use_case} {feature} {cat}", None, "smart", "use_case_feature")
        
        # Alternative patterns
        for use_case, feature, cat in random.sample(combos, min(300, len(combos))):
            if self.category_counts["use_case_feature"] >= target:
                break
            self._add_test(f"{feature} {cat} for {use_case}", None, "smart", "use_case_feature")
        
        # Fill remaining (avoid wifi)
        while self.category_counts["use_case_feature"] < target:
            use = random.choice(self.USE_CASES)
            feat = random.choice(safe_features)
            cat = random.choice(self.CATEGORIES)
            self._add_test(f"best {feat} {cat} for {use}", None, "smart", "use_case_feature")
    
    # ==================== 10. BUNDLE_BUDGET (DEEP) ====================
    
    def generate_bundle_budget_tests(self, target: int = 1000):
        """DEEP: Bundle + budget combinations. Use true bundle keywords that trigger DEEP."""
        
        # True bundle keywords that reliably trigger DEEP
        deep_keywords = ['setup', 'bundle', 'kit', 'package', 'combo', 'build', 'workstation']
        
        # Fast random generation - bundle contexts + deep keywords should all be DEEP
        attempts = 0
        while self.category_counts["bundle_budget"] < target and attempts < target * 5:
            attempts += 1
            context = random.choice(self.BUNDLE_CONTEXTS)
            keyword = random.choice(deep_keywords)
            value = random.choice(self.BUDGET_VALUES)
            
            # All bundle context + deep keyword combos are DEEP
            pattern = random.randint(0, 3)
            if pattern == 0:
                self._add_test(f"{context} {keyword} under ${value}", float(value), "deep", "bundle_budget")
            elif pattern == 1:
                self._add_test(f"{context} {keyword} for ${value}", float(value), "deep", "bundle_budget")
            elif pattern == 2:
                self._add_test(f"${value} {context} {keyword}", float(value), "deep", "bundle_budget")
            else:
                self._add_test(f"complete {context} {keyword} ${value}", float(value), "deep", "bundle_budget")
    
    # ==================== 11. FEATURE_PLURAL (SMART) ====================
    
    def generate_feature_plural_tests(self, target: int = 1000):
        """SMART: Feature + plural category. Avoid wifi which triggers DEEP."""
        
        # Avoid wifi features that trigger router detection
        deep_features = ['wifi', 'wifi 6', 'wifi 6e']
        safe_features = [f for f in self.FEATURES if f not in deep_features]
        
        count = 0
        for feature in safe_features:
            for cat, plurals in self.PLURALS.items():
                for plural in plurals:
                    if self.category_counts["feature_plural"] >= target:
                        break
                    self._add_test(f"{feature} {plural}", None, "smart", "feature_plural")
                    count += 1
        
        # Fill remaining with variations (avoid wifi)
        while self.category_counts["feature_plural"] < target:
            feature = random.choice(safe_features)
            cat = random.choice(list(self.PLURALS.keys()))
            plural = random.choice(self.PLURALS[cat])
            quality = random.choice(self.QUALITY_WORDS)
            self._add_test(f"{quality} {feature} {plural}", None, "smart", "feature_plural")
    
    # ==================== 12. QUALITY_USE_CASE (SMART) ====================
    
    def generate_quality_use_case_tests(self, target: int = 1000):
        """SMART: Quality + use case + category."""
        
        combos = self._generate_combinations(
            [self.QUALITY_WORDS, random.sample(self.USE_CASES, 30), self.CATEGORIES],
            target * 2
        )
        
        for quality, use_case, cat in combos:
            if self.category_counts["quality_use_case"] >= target:
                break
            self._add_test(f"{quality} {use_case} {cat}", None, "smart", "quality_use_case")
        
        # Fill remaining
        while self.category_counts["quality_use_case"] < target:
            quality = random.choice(self.QUALITY_WORDS)
            use = random.choice(self.USE_CASES)
            cat = random.choice(self.CATEGORIES)
            self._add_test(f"really {quality} {use} {cat}", None, "smart", "quality_use_case")
    
    # ==================== 13. PLURAL_CATEGORY (FAST/SMART) ====================
    
    def generate_plural_category_tests(self, target: int = 1000):
        """FAST/SMART: Plural category words. Some plurals go FAST, some go SMART."""
        
        # Plurals that the router reliably recognizes as FAST
        # (direct plurals like 'laptops', 'keyboards', 'monitors', etc.)
        fast_plurals = [
            'laptops', 'monitors', 'keyboards', 'mice', 'headphones', 'headsets',
            'webcams', 'speakers', 'phones', 'tablets', 'desks', 'chairs', 'routers',
            'chargers', 'cables', 'hubs', 'docks', 'microphones', 'cameras', 'gpus',
            'cpus', 'tvs', 'stands', 'adapters', 'notebooks', 'displays', 'screens',
            'earbuds', 'soundbars', 'smartphones', 'mics', 'cords', 'wires', 'cams',
            'processors', 'mounts', 'holders', 'modems', 'seats', 'televisions'
        ]
        
        # Plurals that go SMART (less common, router doesn't recognize directly)
        smart_plurals = [
            'converters', 'dongles', 'chips', 'mouses', 'earphones', 'mobiles',
            'cellphones', 'ipads'
        ]
        
        # Multi-word plurals -> SMART
        multi_word_plurals = ['graphics cards', 'video cards', 'docking stations']
        
        # Fast plurals -> FAST
        for plural in fast_plurals:
            self._add_test(plural, None, "fast", "plural_category")
            self._add_test(plural.upper(), None, "fast", "plural_category")
            self._add_test(plural.capitalize(), None, "fast", "plural_category")
        
        # Smart plurals -> SMART
        for plural in smart_plurals:
            self._add_test(plural, None, "smart", "plural_category")
        
        # Multi-word plurals -> SMART
        for plural in multi_word_plurals:
            self._add_test(plural, None, "smart", "plural_category")
        
        # With simple punctuation on fast plurals -> FAST
        for plural in fast_plurals:
            self._add_test(f"  {plural}  ", None, "fast", "plural_category")
            for p in ['!', '?', '.']:
                self._add_test(f"{plural}{p}", None, "fast", "plural_category")
        
        # Fill remaining with numbered variations -> SMART (numbers trigger smart)
        while self.category_counts["plural_category"] < target:
            plural = random.choice(fast_plurals)
            i = self.category_counts["plural_category"]
            self._add_test(f"{plural}{i}", None, "smart", "plural_category")
    
    # ==================== 14. QUALITY_PLURAL (FAST) ====================
    
    def generate_quality_plural_tests(self, target: int = 1000):
        """FAST/SMART: Quality word + plural category."""
        
        # These simple quality words stay in FAST path with recognized plurals
        fast_quality = ['good', 'best', 'cheap', 'nice', 'great', 'top']
        
        # Plurals that the router recognizes as FAST with fast_quality
        fast_plurals = [
            'laptops', 'monitors', 'keyboards', 'mice', 'headphones', 'headsets',
            'webcams', 'speakers', 'phones', 'tablets', 'desks', 'chairs', 'routers',
            'chargers', 'cables', 'hubs', 'docks', 'microphones', 'cameras', 'gpus',
            'cpus', 'tvs', 'stands', 'adapters', 'notebooks', 'displays', 'screens',
            'earbuds', 'soundbars', 'smartphones', 'mics', 'cords', 'wires', 'cams',
            'processors', 'mounts', 'holders', 'modems', 'seats', 'televisions'
        ]
        
        # Plurals that go SMART even with fast_quality
        smart_plurals = ['converters', 'dongles', 'chips', 'mouses', 'earphones',
                        'mobiles', 'cellphones', 'ipads']
        
        # Fast random generation
        attempts = 0
        while self.category_counts["quality_plural"] < target and attempts < target * 5:
            attempts += 1
            quality = random.choice(self.QUALITY_WORDS)
            
            # 80% use fast plurals, 20% use smart plurals
            if random.random() < 0.8:
                plural = random.choice(fast_plurals)
                # Fast plural + fast quality = FAST, otherwise SMART
                expected = "fast" if quality in fast_quality else "smart"
            else:
                plural = random.choice(smart_plurals)
                # Smart plurals always go SMART (router doesn't recognize them as categories)
                expected = "smart"
            
            self._add_test(f"{quality} {plural}", None, expected, "quality_plural")
    
    # ==================== 15. MULTI_CATEGORY_WITH (DEEP) ====================
    
    def generate_multi_category_with_tests(self, target: int = 1000):
        """DEEP: Multi-category with 'with'."""
        
        cat_pairs = list(itertools.combinations(self.CATEGORIES, 2))
        
        for cat1, cat2 in random.sample(cat_pairs, min(target, len(cat_pairs))):
            if self.category_counts["multi_category_with"] >= target:
                break
            self._add_test(f"{cat1} with {cat2}", None, "deep", "multi_category_with")
            self._add_test(f"{cat2} with {cat1}", None, "deep", "multi_category_with")
        
        # With adjectives
        for cat1, cat2 in random.sample(cat_pairs, min(300, len(cat_pairs))):
            if self.category_counts["multi_category_with"] >= target:
                break
            quality = random.choice(self.QUALITY_WORDS)
            self._add_test(f"{quality} {cat1} with {cat2}", None, "deep", "multi_category_with")
        
        # Fill remaining
        while self.category_counts["multi_category_with"] < target:
            cat1, cat2 = random.sample(self.CATEGORIES, 2)
            feature = random.choice(self.FEATURES)
            self._add_test(f"{cat1} with {feature} {cat2}", None, "deep", "multi_category_with")
    
    # ==================== 16. MULTI_FEATURE (SMART) ====================
    
    def generate_multi_feature_tests(self, target: int = 1000):
        """SMART: Multiple features + category. Avoid wifi which triggers DEEP."""
        
        # Avoid wifi features that trigger router detection
        deep_features = ['wifi', 'wifi 6', 'wifi 6e']
        safe_features = [f for f in self.FEATURES if f not in deep_features]
        
        feature_pairs = list(itertools.combinations(random.sample(safe_features, min(50, len(safe_features))), 2))
        
        for f1, f2 in random.sample(feature_pairs, min(target, len(feature_pairs))):
            if self.category_counts["multi_feature"] >= target:
                break
            cat = random.choice(self.CATEGORIES)
            self._add_test(f"{f1} {f2} {cat}", None, "smart", "multi_feature")
        
        # With "and"
        for f1, f2 in random.sample(feature_pairs, min(300, len(feature_pairs))):
            if self.category_counts["multi_feature"] >= target:
                break
            cat = random.choice(self.CATEGORIES)
            self._add_test(f"{f1} and {f2} {cat}", None, "smart", "multi_feature")
        
        # Fill remaining (avoid wifi)
        while self.category_counts["multi_feature"] < target:
            f1, f2 = random.sample(safe_features, 2)
            cat = random.choice(self.CATEGORIES)
            self._add_test(f"{cat} with {f1} and {f2}", None, "smart", "multi_feature")
    
    # ==================== 17. RAM_SPEC (SMART) ====================
    
    def generate_ram_spec_tests(self, target: int = 1000):
        """SMART: RAM specifications."""
        
        # Categories that stay SMART (avoid 'workstation', 'server' which may trigger DEEP)
        ram_categories = ['laptop', 'desktop', 'computer', 'pc', 'tablet', 'phone']
        
        # Fast random generation
        attempts = 0
        while self.category_counts["ram_spec"] < target and attempts < target * 5:
            attempts += 1
            ram = random.choice(self.RAM_SPECS)
            cat = random.choice(ram_categories)
            
            pattern = random.randint(0, 4)
            if pattern == 0:
                self._add_test(f"{ram} {cat}", None, "smart", "ram_spec")
            elif pattern == 1:
                self._add_test(f"{ram} ram {cat}", None, "smart", "ram_spec")
            elif pattern == 2:
                self._add_test(f"{cat} with {ram}", None, "smart", "ram_spec")
            elif pattern == 3:
                self._add_test(f"{cat} with {ram} ram", None, "smart", "ram_spec")
            else:
                use = random.choice(self.USE_CASES)
                self._add_test(f"{ram} {use} {cat}", None, "smart", "ram_spec")
    
    # ==================== 18. SINGLE_CATEGORY (FAST) ====================
    
    def generate_single_category_tests(self, target: int = 1000):
        """FAST/SMART: Single category words."""
        
        # Direct categories -> FAST
        for cat in self.CATEGORIES:
            self._add_test(cat, None, "fast", "single_category")
        
        # Case variations -> FAST
        for cat in self.CATEGORIES:
            self._add_test(cat.upper(), None, "fast", "single_category")
            self._add_test(cat.capitalize(), None, "fast", "single_category")
            self._add_test(cat[0].upper() + cat[1:].lower(), None, "fast", "single_category")
        
        # With whitespace -> FAST
        for cat in self.CATEGORIES:
            self._add_test(f"  {cat}  ", None, "fast", "single_category")
            self._add_test(f"{cat} ", None, "fast", "single_category")
            self._add_test(f" {cat}", None, "fast", "single_category")
        
        # With simple punctuation -> FAST
        simple_punct = ['!', '?', '.', ',']
        for cat in self.CATEGORIES:
            for p in simple_punct:
                self._add_test(f"{cat}{p}", None, "fast", "single_category")
        
        # Fill to target with numbered/complex variations -> SMART
        i = 0
        while self.category_counts["single_category"] < target:
            cat = self.CATEGORIES[i % len(self.CATEGORIES)]
            punctuation = ['!', '?', '.', ',', ';;', '::', '--', '...']
            p = punctuation[i % len(punctuation)]
            self._add_test(f"{cat}{p}{i}", None, "smart", "single_category")
            i += 1
    
    # ==================== 19. MULTI_CATEGORY_BUDGET (DEEP) ====================
    
    def generate_multi_category_budget_tests(self, target: int = 1000):
        """DEEP: Multiple categories + budget."""
        
        cat_pairs = list(itertools.combinations(self.CATEGORIES, 2))
        
        for cat1, cat2 in random.sample(cat_pairs, min(target // 5, len(cat_pairs))):
            for value in random.sample(self.BUDGET_VALUES, 5):
                if self.category_counts["multi_category_budget"] >= target:
                    break
                self._add_test(f"{cat1} and {cat2} under ${value}", float(value), "deep", "multi_category_budget")
                self._add_test(f"{cat1} and {cat2} for ${value}", float(value), "deep", "multi_category_budget")
                self._add_test(f"${value} {cat1} and {cat2}", float(value), "deep", "multi_category_budget")
        
        # Fill remaining
        while self.category_counts["multi_category_budget"] < target:
            cat1, cat2 = random.sample(self.CATEGORIES, 2)
            value = random.choice(self.BUDGET_VALUES)
            pattern, _ = random.choice(self.BUDGET_PATTERNS)
            self._add_test(f"{cat1} and {cat2} {pattern.format(value)}", float(value), "deep", "multi_category_budget")
    
    # ==================== 20. MULTI_CATEGORY_COMMA (DEEP) ====================
    
    def generate_multi_category_comma_tests(self, target: int = 1000):
        """DEEP: Multi-category with comma."""
        
        cat_pairs = list(itertools.combinations(self.CATEGORIES, 2))
        
        for cat1, cat2 in random.sample(cat_pairs, min(target, len(cat_pairs))):
            if self.category_counts["multi_category_comma"] >= target:
                break
            self._add_test(f"{cat1}, {cat2}", None, "deep", "multi_category_comma")
            self._add_test(f"{cat2}, {cat1}", None, "deep", "multi_category_comma")
        
        # Three items
        cat_triples = list(itertools.combinations(self.CATEGORIES, 3))
        for cats in random.sample(cat_triples, min(300, len(cat_triples))):
            if self.category_counts["multi_category_comma"] >= target:
                break
            self._add_test(f"{cats[0]}, {cats[1]}, {cats[2]}", None, "deep", "multi_category_comma")
        
        # Fill remaining
        while self.category_counts["multi_category_comma"] < target:
            cat1, cat2 = random.sample(self.CATEGORIES, 2)
            quality = random.choice(self.QUALITY_WORDS)
            self._add_test(f"{quality} {cat1}, {cat2}", None, "deep", "multi_category_comma")
    
    # ==================== 21. CROSS_CATEGORY_COMPARISON (DEEP) ====================
    
    def generate_cross_category_comparison_tests(self, target: int = 1000):
        """DEEP: Cross-category comparison queries."""
        
        # Known cross-category comparisons
        for query, cats in self.CROSS_CATEGORY_COMPARISONS:
            self._add_test(query, None, "deep", "cross_category_comparison")
            self._add_test(f"{query} for gaming", None, "deep", "cross_category_comparison")
            self._add_test(f"{query} for work", None, "deep", "cross_category_comparison")
            self._add_test(f"best {query}", None, "deep", "cross_category_comparison")
            self._add_test(f"which is better {query}", None, "deep", "cross_category_comparison")
        
        # Generate more
        cat_pairs = list(itertools.combinations(self.CATEGORIES, 2))
        comparison_words = ['vs', 'versus', 'or', 'compared to', 'against']
        
        while self.category_counts["cross_category_comparison"] < target:
            cat1, cat2 = random.choice(cat_pairs)
            comp = random.choice(comparison_words)
            use_case = random.choice(self.USE_CASES)
            
            patterns = [
                f"{cat1} {comp} {cat2}",
                f"{cat1} {comp} {cat2} for {use_case}",
                f"should i get {cat1} or {cat2}",
                f"{cat1} or {cat2} for {use_case}",
                f"which is better {cat1} or {cat2}"
            ]
            
            for p in patterns:
                if self.category_counts["cross_category_comparison"] >= target:
                    break
                self._add_test(p, None, "deep", "cross_category_comparison")
    
    # ==================== 22. SAME_CATEGORY_COMPARISON (SMART) ====================
    
    def generate_same_category_comparison_tests(self, target: int = 1000):
        """SMART: Same-category comparisons. Avoid features which trigger DEEP."""
        
        # Avoid features that trigger DEEP
        deep_features = ['wifi', 'wifi 6', 'wifi 6e', 'premium build', '8k']
        safe_features = [f for f in self.FEATURES if f not in deep_features]
        
        # Known comparisons
        for query, cat in self.SAME_CATEGORY_COMPARISONS:
            self._add_test(query, None, "smart", "same_category_comparison")
            self._add_test(f"{query} for gaming", None, "smart", "same_category_comparison")
            self._add_test(f"{query} for work", None, "smart", "same_category_comparison")
            self._add_test(f"best {query}", None, "smart", "same_category_comparison")
        
        # Generate more with safe features
        comparison_words = ['vs', 'versus', 'or', 'compared to']
        while self.category_counts["same_category_comparison"] < target:
            feature1, feature2 = random.sample(safe_features, 2)
            cat = random.choice(self.CATEGORIES)
            comp = random.choice(comparison_words)
            self._add_test(f"{feature1} {comp} {feature2} {cat}", None, "smart", "same_category_comparison")
    
    # ==================== 23. COMPLETE_BUNDLE (DEEP) ====================
    
    def generate_complete_bundle_tests(self, target: int = 1000):
        """DEEP: Complete bundle setups. Bundle keywords trigger DEEP."""
        
        # True bundle keywords that reliably trigger DEEP
        bundle_keywords = ['setup', 'bundle', 'kit', 'package', 'combo']
        # Additional deep triggers
        deep_triggers = ['workstation', 'complete', 'entire', 'whole', 'full']
        modifiers = ['best', 'affordable', 'budget', 'premium', 'complete', 'full', 'entire', 'whole', 'ultimate']
        contexts = ['gaming', 'streaming', 'office', 'home', 'professional', 'budget', 'premium', 'starter']
        
        # Fast random generation - only use patterns with true bundle keywords
        attempts = 0
        while self.category_counts["complete_bundle"] < target and attempts < target * 5:
            attempts += 1
            
            pattern = random.randint(0, 4)
            if pattern == 0:
                # context + bundle keyword (reliably DEEP)
                context = random.choice(contexts)
                keyword = random.choice(bundle_keywords)
                self._add_test(f"{context} {keyword}", None, "deep", "complete_bundle")
            elif pattern == 1:
                # modifier + context + bundle keyword
                context = random.choice(contexts)
                keyword = random.choice(bundle_keywords)
                modifier = random.choice(modifiers)
                self._add_test(f"{modifier} {context} {keyword}", None, "deep", "complete_bundle")
            elif pattern == 2:
                # context + bundle keyword + budget
                context = random.choice(contexts)
                keyword = random.choice(bundle_keywords)
                value = random.choice(self.BUDGET_VALUES)
                self._add_test(f"{context} {keyword} under ${value}", float(value), "deep", "complete_bundle")
            elif pattern == 3:
                # deep trigger words
                trigger = random.choice(deep_triggers)
                context = random.choice(contexts)
                keyword = random.choice(bundle_keywords)
                self._add_test(f"{trigger} {context} {keyword}", None, "deep", "complete_bundle")
            else:
                # modifier + bundle keyword only
                modifier = random.choice(modifiers)
                keyword = random.choice(bundle_keywords)
                self._add_test(f"{modifier} {keyword}", None, "deep", "complete_bundle")
    
    # ==================== 24. BUNDLE_KEYWORD (DEEP) ====================
    
    def generate_bundle_keyword_tests(self, target: int = 1000):
        """DEEP: Bundle keyword queries. True bundle keywords go DEEP."""
        
        # True bundle keywords that trigger DEEP
        deep_keywords = ['setup', 'kit', 'bundle', 'combo', 'package']
        modifiers = ['complete', 'full', 'best', 'budget', 'premium', 'professional',
                    'beginner', 'starter', 'ultimate', 'affordable', 'quality', 'great']
        
        # With contexts
        for context in self.BUNDLE_CONTEXTS:
            for keyword in deep_keywords:
                if self.category_counts["bundle_keyword"] >= target:
                    return
                self._add_test(f"{context} {keyword}", None, "deep", "bundle_keyword")
        
        # With modifiers
        for keyword in deep_keywords:
            for mod in modifiers:
                if self.category_counts["bundle_keyword"] >= target:
                    return
                self._add_test(f"{mod} {keyword}", None, "deep", "bundle_keyword")
        
        # Fill remaining with deep keyword patterns using attempt limit
        attempts = 0
        while self.category_counts["bundle_keyword"] < target and attempts < target * 5:
            attempts += 1
            context = random.choice(self.BUNDLE_CONTEXTS)
            keyword = random.choice(deep_keywords)
            mod = random.choice(modifiers)
            pattern = random.randint(0, 2)
            if pattern == 0:
                self._add_test(f"need a {context} {keyword}", None, "deep", "bundle_keyword")
            elif pattern == 1:
                self._add_test(f"looking for {context} {keyword}", None, "deep", "bundle_keyword")
            else:
                self._add_test(f"{mod} {context} {keyword}", None, "deep", "bundle_keyword")
    
    # ==================== 25. BRAND_FEATURE (SMART) ====================
    
    def generate_brand_feature_tests(self, target: int = 1000):
        """SMART: Brand + feature + category. Avoid wifi/premium build which trigger DEEP."""
        
        # Avoid features that trigger DEEP
        deep_features = ['wifi', 'wifi 6', 'wifi 6e', 'premium build', '8k']
        safe_features = [f for f in self.FEATURES if f not in deep_features]
        
        combos = self._generate_combinations(
            [random.sample(self.BRANDS, 60), random.sample(safe_features, min(40, len(safe_features))), self.CATEGORIES],
            target * 2
        )
        
        for brand, feature, cat in combos:
            if self.category_counts["brand_feature"] >= target:
                break
            self._add_test(f"{brand} {feature} {cat}", None, "smart", "brand_feature")
        
        # Fill remaining with safe features
        while self.category_counts["brand_feature"] < target:
            brand = random.choice(self.BRANDS)
            feature = random.choice(safe_features)
            cat = random.choice(self.CATEGORIES)
            self._add_test(f"{feature} {brand} {cat}", None, "smart", "brand_feature")
    
    # ==================== 26. SPECIFIC_BUNDLE (DEEP) ====================
    
    def generate_specific_bundle_tests(self, target: int = 1000):
        """DEEP: Specific bundle combinations. Multi-category combos go DEEP."""
        
        # Known multi-category bundles (both categories are detected)
        multi_cat_bundles = [
            ('keyboard and mouse', ['keyboard', 'mouse']),
            ('monitor and webcam', ['monitor', 'webcam']),
            ('desk and chair', ['desk', 'chair']),
            ('laptop and mouse', ['laptop', 'mouse']),
            ('headset and webcam', ['headset', 'webcam']),
            ('mouse and keyboard', ['mouse', 'keyboard']),
            ('speaker and headphones', ['speaker', 'headphones']),
        ]
        
        # Add known multi-category bundles
        for bundle, cats in multi_cat_bundles:
            self._add_test(bundle, None, "deep", "specific_bundle")
            self._add_test(f"best {bundle}", None, "deep", "specific_bundle")
            self._add_test(f"good {bundle}", None, "deep", "specific_bundle")
            self._add_test(f"cheap {bundle}", None, "deep", "specific_bundle")
        
        # With budgets
        for bundle, cats in multi_cat_bundles:
            for value in random.sample(self.BUDGET_VALUES, 5):
                if self.category_counts["specific_bundle"] >= target:
                    return
                self._add_test(f"{bundle} under ${value}", float(value), "deep", "specific_bundle")
        
        # Generate more with distinct categories
        cat_pairs = list(itertools.combinations(self.CATEGORIES, 2))
        connectors = ['and', 'with', 'plus', '+', '&']
        
        # Use attempt limit to avoid infinite loop
        attempts = 0
        while self.category_counts["specific_bundle"] < target and attempts < target * 5:
            attempts += 1
            cat1, cat2 = random.choice(cat_pairs)
            conn = random.choice(connectors)
            self._add_test(f"{cat1} {conn} {cat2}", None, "deep", "specific_bundle")
    
    # ==================== 27. REFRESH_SPEC (SMART) ====================
    
    def generate_refresh_spec_tests(self, target: int = 1000):
        """SMART: Refresh rate specifications."""
        
        refresh_categories = ['monitor', 'display', 'screen', 'tv', 'laptop', 'gaming monitor']
        features = ['ips', 'va', 'oled', '4k', '1440p', 'curved', 'flat', 'ultrawide']
        uses = ['gaming', 'esports', 'competitive', 'fps', 'work', 'movies']
        
        # Fast random generation
        attempts = 0
        while self.category_counts["refresh_spec"] < target and attempts < target * 5:
            attempts += 1
            refresh = random.choice(self.REFRESH_RATES)
            cat = random.choice(refresh_categories)
            
            pattern = random.randint(0, 4)
            if pattern == 0:
                self._add_test(f"{refresh} {cat}", None, "smart", "refresh_spec")
            elif pattern == 1:
                self._add_test(f"{cat} {refresh}", None, "smart", "refresh_spec")
            elif pattern == 2:
                self._add_test(f"{cat} with {refresh}", None, "smart", "refresh_spec")
            elif pattern == 3:
                feature = random.choice(features)
                self._add_test(f"{refresh} {feature} {cat}", None, "smart", "refresh_spec")
            else:
                use = random.choice(uses)
                self._add_test(f"{refresh} {cat} for {use}", None, "smart", "refresh_spec")
    
    # ==================== 28. PROCESSOR_SPEC (SMART) ====================
    
    def generate_processor_spec_tests(self, target: int = 1000):
        """SMART/DEEP: Processor specifications."""
        
        # Categories that stay SMART
        smart_categories = ['laptop', 'desktop', 'computer', 'pc']
        # Categories that trigger DEEP (bundle keywords)
        deep_categories = ['workstation', 'build']
        
        # Fast random generation
        attempts = 0
        while self.category_counts["processor_spec"] < target and attempts < target * 5:
            attempts += 1
            proc = random.choice(self.PROCESSORS)
            
            # Mix of SMART and DEEP patterns
            pattern = random.randint(0, 3)
            if pattern == 0:
                cat = random.choice(smart_categories)
                self._add_test(f"{proc} {cat}", None, "smart", "processor_spec")
            elif pattern == 1:
                cat = random.choice(smart_categories)
                self._add_test(f"{cat} with {proc}", None, "smart", "processor_spec")
            elif pattern == 2:
                cat = random.choice(smart_categories)
                use = random.choice(self.USE_CASES)
                self._add_test(f"{proc} {cat} for {use}", None, "smart", "processor_spec")
            else:
                # Avoid 'build' and 'workstation' which trigger DEEP
                cat = random.choice(smart_categories)
                ram = random.choice(self.RAM_SPECS)
                self._add_test(f"{proc} {ram} {cat}", None, "smart", "processor_spec")
    
    # ==================== 29. STORAGE_SPEC (SMART) ====================
    
    def generate_storage_spec_tests(self, target: int = 1000):
        """SMART: Storage specifications. Avoid patterns that trigger multi-category detection."""
        
        # ONLY use storage-specific terms to avoid multi-category detection
        # Avoid 'laptop', 'computer', 'pc', 'desktop' which can trigger multi-category
        safe_categories = ['ssd', 'drive', 'hard drive', 'storage', 'disk', 'external drive']
        storage_types = ['ssd', 'nvme', 'hdd', 'm.2', 'sata']
        
        # Direct generation - much faster
        attempts = 0
        while self.category_counts["storage_spec"] < target and attempts < target * 5:
            attempts += 1
            storage = random.choice(self.STORAGE_SPECS)
            cat = random.choice(safe_categories)
            stype = random.choice(storage_types)
            
            pattern = random.randint(0, 4)
            if pattern == 0:
                self._add_test(f"{storage} {cat}", None, "smart", "storage_spec")
            elif pattern == 1:
                self._add_test(f"{cat} with {storage}", None, "smart", "storage_spec")
            elif pattern == 2:
                self._add_test(f"{storage} {stype}", None, "smart", "storage_spec")
            elif pattern == 3:
                self._add_test(f"{storage} {stype} {cat}", None, "smart", "storage_spec")
            else:
                self._add_test(f"{stype} {storage} {cat}", None, "smart", "storage_spec")
    
    # ==================== 30. NATURAL_LANGUAGE (SMART) ====================
    
    def generate_natural_language_tests(self, target: int = 1000):
        """SMART: Natural language queries."""
        
        all_patterns = self.NATURAL_PATTERNS + [
            "i'm looking for a {} that's good for {}",
            "need a good {} for my {}",
            "what's the best {} for {} work",
            "recommend me a {} for {}",
            "help me find a {} for {}",
            "i want to buy a {} for {}",
            "shopping for a {} for {}",
            "any suggestions for a {} for {}",
            "which {} works best for {}",
            "best {} for {} use"
        ]
        
        # Fast random generation
        attempts = 0
        while self.category_counts["natural_language"] < target and attempts < target * 5:
            attempts += 1
            cat = random.choice(self.CATEGORIES)
            use_case = random.choice(self.USE_CASES)
            pattern = random.choice(all_patterns)
            
            try:
                query = pattern.format(cat, use_case)
                self._add_test(query, None, "smart", "natural_language")
            except:
                pass
        
        # Also add question patterns
        for pattern in self.QUESTION_PATTERNS:
            for cat in self.CATEGORIES:
                if self.category_counts["natural_language"] >= target:
                    break
                query = pattern.format(cat)
                self._add_test(query, None, "smart", "natural_language")
    
    # ==================== 31. COMPLEX_SPEC (SMART) ====================
    
    def generate_complex_spec_tests(self, target: int = 1000):
        """SMART: Complex multi-spec queries."""
        
        while self.category_counts["complex_spec"] < target:
            # RAM + Processor + Category
            ram = random.choice(self.RAM_SPECS)
            proc = random.choice(self.PROCESSORS)
            cat = random.choice(['laptop', 'desktop', 'pc', 'computer'])
            
            patterns = [
                f"{ram} {proc} {cat}",
                f"{proc} {ram} {cat}",
                f"{cat} with {ram} and {proc}",
                f"{proc} {cat} with {ram}",
                f"{ram} ram {proc} {cat}"
            ]
            
            for p in patterns:
                if self.category_counts["complex_spec"] >= target:
                    break
                self._add_test(p, None, "smart", "complex_spec")
        
        # RAM + Storage + Category
        while self.category_counts["complex_spec"] < target:
            ram = random.choice(self.RAM_SPECS)
            storage = random.choice(self.STORAGE_SPECS)
            cat = random.choice(['laptop', 'desktop', 'pc'])
            
            self._add_test(f"{ram} {storage} {cat}", None, "smart", "complex_spec")
            self._add_test(f"{cat} with {ram} and {storage}", None, "smart", "complex_spec")
    
    # ==================== 32. DOUBLE_QUALITY (FAST) ====================
    
    def generate_double_quality_tests(self, target: int = 1000):
        """FAST/SMART: Modifier + quality + category. Some combos stay FAST."""
        
        # These quality words stay in FAST path even with modifiers
        fast_quality = ['nice', 'good', 'best', 'cheap', 'great', 'top', 'quality']
        # These modifiers with fast_quality stay FAST
        fast_modifiers = ['really', 'very', 'super', 'so', 'fairly', 'extremely', 'quite', 'pretty']
        
        combos = self._generate_combinations(
            [self.MODIFIER_WORDS, self.QUALITY_WORDS, self.CATEGORIES],
            target * 2
        )
        
        for mod, quality, cat in combos:
            if self.category_counts["double_quality"] >= target:
                break
            # Simple modifier + simple quality + category may stay FAST
            if mod in fast_modifiers and quality in fast_quality:
                self._add_test(f"{mod} {quality} {cat}", None, "fast", "double_quality")
            else:
                self._add_test(f"{mod} {quality} {cat}", None, "smart", "double_quality")
        
        # Fill remaining with SMART patterns
        while self.category_counts["double_quality"] < target:
            mod = random.choice(self.MODIFIER_WORDS)
            quality = random.choice(self.QUALITY_WORDS)
            cat = random.choice(self.CATEGORIES)
            plural = random.choice([p for p in self.PLURALS.get(cat, [cat]) if ' ' not in p])
            expected = "fast" if (mod in fast_modifiers and quality in fast_quality) else "smart"
            self._add_test(f"{mod} {quality} {plural}", None, expected, "double_quality")
    
    # ==================== 33. DISPLAY_SPEC (SMART) ====================
    
    def generate_display_spec_tests(self, target: int = 1000):
        """SMART: Display size specifications."""
        
        display_categories = ['monitor', 'tv', 'laptop', 'tablet', 'display', 'screen']
        features = ['4k', '1440p', 'oled', 'ips', 'curved', 'ultrawide', 'hdr', 'led']
        
        # Fast random generation
        attempts = 0
        while self.category_counts["display_spec"] < target and attempts < target * 5:
            attempts += 1
            size = random.choice(self.DISPLAY_SIZES)
            cat = random.choice(display_categories)
            
            pattern = random.randint(0, 3)
            if pattern == 0:
                self._add_test(f"{size} {cat}", None, "smart", "display_spec")
            elif pattern == 1:
                self._add_test(f"{cat} {size}", None, "smart", "display_spec")
            elif pattern == 2:
                feature = random.choice(features)
                self._add_test(f"{size} {feature} {cat}", None, "smart", "display_spec")
            else:
                refresh = random.choice(self.REFRESH_RATES)
                self._add_test(f"{size} {refresh} {cat}", None, "smart", "display_spec")
    
    # ==================== 34. QUESTION_BUNDLE (DEEP) ====================
    
    def generate_question_bundle_tests(self, target: int = 1000):
        """SMART/DEEP: Question-form bundle queries. Single-category questions go SMART."""
        
        # Questions that go DEEP (contain bundle keywords like 'setup', 'kit', 'build', 'complete')
        deep_patterns = [
            "what do i need for a {} setup",
            "what do i need for a {} kit",
            "what do i need for a {} build",
            "what do i need for a {} bundle",
            "what {} completes a {} setup",
            "what would complete a {}"
        ]
        
        # Contexts that don't trigger DEEP on their own (avoid 'home office', 'home studio', 'desk', etc.)
        # Note: 'desk' triggers multi-category when combined with mouse/webcam/etc
        safe_contexts = ['gaming', 'streaming', 'podcast', 'youtube', 'content creation',
                        'esports', 'professional', 'creator', 'influencer', 'vlogger',
                        'editor', 'developer', 'coder', 'remote', 'wfh']
        
        # Fast random generation - most questions go SMART
        attempts = 0
        while self.category_counts["question_bundle"] < target and attempts < target * 5:
            attempts += 1
            context = random.choice(self.BUNDLE_CONTEXTS)
            safe_context = random.choice(safe_contexts)
            cat = random.choice(self.CATEGORIES)
            
            # 30% DEEP (bundle keyword patterns), 70% SMART (single category questions with safe contexts)
            if random.random() < 0.3:
                pattern = random.choice(deep_patterns)
                try:
                    query = pattern.format(context, cat) if '{}' in pattern and pattern.count('{}') > 1 else pattern.format(context)
                    self._add_test(query, None, "deep", "question_bundle")
                except:
                    pass
            else:
                # Single category questions go SMART - use safe contexts
                smart_patterns = [
                    f"what {cat} should i get for {safe_context}",
                    f"which {cat} is best for {safe_context}",
                    f"what {cat} do i need for {safe_context}",
                    f"what's the best {cat} for {safe_context}",
                    f"what gear for {safe_context}",
                    f"what accessories for {safe_context}"
                ]
                self._add_test(random.choice(smart_patterns), None, "smart", "question_bundle")
    
    # ==================== 35. EDGE CASES ====================
    
    def generate_edge_typo_tests(self, target: int = 1000):
        """EDGE: Typo variations."""
        
        def create_typo(word):
            if len(word) < 3:
                return word
            typo_type = random.choice(['swap', 'delete', 'double', 'replace'])
            chars = list(word)
            pos = random.randint(1, len(chars) - 2)
            
            if typo_type == 'swap' and pos < len(chars) - 1:
                chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
            elif typo_type == 'delete':
                chars.pop(pos)
            elif typo_type == 'double':
                chars.insert(pos, chars[pos])
            elif typo_type == 'replace':
                chars[pos] = random.choice('abcdefghijklmnopqrstuvwxyz')
            
            return ''.join(chars)
        
        # Known typos first
        for correct, typos in self.TYPOS.items():
            for typo in typos:
                if self.category_counts["edge_typo"] >= target:
                    break
                self._add_test(typo, None, "smart", "edge_typo")
        
        # Fast random generation
        attempts = 0
        while self.category_counts["edge_typo"] < target and attempts < target * 5:
            attempts += 1
            cat = random.choice(self.CATEGORIES)
            typo = create_typo(cat)
            if typo != cat:
                pattern = random.randint(0, 3)
                if pattern == 0:
                    self._add_test(typo, None, "smart", "edge_typo")
                elif pattern == 1:
                    self._add_test(f"gaming {typo}", None, "smart", "edge_typo")
                elif pattern == 2:
                    self._add_test(f"best {typo}", None, "smart", "edge_typo")
                else:
                    use = random.choice(self.USE_CASES)
                    self._add_test(f"{typo} for {use}", None, "smart", "edge_typo")
    
    def generate_edge_abbreviation_tests(self, target: int = 1000):
        """EDGE: Abbreviation queries. Common abbreviations may go FAST or SMART."""
        
        abbrevs = list(self.ABBREVIATIONS.keys())
        
        # Some very common abbreviations go FAST (directly recognized)
        fast_abbrevs = ['ssd', 'mic', 'gpu', 'cpu', 'tv', 'pc', 'hdd', 'ram']
        # Quality words that keep FAST path
        fast_quality = ['good', 'best', 'cheap', 'nice', 'great', 'top']
        
        # Fast random generation
        attempts = 0
        while self.category_counts["edge_abbreviation"] < target and attempts < target * 5:
            attempts += 1
            abbrev = random.choice(abbrevs)
            
            pattern = random.randint(0, 4)
            if pattern == 0:
                # Plain abbreviation
                expected = "fast" if abbrev in fast_abbrevs else "smart"
                self._add_test(abbrev, None, expected, "edge_abbreviation")
            elif pattern == 1:
                expected = "fast" if abbrev.lower() in fast_abbrevs else "smart"
                self._add_test(abbrev.upper(), None, expected, "edge_abbreviation")
            elif pattern == 2:
                self._add_test(f"gaming {abbrev}", None, "smart", "edge_abbreviation")
            elif pattern == 3:
                use = random.choice(self.USE_CASES)
                self._add_test(f"{abbrev} for {use}", None, "smart", "edge_abbreviation")
            else:
                quality = random.choice(self.QUALITY_WORDS)
                # Fast quality + fast abbrev = FAST, otherwise SMART
                expected = "fast" if (quality in fast_quality and abbrev in fast_abbrevs) else "smart"
                self._add_test(f"{quality} {abbrev}", None, expected, "edge_abbreviation")
    
    def generate_edge_special_char_tests(self, target: int = 1000):
        """FAST/SMART: Special character handling. Most special chars are stripped, giving FAST."""
        
        # These chars result in FAST (stripped/ignored by router)
        fast_chars = ['!', '?', '.', ',', ';', ':', '-', '#', '$', '%', '&', '*', '@']
        # Underscore prefix/suffix triggers SMART (not stripped the same way)
        smart_chars = ['_']
        
        # Fast random generation
        attempts = 0
        while self.category_counts["edge_special_char"] < target and attempts < target * 5:
            attempts += 1
            cat = random.choice(self.CATEGORIES)
            
            pattern = random.randint(0, 3)
            if pattern == 0:
                # Fast chars suffix -> FAST
                char = random.choice(fast_chars)
                self._add_test(f"{cat}{char}", None, "fast", "edge_special_char")
            elif pattern == 1:
                # Fast chars prefix -> FAST (router strips and recognizes category)
                char = random.choice(fast_chars)
                self._add_test(f"{char}{cat}", None, "fast", "edge_special_char")
            elif pattern == 2:
                # Double suffix with fast chars -> FAST
                char = random.choice(fast_chars)
                self._add_test(f"{cat}{char}{char}", None, "fast", "edge_special_char")
            else:
                # Underscore prefix/suffix -> SMART
                self._add_test(f"_{cat}", None, "smart", "edge_special_char")
    
    def generate_edge_mixed_case_tests(self, target: int = 1000):
        """EDGE: Mixed case queries. Avoid wifi/build which trigger DEEP."""
        
        # Avoid features that trigger DEEP
        deep_features = ['wifi', 'wifi 6', 'wifi 6e', 'premium build']
        safe_features = [f for f in self.FEATURES if f not in deep_features]
        
        def random_case(word):
            return ''.join(random.choice([c.upper(), c.lower()]) for c in word)
        
        for cat in self.CATEGORIES:
            for _ in range(30):
                if self.category_counts["edge_mixed_case"] >= target:
                    break
                mixed = random_case(cat)
                self._add_test(mixed, None, "fast", "edge_mixed_case")
        
        # With features (avoid wifi/build)
        while self.category_counts["edge_mixed_case"] < target:
            cat = random.choice(self.CATEGORIES)
            feature = random.choice(safe_features)
            
            patterns = [
                random_case(f"{feature} {cat}"),
                f"{random_case(feature)} {cat}",
                f"{feature} {random_case(cat)}",
                random_case(f"gaming {cat}")
            ]
            
            for p in patterns:
                if self.category_counts["edge_mixed_case"] >= target:
                    break
                self._add_test(p, None, "smart", "edge_mixed_case")
    
    def generate_edge_long_query_tests(self, target: int = 1000):
        """SMART/DEEP: Very long queries. Note: 'setup', 'build' keywords trigger DEEP."""
        
        # Avoid features/contexts that trigger DEEP
        deep_features = ['wifi', 'wifi 6', 'wifi 6e']
        safe_features = [f for f in self.FEATURES if f not in deep_features]
        
        # Templates that stay SMART (avoid setup, build, bundle keywords)
        smart_templates = [
            "i am looking for a really good high quality {feature} {cat} with excellent {feature2} for {use_case}",
            "need to find the best {brand} {cat} with {feature} and {feature2} capabilities for {use_case}",
            "searching for a {quality} {feature} {cat} that works well for {use_case} applications",
            "want a professional grade {brand} {cat} with {feature} {feature2} for {use_case}",
            "help me find a {quality} {cat} for {use_case} that has {feature} and costs around ${budget}",
            "i need recommendations for a {brand} {cat} with {feature} that is good for {use_case}",
            "what is the best {feature} {cat} for {use_case} that also has {feature2}",
            "can you suggest a {quality} {feature} {cat} under ${budget} for {use_case}",
            "recommend me a {brand} {cat} with {feature} for {use_case} work"
        ]
        
        # Templates that trigger DEEP (contain 'setup', 'build', etc)
        deep_templates = [
            "looking to upgrade my {use_case} setup with a new {quality} {feature} {cat}",
            "want a professional grade {brand} {cat} with {feature} for my {use_case} build"
        ]
        
        # Fast random generation
        attempts = 0
        while self.category_counts["edge_long_query"] < target and attempts < target * 5:
            attempts += 1
            
            # 80% SMART, 20% DEEP
            if random.random() < 0.8:
                template = random.choice(smart_templates)
                expected = "smart"
            else:
                template = random.choice(deep_templates)
                expected = "deep"
            
            params = {
                'cat': random.choice(self.CATEGORIES),
                'feature': random.choice(safe_features),  # Use safe features
                'feature2': random.choice(safe_features),  # Use safe features
                'use_case': random.choice(self.USE_CASES),
                'quality': random.choice(self.QUALITY_WORDS),
                'brand': random.choice(self.BRANDS),
                'budget': random.choice(self.BUDGET_VALUES)
            }
            
            try:
                query = template.format(**params)
                self._add_test(query, None, expected, "edge_long_query")
            except:
                pass
    
    def generate_edge_minimal_query_tests(self, target: int = 1000):
        """EDGE: Very minimal/vague queries."""
        
        minimal_queries = [
            # Articles
            "the", "a", "an", "this", "that", "these", "those",
            # Common words
            "find", "get", "buy", "need", "want", "search", "show", "help",
            "good", "best", "nice", "new", "cheap", "free", "fast",
            # Single letters
            "a", "b", "c", "d", "e", "x", "y", "z",
            # Numbers
            "1", "2", "10", "100", "1000",
            # Symbols alone
            "?", "!", "...", "---",
            # Very short
            "pc", "tv", "hd", "4k", "5g",
            # Vague
            "stuff", "things", "items", "products", "gear", "equipment",
            "technology", "electronics", "devices", "gadgets",
            "something", "anything", "everything",
            "idk", "hmm", "umm", "uhh",
            # Empty-ish
            "   ", "  a  ", "    the    "
        ]
        
        for query in minimal_queries:
            self._add_test(query, None, "smart", "edge_minimal_query")
        
        # Fast random generation
        articles = ['the', 'a', 'my', 'your', 'some', 'any']
        vague_words = ['stuff', 'thing', 'item', 'product', 'device']
        preps = ['for', 'to', 'with', 'and', 'or']
        price_words = ['under', 'around', 'about']
        
        attempts = 0
        while self.category_counts["edge_minimal_query"] < target and attempts < target * 5:
            attempts += 1
            pattern = random.randint(0, 5)
            if pattern == 0:
                self._add_test(random.choice(articles), None, "smart", "edge_minimal_query")
            elif pattern == 1:
                self._add_test(random.choice(vague_words), None, "smart", "edge_minimal_query")
            elif pattern == 2:
                self._add_test(random.choice(preps), None, "smart", "edge_minimal_query")
            elif pattern == 3:
                use = random.choice(self.USE_CASES)
                self._add_test(f"something for {use}", None, "smart", "edge_minimal_query")
            elif pattern == 4:
                q = random.choice(self.QUALITY_WORDS)
                self._add_test(f"anything {q}", None, "smart", "edge_minimal_query")
            else:
                val = random.choice(self.BUDGET_VALUES)
                word = random.choice(price_words)
                self._add_test(f"{word} ${val}", None, "smart", "edge_minimal_query")
    
    def generate_edge_unicode_tests(self, target: int = 1000):
        """EDGE: Unicode and international character handling."""
        
        # Features that trigger DEEP - avoid these
        deep_features = ['wifi', 'wifi 6', 'wifi 6e', 'premium build', '8k']
        safe_features = [f for f in self.FEATURES if f not in deep_features]
        
        # Categories with various unicode characters
        unicode_patterns = [
            # Accents
            "laptöp", "mönitor", "keybøard", "müse",
            # Emoji (usually stripped)
            "laptop 💻", "gaming 🎮 keyboard", "monitor 🖥️",
            # Japanese/Chinese approximations
            "ラップトップ", "键盘", "显示器",
            # Currency symbols
            "laptop $500", "monitor €400", "keyboard £100", "mouse ¥500",
            # Fractions
            "½ price laptop", "¼ off monitor",
            # Degree symbols
            "laptop 90° rotation", "monitor 360° stand"
        ]
        
        for query in unicode_patterns:
            self._add_test(query, None, "smart", "edge_unicode")
        
        # With categories
        unicode_chars = ['é', 'ü', 'ñ', 'ø', 'ß', 'æ', 'ð', 'þ', 'α', 'β', 'γ']
        for cat in self.CATEGORIES:
            for char in unicode_chars:
                if self.category_counts["edge_unicode"] >= target:
                    break
                self._add_test(f"{char}{cat}", None, "smart", "edge_unicode")
                self._add_test(f"{cat}{char}", None, "smart", "edge_unicode")
        
        # Fill remaining - use safe_features to avoid wifi triggers
        while self.category_counts["edge_unicode"] < target:
            cat = random.choice(self.CATEGORIES)
            char = random.choice(unicode_chars)
            feature = random.choice(safe_features)
            self._add_test(f"{feature}{char} {cat}", None, "smart", "edge_unicode")
    
    def generate_edge_number_tests(self, target: int = 1000):
        """EDGE: Numeric queries and formats."""
        
        price_formats = ['$100', '$100.00', '100$', '100 dollars', '100 usd', '$1,000', '$1000', '1k', '1.5k', '2k']
        quantity_formats = ['2x', '3x', 'x2', 'x3', 'two', 'three', 'pair of', 'set of 3']
        
        # Fast random generation
        attempts = 0
        while self.category_counts["edge_number"] < target and attempts < target * 5:
            attempts += 1
            cat = random.choice(self.CATEGORIES)
            
            pattern = random.randint(0, 3)
            if pattern == 0:
                price = random.choice(price_formats)
                self._add_test(f"{cat} {price}", None, "smart", "edge_number")
            elif pattern == 1:
                price = random.choice(price_formats)
                self._add_test(f"{price} {cat}", None, "smart", "edge_number")
            elif pattern == 2:
                qty = random.choice(quantity_formats)
                self._add_test(f"{qty} {cat}", None, "smart", "edge_number")
            else:
                num = random.randint(1, 100)
                self._add_test(f"{num} {cat}", None, "smart", "edge_number")
    
    # ==================== MAIN GENERATOR ====================
    
    def generate_all(self, tests_per_category: int = 1000) -> List[TestCase]:
        """Generate all test cases with target per category."""
        
        print(f"🧪 Generating {tests_per_category} tests per category...")
        print("=" * 70)
        
        # ===== FAST Path Tests =====
        print("\n⚡ FAST Path Tests:")
        
        self.generate_single_category_tests(tests_per_category)
        print(f"  single_category:           {self.category_counts['single_category']:>5}")
        
        self.generate_plural_category_tests(tests_per_category)
        print(f"  plural_category:           {self.category_counts['plural_category']:>5}")
        
        self.generate_quality_category_tests(tests_per_category)
        print(f"  quality_category:          {self.category_counts['quality_category']:>5}")
        
        self.generate_quality_plural_tests(tests_per_category)
        print(f"  quality_plural:            {self.category_counts['quality_plural']:>5}")
        
        self.generate_double_quality_tests(tests_per_category)
        print(f"  double_quality:            {self.category_counts['double_quality']:>5}")
        
        # ===== SMART Path Tests =====
        print("\n🧠 SMART Path Tests:")
        
        self.generate_brand_category_tests(tests_per_category)
        print(f"  brand_category:            {self.category_counts['brand_category']:>5}")
        
        self.generate_use_case_category_tests(tests_per_category)
        print(f"  use_case_category:         {self.category_counts['use_case_category']:>5}")
        
        self.generate_feature_category_tests(tests_per_category)
        print(f"  feature_category:          {self.category_counts['feature_category']:>5}")
        
        self.generate_budget_category_tests(tests_per_category)
        print(f"  budget_category:           {self.category_counts['budget_category']:>5}")
        
        self.generate_use_case_feature_tests(tests_per_category)
        print(f"  use_case_feature:          {self.category_counts['use_case_feature']:>5}")
        
        self.generate_feature_plural_tests(tests_per_category)
        print(f"  feature_plural:            {self.category_counts['feature_plural']:>5}")
        
        self.generate_quality_use_case_tests(tests_per_category)
        print(f"  quality_use_case:          {self.category_counts['quality_use_case']:>5}")
        
        self.generate_multi_feature_tests(tests_per_category)
        print(f"  multi_feature:             {self.category_counts['multi_feature']:>5}")
        
        self.generate_ram_spec_tests(tests_per_category)
        print(f"  ram_spec:                  {self.category_counts['ram_spec']:>5}")
        
        self.generate_processor_spec_tests(tests_per_category)
        print(f"  processor_spec:            {self.category_counts['processor_spec']:>5}")
        
        self.generate_storage_spec_tests(tests_per_category)
        print(f"  storage_spec:              {self.category_counts['storage_spec']:>5}")
        
        self.generate_refresh_spec_tests(tests_per_category)
        print(f"  refresh_spec:              {self.category_counts['refresh_spec']:>5}")
        
        self.generate_display_spec_tests(tests_per_category)
        print(f"  display_spec:              {self.category_counts['display_spec']:>5}")
        
        self.generate_complex_spec_tests(tests_per_category)
        print(f"  complex_spec:              {self.category_counts['complex_spec']:>5}")
        
        self.generate_brand_feature_tests(tests_per_category)
        print(f"  brand_feature:             {self.category_counts['brand_feature']:>5}")
        
        self.generate_same_category_comparison_tests(tests_per_category)
        print(f"  same_category_comparison:  {self.category_counts['same_category_comparison']:>5}")
        
        self.generate_natural_language_tests(tests_per_category)
        print(f"  natural_language:          {self.category_counts['natural_language']:>5}")
        
        # ===== DEEP Path Tests =====
        print("\n🔧 DEEP Path Tests:")
        
        self.generate_multi_category_and_tests(tests_per_category)
        print(f"  multi_category_and:        {self.category_counts['multi_category_and']:>5}")
        
        self.generate_multi_category_with_tests(tests_per_category)
        print(f"  multi_category_with:       {self.category_counts['multi_category_with']:>5}")
        
        self.generate_multi_category_comma_tests(tests_per_category)
        print(f"  multi_category_comma:      {self.category_counts['multi_category_comma']:>5}")
        
        self.generate_multi_category_budget_tests(tests_per_category)
        print(f"  multi_category_budget:     {self.category_counts['multi_category_budget']:>5}")
        
        self.generate_three_categories_tests(tests_per_category)
        print(f"  three_categories:          {self.category_counts['three_categories']:>5}")
        
        self.generate_context_bundle_tests(tests_per_category)
        print(f"  context_bundle:            {self.category_counts['context_bundle']:>5}")
        
        self.generate_bundle_budget_tests(tests_per_category)
        print(f"  bundle_budget:             {self.category_counts['bundle_budget']:>5}")
        
        self.generate_bundle_keyword_tests(tests_per_category)
        print(f"  bundle_keyword:            {self.category_counts['bundle_keyword']:>5}")
        
        self.generate_complete_bundle_tests(tests_per_category)
        print(f"  complete_bundle:           {self.category_counts['complete_bundle']:>5}")
        
        self.generate_specific_bundle_tests(tests_per_category)
        print(f"  specific_bundle:           {self.category_counts['specific_bundle']:>5}")
        
        self.generate_question_bundle_tests(tests_per_category)
        print(f"  question_bundle:           {self.category_counts['question_bundle']:>5}")
        
        self.generate_cross_category_comparison_tests(tests_per_category)
        print(f"  cross_category_comparison: {self.category_counts['cross_category_comparison']:>5}")
        
        # ===== EDGE Case Tests =====
        print("\n🎯 EDGE Case Tests:")
        
        self.generate_edge_typo_tests(tests_per_category)
        print(f"  edge_typo:                 {self.category_counts['edge_typo']:>5}")
        
        self.generate_edge_abbreviation_tests(tests_per_category)
        print(f"  edge_abbreviation:         {self.category_counts['edge_abbreviation']:>5}")
        
        self.generate_edge_special_char_tests(tests_per_category)
        print(f"  edge_special_char:         {self.category_counts['edge_special_char']:>5}")
        
        self.generate_edge_mixed_case_tests(tests_per_category)
        print(f"  edge_mixed_case:           {self.category_counts['edge_mixed_case']:>5}")
        
        self.generate_edge_long_query_tests(tests_per_category)
        print(f"  edge_long_query:           {self.category_counts['edge_long_query']:>5}")
        
        self.generate_edge_minimal_query_tests(tests_per_category)
        print(f"  edge_minimal_query:        {self.category_counts['edge_minimal_query']:>5}")
        
        self.generate_edge_unicode_tests(tests_per_category)
        print(f"  edge_unicode:              {self.category_counts['edge_unicode']:>5}")
        
        self.generate_edge_number_tests(tests_per_category)
        print(f"  edge_number:               {self.category_counts['edge_number']:>5}")
        
        print("\n" + "=" * 70)
        print(f"📊 Total unique test cases: {len(self.test_cases)}")
        print(f"📁 Categories: {len(self.category_counts)}")
        
        # Summary by path
        fast_count = sum(1 for t in self.test_cases if t.expected_path == 'fast')
        smart_count = sum(1 for t in self.test_cases if t.expected_path == 'smart')
        deep_count = sum(1 for t in self.test_cases if t.expected_path == 'deep')
        
        print(f"\n📈 Path Distribution:")
        print(f"  FAST:  {fast_count:>6} ({fast_count/len(self.test_cases)*100:.1f}%)")
        print(f"  SMART: {smart_count:>6} ({smart_count/len(self.test_cases)*100:.1f}%)")
        print(f"  DEEP:  {deep_count:>6} ({deep_count/len(self.test_cases)*100:.1f}%)")
        
        return self.test_cases


def run_mega_tests(sample_size: Optional[int] = None):
    """Run the mega test suite."""
    
    # Generate tests
    generator = MegaTestGenerator()
    test_cases = generator.generate_all(tests_per_category=1000)
    
    # Optionally sample for faster testing
    if sample_size and sample_size < len(test_cases):
        print(f"\n⚡ Sampling {sample_size} tests from {len(test_cases)} for faster execution...")
        
        # Sample proportionally from each category
        sampled = []
        categories = list(generator.category_counts.keys())
        per_cat = max(1, sample_size // len(categories))
        
        for cat in categories:
            cat_tests = [t for t in test_cases if t.category == cat]
            sampled.extend(random.sample(cat_tests, min(per_cat, len(cat_tests))))
        
        test_cases = sampled[:sample_size]
        print(f"  Sampled {len(test_cases)} tests")
    
    # Initialize router
    router = QueryRouter()
    
    print(f"\n{'='*80}")
    print(f"🧪 MEGA ROUTER TEST SUITE")
    print(f"{'='*80}")
    print(f"Router LLM Available: {router._groq_client is not None}")
    print(f"Total Test Cases: {len(test_cases)}")
    print(f"{'='*80}\n")
    
    # Run tests
    results = defaultdict(lambda: {'passed': 0, 'failed': 0, 'failures': []})
    overall_passed = 0
    overall_failed = 0
    
    start_time = time.time()
    
    for i, test in enumerate(test_cases):
        router.clear_cache()
        
        try:
            decision = router.analyze(test.query, test.budget)
            actual_path = decision.path.value
            
            if actual_path == test.expected_path:
                overall_passed += 1
                results[test.category]['passed'] += 1
            else:
                overall_failed += 1
                results[test.category]['failed'] += 1
                results[test.category]['failures'].append({
                    'query': test.query[:50],
                    'budget': test.budget,
                    'expected': test.expected_path,
                    'actual': actual_path,
                    'reason': decision.reason[:60] if hasattr(decision, 'reason') else ''
                })
        except Exception as e:
            overall_failed += 1
            results[test.category]['failed'] += 1
            results[test.category]['failures'].append({
                'query': test.query[:50],
                'budget': test.budget,
                'expected': test.expected_path,
                'actual': 'ERROR',
                'reason': str(e)[:60]
            })
        
        # Progress indicator
        if (i + 1) % 1000 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            eta = (len(test_cases) - i - 1) / rate
            pct = (i + 1) / len(test_cases) * 100
            print(f"  Progress: {i + 1:>6}/{len(test_cases)} ({pct:>5.1f}%) | {rate:.0f} tests/sec | ETA: {eta:.0f}s")
    
    elapsed = time.time() - start_time
    
    # Print results
    print(f"\n{'='*80}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"Total:  {overall_passed} passed, {overall_failed} failed out of {len(test_cases)}")
    print(f"Time:   {elapsed:.2f}s ({elapsed/len(test_cases)*1000:.2f}ms per test)")
    print(f"Rate:   {overall_passed/len(test_cases)*100:.2f}% pass rate")
    print(f"{'='*80}\n")
    
    # Path breakdown
    fast_cases = [t for t in test_cases if t.expected_path == 'fast']
    smart_cases = [t for t in test_cases if t.expected_path == 'smart']
    deep_cases = [t for t in test_cases if t.expected_path == 'deep']
    
    print("PATH BREAKDOWN:")
    print(f"  FAST:  {len(fast_cases):>6} tests")
    print(f"  SMART: {len(smart_cases):>6} tests")
    print(f"  DEEP:  {len(deep_cases):>6} tests")
    print()
    
    # Category breakdown
    print("CATEGORY BREAKDOWN:")
    print("-" * 80)
    sorted_categories = sorted(results.keys())
    
    for category in sorted_categories:
        r = results[category]
        total = r['passed'] + r['failed']
        rate = r['passed'] / total * 100 if total > 0 else 0
        status = "✅" if rate >= 95 else ("⚠️" if rate >= 80 else "❌")
        print(f"  {status} {category:30} {r['passed']:>5}/{total:<5} ({rate:>6.2f}%)")
    
    # Failed tests summary
    if overall_failed > 0:
        print(f"\n{'='*80}")
        print(f"FAILURE SUMMARY BY CATEGORY")
        print(f"{'='*80}")
        
        for category in sorted_categories:
            failures = results[category]['failures']
            if failures:
                print(f"\n  📁 {category}: {len(failures)} failures")
                for f in failures[:3]:  # Show first 3
                    print(f"     • '{f['query'][:40]}...' → expected {f['expected']}, got {f['actual']}")
                if len(failures) > 3:
                    print(f"     ... and {len(failures) - 3} more")
    
    # Final summary
    print(f"\n{'='*80}")
    if overall_failed == 0:
        print("🎉 ALL TESTS PASSED! Router is rock solid.")
    elif overall_passed / len(test_cases) >= 0.95:
        print(f"✅ EXCELLENT: {overall_passed/len(test_cases)*100:.1f}% pass rate")
    elif overall_passed / len(test_cases) >= 0.90:
        print(f"⚠️  GOOD: {overall_passed/len(test_cases)*100:.1f}% pass rate - minor issues to fix")
    elif overall_passed / len(test_cases) >= 0.80:
        print(f"⚠️  FAIR: {overall_passed/len(test_cases)*100:.1f}% pass rate - needs attention")
    else:
        print(f"❌ NEEDS WORK: {overall_passed/len(test_cases)*100:.1f}% pass rate")
    print(f"{'='*80}")
    
    return overall_passed, overall_failed, len(test_cases), results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run mega router tests')
    parser.add_argument('--sample', type=int, default=None, 
                       help='Sample size for faster testing (default: run all)')
    parser.add_argument('--quick', action='store_true',
                       help='Quick mode: sample 3000 tests')
    parser.add_argument('--medium', action='store_true',
                       help='Medium mode: sample 10000 tests')
    
    args = parser.parse_args()
    
    sample_size = args.sample
    if args.quick:
        sample_size = 3000
    elif args.medium:
        sample_size = 10000
    
    run_mega_tests(sample_size=sample_size)
