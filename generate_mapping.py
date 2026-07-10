#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ابزار تولید فایل image_mapping.json از محصولات موجود
"""

import json
import os
from typing import Dict, List

def generate_mapping_from_products(products: List[Dict]) -> Dict:
    """تولید mapping تصاویر از لیست محصولات"""
    mapping = {}
    
    for product in products:
        product_id = product.get('id', '')
        if not product_id:
            continue
            
        # بررسی تصاویر موجود
        images = product.get('images', [])
        if not images and product.get('image'):
            images = [product.get('image')]
        
        if images:
            mapping[product_id] = {
                'name': product.get('name', ''),
                'brand': product.get('brand', ''),
                'images': images,
                'source_url': product.get('source_url', ''),
                'source': product.get('source', '')
            }
    
    return mapping

def load_products() -> List[Dict]:
    """بارگذاری محصولات از فایل"""
    try:
        with open('products_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def main():
    products = load_products()
    if not products:
        print("⚠️ فایل products_data.json یافت نشد.")
        return
    
    mapping = generate_mapping_from_products(products)
    
    with open('image_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"✅ فایل image_mapping.json با {len(mapping)} محصول تولید شد.")

if __name__ == '__main__':
    main()
