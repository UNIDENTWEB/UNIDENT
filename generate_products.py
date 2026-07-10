import json
import random
import os

def generate_products(count=300):
    output_file = 'products.json'
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        if existing:
            print(f'{len(existing)} products already exist in {output_file}. Skipping generation.')
            return

    brands = ['NSK', 'COXO', 'W&H']
    categories = ['ایمپلنت', 'توربین', 'آنگل', 'ایرموتور', 'ست هندپیس', 'اندو', 'ارتودنسی']
    products = []
    for i in range(count):
        brand = brands[i % len(brands)]
        products.append({
            'id': f'{brand.lower()}_{i+1}',
            'name': f'{brand} Model-{i+1}',
            'brand': brand,
            'category': random.choice(categories),
            'code': f'CODE{i+1:04d}',
            'isOriginal': brand == 'COXO'
        })
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f'{count} products generated.')

if __name__ == '__main__':
    generate_products()
