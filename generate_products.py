import json
import random

def generate_products(count=300):
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
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f'✅ {count} محصول تولید شد.')

if __name__ == '__main__':
    generate_products()
