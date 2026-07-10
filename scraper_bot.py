#!/usr/bin/env python3
# scraper_bot.py - دریافت تصاویر از سایت‌های مرجع با requests

import os
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def get_coxo_image(product_name, product_code):
    """دریافت تصویر از coxotec.com"""
    clean_name = product_name.replace(/^[A-Z]+\s*/i, '').lower().strip()
    model_part = '-'.join(clean_name.split())
    urls = [
        f'https://coxotec.com/product/{model_part}/',
        f'https://coxotec.com/en/product/{model_part}/',
        f'https://coxotec.com/ja/product/{model_part}/',
        f'https://coxotec.com/ru/product/{model_part}/'
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'lxml')
                # الگوی og:image
                og_img = soup.find('meta', property='og:image')
                if og_img and og_img.get('content'):
                    return og_img['content']
                # تصویر محصول با کلاس
                img = soup.find('img', class_='product-image')
                if img and img.get('src'):
                    return urljoin(url, img['src'])
        except:
            continue
    return None

def get_nsk_image(product_name, product_code):
    """دریافت تصویر از fordent.ru"""
    base = 'https://fordent.ru'
    query = product_code or product_name
    search_url = f'{base}/search/?q={query}'
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'lxml')
            # پیدا کردن اولین تصویر در نتایج جستجو
            img = soup.find('img', src=lambda x: x and ('/catalog/product/' in x or '/upload/' in x))
            if img and img.get('src'):
                return urljoin(base, img['src'])
    except:
        pass
    return None

def get_wh_image(product_name, product_code):
    """دریافت تصویر از expo-dent.com (یا swallowdental.co.uk)"""
    base = 'https://www.swallowdental.co.uk'
    query = product_code or product_name
    search_url = f'{base}/search/{query}'
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'lxml')
            img = soup.find('img', class_='product-image') or \
                  soup.find('img', src=lambda x: x and '/media/catalog/product/' in x)
            if img and img.get('src'):
                return urljoin(base, img['src'])
    except:
        pass
    return None

def main():
    # خواندن فایل products.json (که توسط generate_products.py تولید شده)
    try:
        with open('products.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
    except FileNotFoundError:
        print('❌ products.json یافت نشد!')
        return

    mapping = {}
    total = len(products)
    print(f'🔄 شروع اسکرپینگ تصاویر برای {total} محصول...')

    for idx, p in enumerate(products, 1):
        brand = p.get('brand')
        name = p.get('name', '')
        code = p.get('code', '')
        img_url = None

        if brand == 'COXO':
            img_url = get_coxo_image(name, code)
        elif brand == 'NSK':
            img_url = get_nsk_image(name, code)
        elif brand == 'W&H':
            img_url = get_wh_image(name, code)

        if img_url:
            mapping[p['id']] = {
                'name': name,
                'brand': brand,
                'images': [img_url]
            }
            print(f'✅ {idx}/{total} {name} -> {img_url}')
        else:
            print(f'⚠️ {idx}/{total} تصویر برای {name} یافت نشد')

        time.sleep(1.5)  # جلوگیری از مسدود شدن

    # ذخیره فایل image_mapping.json
    with open('image_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f'✅ اسکرپینگ کامل شد. {len(mapping)} محصول تصویر دارند.')

if __name__ == '__main__':
    main()
