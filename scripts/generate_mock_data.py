"""
Generate Mock Product Database for FinBundle
Creates 1000 realistic products across 10 categories
"""
import json
import random
from pathlib import Path

CATEGORIES = ['laptops', 'monitors', 'keyboards', 'mice', 'headsets', 'webcams', 'speakers', 'desks', 'chairs', 'gpus']

BRANDS = {
    'laptops': ['Dell', 'HP', 'ASUS', 'Lenovo', 'Acer', 'MSI', 'Apple', 'Razer'],
    'monitors': ['Samsung', 'LG', 'Dell', 'ASUS', 'BenQ', 'Acer', 'ViewSonic', 'AOC'],
    'keyboards': ['Logitech', 'Corsair', 'Razer', 'SteelSeries', 'HyperX', 'Ducky', 'Keychron', 'Das Keyboard'],
    'mice': ['Logitech', 'Razer', 'Corsair', 'SteelSeries', 'Zowie', 'Glorious', 'Pulsar', 'Finalmouse'],
    'headsets': ['SteelSeries', 'HyperX', 'Razer', 'Logitech', 'Corsair', 'Sennheiser', 'Audio-Technica', 'Beyerdynamic'],
    'webcams': ['Logitech', 'Razer', 'Elgato', 'AVerMedia', 'Microsoft', 'Obsbot', 'Anker', 'Dell'],
    'speakers': ['Logitech', 'Creative', 'Audioengine', 'Klipsch', 'Edifier', 'PreSonus', 'JBL', 'Bose'],
    'desks': ['FlexiSpot', 'Uplift', 'Secretlab', 'IKEA', 'Autonomous', 'Vari', 'Branch', 'Fully'],
    'chairs': ['Secretlab', 'Herman Miller', 'Steelcase', 'Autonomous', 'IKEA', 'Razer', 'Noblechairs', 'AndaSeat'],
    'gpus': ['NVIDIA', 'ASUS', 'MSI', 'Gigabyte', 'EVGA', 'Zotac', 'Sapphire', 'PowerColor']
}

PRICE_RANGES = {
    'laptops': (400, 2500),
    'monitors': (150, 1200),
    'keyboards': (30, 250),
    'mice': (15, 180),
    'gpus': (200, 1800),
    'headsets': (30, 400),
    'webcams': (40, 350),
    'speakers': (50, 500),
    'desks': (100, 900),
    'chairs': (150, 1500)
}

MODEL_PREFIXES = {
    'laptops': ['ProBook', 'XPS', 'ThinkPad', 'ZenBook', 'Predator', 'ROG', 'MacBook', 'Blade'],
    'monitors': ['UltraSharp', 'Odyssey', 'TUF', 'ProArt', 'XG', 'Nitro', 'VP', 'CU'],
    'keyboards': ['K', 'Pro', 'Huntsman', 'Apex', 'Alloy', 'One', 'Q', 'Model'],
    'mice': ['G', 'DeathAdder', 'Dark Core', 'Rival', 'EC', 'Model O', 'X2', 'UL'],
    'headsets': ['Arctis', 'Cloud', 'BlackShark', 'G Pro', 'HS', 'HD', 'M', 'DT'],
    'webcams': ['C', 'Kiyo', 'Facecam', 'PW', 'LifeCam', 'Tiny', 'PowerConf', 'UltraSharp'],
    'speakers': ['G', 'Pebble', 'A', 'R', 'R1280', 'Eris', 'Flip', 'Companion'],
    'desks': ['E', 'V', 'Magnus', 'BEKANT', 'SmartDesk', 'Electric', 'Jarvis', 'Desk'],
    'chairs': ['Titan', 'Aeron', 'Leap', 'ErgoChair', 'MARKUS', 'Iskur', 'Hero', 'Kaiser'],
    'gpus': ['RTX', 'STRIX', 'GAMING X', 'AORUS', 'FTW3', 'Trinity', 'NITRO+', 'Red Devil']
}

FEATURES = {
    'laptops': ['16GB RAM', '32GB RAM', '512GB SSD', '1TB SSD', 'RTX 4060', 'RTX 4070', 'i7-13700H', 'Ryzen 7 7735HS', '4K Display', '144Hz'],
    'monitors': ['4K', '1440p', '144Hz', '240Hz', 'IPS', 'OLED', 'Curved', 'HDR', '27"', '32"', '34" Ultrawide'],
    'keyboards': ['Mechanical', 'Hot-swappable', 'RGB', 'Wireless', 'TKL', '65%', 'Cherry MX', 'Gateron', 'Low Profile'],
    'mice': ['Wireless', 'Lightweight', '25600 DPI', 'Optical', 'Ergonomic', 'Ambidextrous', 'RGB', 'Polling 8000Hz'],
    'headsets': ['7.1 Surround', 'Wireless', 'Noise-cancelling', 'Open-back', 'Closed-back', 'RGB', 'Detachable Mic'],
    'webcams': ['4K', '1080p 60fps', 'Auto-focus', 'Ring Light', 'Privacy Shutter', 'Built-in Mic', 'Wide Angle'],
    'speakers': ['2.1 System', 'Bluetooth', 'Studio Quality', 'RGB', 'Subwoofer', 'USB-C', 'Active'],
    'desks': ['Standing', 'Electric', 'Programmable Height', 'Cable Management', 'Drawer', 'L-Shaped', 'Bamboo Top'],
    'chairs': ['Ergonomic', 'Lumbar Support', 'Memory Foam', '4D Armrests', 'Mesh', 'Leather', 'Reclining', 'Footrest'],
    'gpus': ['12GB VRAM', '16GB VRAM', '24GB VRAM', 'Ray Tracing', 'DLSS 3', 'Overclocked', 'Liquid Cooled', 'Mini ITX']
}


def generate_product_name(category: str, brand: str, idx: int) -> str:
    """Generate a realistic product name."""
    prefix = random.choice(MODEL_PREFIXES[category])
    model_number = random.randint(100, 9999)
    features = random.sample(FEATURES[category], k=min(2, len(FEATURES[category])))
    feature_str = ' '.join(features[:1])  # Just one feature in name
    return f"{brand} {prefix} {model_number} {feature_str}".strip()


def generate_description(product_name: str, category: str, brand: str, features: list) -> str:
    """Generate a realistic product description."""
    feature_text = ', '.join(features) if features else 'premium quality'
    templates = [
        f"High-performance {category.rstrip('s')} from {brand} featuring {feature_text}. Perfect for professionals and enthusiasts alike.",
        f"The {product_name} delivers exceptional {category.rstrip('s')} experience with {feature_text}. Built for demanding users.",
        f"Experience premium quality with this {brand} {category.rstrip('s')}. Features include {feature_text}.",
        f"Designed for excellence, this {category.rstrip('s')} offers {feature_text}. A top choice from {brand}."
    ]
    return random.choice(templates)


def generate_products(n: int = 1000) -> list:
    """Generate n mock products with realistic attributes."""
    products = []
    
    for i in range(n):
        category = random.choice(CATEGORIES)
        brand = random.choice(BRANDS[category])
        
        # Generate price with some price clustering (realistic market behavior)
        min_p, max_p = PRICE_RANGES[category]
        
        # Create price tiers: budget (30%), mid (50%), premium (20%)
        tier = random.random()
        if tier < 0.3:
            price = round(random.uniform(min_p, min_p + (max_p - min_p) * 0.3), 2)
        elif tier < 0.8:
            price = round(random.uniform(min_p + (max_p - min_p) * 0.3, min_p + (max_p - min_p) * 0.7), 2)
        else:
            price = round(random.uniform(min_p + (max_p - min_p) * 0.7, max_p), 2)
        
        # Generate other attributes
        product_name = generate_product_name(category, brand, i)
        features = random.sample(FEATURES[category], k=random.randint(2, 4))
        
        product = {
            "id": f"prod_{i:04d}",
            "name": product_name,
            "category": category,
            "brand": brand,
            "price": price,
            "rating": round(random.uniform(3.2, 5.0), 1),
            "review_count": random.randint(5, 2500),
            "description": generate_description(product_name, category, brand, features),
            "features": features,
            "image_url": f"https://via.placeholder.com/300x300?text={category.replace(' ', '+')}",
            "in_stock": random.choices([True, False], weights=[0.85, 0.15])[0],
            "condition": random.choices(['new', 'refurbished', 'open-box'], weights=[0.80, 0.12, 0.08])[0],
            "warranty_months": random.choice([12, 24, 36]),
            "shipping_days": random.randint(1, 7),
            "seller_rating": round(random.uniform(4.0, 5.0), 1)
        }
        products.append(product)
    
    return products


def main():
    """Generate products and save to JSON file."""
    # Ensure data directory exists
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(exist_ok=True)
    
    print("🔄 Generating 1000 mock products...")
    products = generate_products(1000)
    
    # Save to JSON
    output_path = data_dir / 'products.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    
    # Print summary statistics
    categories_count = {}
    for p in products:
        categories_count[p['category']] = categories_count.get(p['category'], 0) + 1
    
    print(f"✅ Generated {len(products)} products")
    print("\n📊 Category Distribution:")
    for cat, count in sorted(categories_count.items()):
        print(f"   {cat}: {count}")
    
    print(f"\n📁 Saved to: {output_path}")


if __name__ == "__main__":
    main()
