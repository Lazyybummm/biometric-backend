#!/usr/bin/env python3
"""
Barcode Product Lookup for Indian Products
Checks multiple barcodes and fetches product details from Open Food Facts
"""

import requests
import time
import json
from typing import Dict, List, Optional

def lookup_product(barcode: str, verbose: bool = True) -> Optional[Dict]:
    """
    Look up product information for a given barcode
    
    Args:
        barcode: The 13-digit barcode number
        verbose: Print detailed output if True
    
    Returns:
        Dictionary with product info or None if not found
    """
    headers = {"User-Agent": "IndianShopkeeperSystem/1.0 (contact@shopapp.com)"}
    
    # Get basic product info from Open Food Facts
    product_url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    
    try:
        product_resp = requests.get(product_url, headers=headers, timeout=10)
        
        if product_resp.status_code == 200:
            data = product_resp.json()
            
            if data.get("status") == 1:
                product = data["product"]
                
                # Extract relevant information
                product_info = {
                    "barcode": barcode,
                    "name": product.get('product_name', 'N/A'),
                    "brand": product.get('brands', 'N/A'),
                    "quantity": product.get('quantity', 'N/A'),
                    "categories": product.get('categories', 'N/A')[:100],
                    "image_url": product.get('image_url', ''),
                    "ingredients": product.get('ingredients_text', '')[:200] if product.get('ingredients_text') else 'N/A',
                    "country": product.get('countries', 'N/A')
                }
                
                if verbose:
                    print(f"\n{'='*60}")
                    print(f"📦 BARCODE: {barcode}")
                    print(f"{'='*60}")
                    print(f"📝 Name: {product_info['name']}")
                    print(f"🏷️  Brand: {product_info['brand']}")
                    print(f"📏 Quantity: {product_info['quantity']}")
                    print(f"📂 Categories: {product_info['categories']}")
                    if product_info['country'] != 'N/A':
                        print(f"🌍 Country: {product_info['country']}")
                
                return product_info
            else:
                if verbose:
                    print(f"\n❌ BARCODE: {barcode} - Product not found in database")
                return None
        else:
            if verbose:
                print(f"\n⚠️  BARCODE: {barcode} - API error (Status: {product_resp.status_code})")
            return None
            
    except requests.exceptions.RequestException as e:
        if verbose:
            print(f"\n⚠️  BARCODE: {barcode} - Connection error: {e}")
        return None


def lookup_multiple_products(barcodes: List[str], delay: float = 0.5) -> Dict[str, Optional[Dict]]:
    """
    Look up multiple barcodes with a delay between requests to be respectful to the API
    
    Args:
        barcodes: List of barcode strings
        delay: Seconds to wait between requests (default 0.5)
    
    Returns:
        Dictionary mapping barcode to product info or None
    """
    results = {}
    
    print(f"\n{'🚀'*30}")
    print(f"Starting lookup for {len(barcodes)} barcodes...")
    print(f"{'🚀'*30}")
    
    for i, barcode in enumerate(barcodes, 1):
        print(f"\n[{i}/{len(barcodes)}] Processing...")
        results[barcode] = lookup_product(barcode, verbose=True)
        
        # Add delay to avoid rate limiting (except for last item)
        if i < len(barcodes):
            time.sleep(delay)
    
    # Print summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")
    
    found_count = sum(1 for info in results.values() if info is not None)
    print(f"✅ Found: {found_count}/{len(barcodes)} products")
    print(f"❌ Not found: {len(barcodes) - found_count}/{len(barcodes)} products")
    
    return results


def save_results_to_file(results: Dict[str, Optional[Dict]], filename: str = "product_results.json"):
    """Save lookup results to a JSON file"""
    
    # Convert None values to a placeholder for JSON
    serializable_results = {}
    for barcode, info in results.items():
        if info:
            serializable_results[barcode] = info
        else:
            serializable_results[barcode] = {"error": "Product not found"}
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(serializable_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to {filename}")


# ============================================
# INDIAN PRODUCT BARCODES TO TEST
# ============================================

# Common Indian product barcodes (13-digit)
INDIAN_BARCODES = [
    "8901764041259",  # Maggi Masala Noodles
    "8901262150064",  # Amul Butter
    "037000061946",  # Parle G Biscuits
    "8908000513101",  # Tata Tea Gold
    "8901125051125",  # Dabur Honey
    "8901497036142",  # Colgate Toothpaste
    "8901030102408",  # Amul Milk
    "8906036003614",  # Britannia Bourbon
    "8901396000198",  # Nescafe Classic
    "8904005003520",  # Patanjali Ghee
    "8901717117073",  # Haldiram's Namkeen
    "8901699100010",  # Cadbury Dairy Milk
    "8901225000109",  # Kissan Mixed Fruit Jam
    "8906014100038",  # Pepsodent Toothpaste
    "8904063800042",  # Surf Excel Detergent
]

# Smaller test set if you want faster testing
SAMPLE_BARCODES = [
    "8901058851311",  # Maggi
    "8901030515147",  # Amul Butter
    "8901725001203",  # Parle G
]


# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🏪 INDIAN PRODUCT BARCODE LOOKUP SYSTEM")
    print("="*60)
    print("\n📌 Using Open Food Facts API (Free)")
    print("📌 Rate limit: ~1 request per second recommended")
    
    # Choose which set to test
    print("\n🔍 Choose test option:")
    print("  1. Test 5 sample products")
    print("  2. Test all Indian products (15 barcodes)")
    print("  3. Enter custom barcodes")
    
    choice = input("\n👉 Enter choice (1/2/3): ").strip()
    
    if choice == "1":
        barcodes_to_test = SAMPLE_BARCODES
    elif choice == "2":
        barcodes_to_test = INDIAN_BARCODES
    elif choice == "3":
        custom_input = input("Enter comma-separated barcodes: ")
        barcodes_to_test = [b.strip() for b in custom_input.split(",") if b.strip()]
    else:
        print("Invalid choice. Using sample barcodes.")
        barcodes_to_test = SAMPLE_BARCODES
    
    if not barcodes_to_test:
        print("No barcodes provided. Exiting.")
        exit()
    
    # Run the lookup
    results = lookup_multiple_products(barcodes_to_test, delay=0.5)
    
    # Ask if user wants to save results
    save_choice = input("\n💾 Save results to JSON file? (y/n): ").strip().lower()
    if save_choice == 'y':
        save_results_to_file(results)
    
    # Show summary of found products
    print(f"\n{'='*60}")
    print("📋 FOUND PRODUCTS LIST")
    print(f"{'='*60}")
    
    found_products = [(barcode, info) for barcode, info in results.items() if info is not None]
    
    if found_products:
        for i, (barcode, info) in enumerate(found_products, 1):
            print(f"\n{i}. {info['name']}")
            print(f"   📍 Barcode: {barcode}")
            print(f"   🏷️  Brand: {info['brand']}")
            print(f"   📏 Pack: {info['quantity']}")
    else:
        print("\n❌ No products found in database")
    
    print("\n✅ Done!")