#!/usr/bin/env python3
"""NSK image scraper - fordent.ru + nsk-dental.com"""
import json, os, re, time, requests, glob, urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
TIMEOUT = 12

# Known NSK product page URLs from previous scrape
NSK_PAGES = {
    'nsk_1': 'https://fordent.ru/product-category/stomatologicheskie-nakonechniki/nakonechniki-nsk/nsk-nakonechniki-turbinnye/nsk-ti-max-z/',
    'nsk_2': 'https://fordent.ru/product-category/stomatologicheskie-nakonechniki/nakonechniki-nsk/nsk-nakonechniki-turbinnye/nsk-ti-max-x/',
    'nsk_3': 'https://fordent.ru/product-category/stomatologicheskie-nakonechniki/nakonechniki-nsk/nsk-nakonechniki-turbinnye/nsk-ti-max-z95l/',
    'nsk_4': 'https://fordent.ru/product-category/stomatologicheskie-nakonechniki/nakonechniki-nsk/nsk-nakonechniki-turbinnye/nsk-pana-air/',
    'nsk_5': 'https://fordent.ru/product-category/stomatologicheskie-nakonechniki/nakonechniki-nsk/nsk-nakonechniki-turbinnye/nsk-pana-max/',
    'nsk_6': 'https://fordent.ru/product-category/stomatologicheskie-nakonechniki/nakonechniki-nsk/nsk-nakonechniki-turbinnye/nsk-pana-max-plus/',
    'nsk_7': 'https://fordent.ru/product-category/stomatologicheskie-nakonechniki/nakonechniki-nsk/nsk-nakonechniki-turbinnye/nsk-vmax/',
    'nsk_8': 'https://fordent.ru/product-category/stomatologicheskie-nakonechniki/nakonechniki-nsk/nsk-nakonechniki-turbinnye/nsk-s-max-m/',
    'nsk_9': 'https://fordent.ru/product-category/stomatologicheskie-nakonechniki/nakonechniki-nsk/nsk-nakonechniki-uglovye/nsk-ti-max-z/',
}

def scrape_fordent(pid, url):
    """Scrape fordent.ru category page for NSK images"""
    saved = []
    source_urls = []
    try:
        r = requests.get(url, headers=H, timeout=TIMEOUT, verify=False)
        if r.status_code != 200:
            return [], []
        
        soup = BeautifulSoup(r.text, 'lxml')
        
        # Find product images
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            if not src or 'placeholder' in src.lower():
                continue
            full = urljoin(url, src)
            if any(x in full.lower() for x in ['logo', 'icon', 'avatar', '/banners/', '/wp-content/plugins']):
                continue
            if any(x in full.lower() for x in ['/upload/', '/catalog/', '/product/', '/wp-content/uploads']):
                source_urls.append(full)
        
        # Download
        for j, url_img in enumerate(source_urls[:8], 1):
            ext = 'png' if '.png' in url_img.lower() else 'jpg'
            path = f'images/{pid}/{j}.{ext}'
            try:
                r2 = requests.get(url_img, headers=H, timeout=TIMEOUT, verify=False)
                if r2.status_code == 200 and len(r2.content) > 2000:
                    os.makedirs(f'images/{pid}', exist_ok=True)
                    with open(path, 'wb') as f:
                        f.write(r2.content)
                    saved.append(path)
            except:
                pass
            time.sleep(0.1)
    except Exception as e:
        pass
    
    return saved, source_urls

def scrape_nsk_official(pid, url):
    """Scrape nsk-dental.com product page"""
    saved = []
    source_urls = []
    try:
        r = requests.get(url, headers=H, timeout=TIMEOUT, verify=False)
        if r.status_code != 200:
            return [], []
        
        soup = BeautifulSoup(r.text, 'lxml')
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            if not src or 'placeholder' in src.lower():
                continue
            full = urljoin(url, src)
            if any(x in full.lower() for x in ['logo', 'icon', 'avatar', 'flag']):
                continue
            if any(x in full.lower() for x in ['/wp-content/uploads', '/images/product', '/catalog']):
                source_urls.append(full)
        
        for j, url_img in enumerate(source_urls[:8], 1):
            ext = 'png' if '.png' in url_img.lower() else 'jpg'
            path = f'images/{pid}/{j}.{ext}'
            try:
                r2 = requests.get(url_img, headers=H, timeout=TIMEOUT, verify=False)
                if r2.status_code == 200 and len(r2.content) > 2000:
                    os.makedirs(f'images/{pid}', exist_ok=True)
                    with open(path, 'wb') as f:
                        f.write(r2.content)
                    saved.append(path)
            except:
                pass
            time.sleep(0.1)
    except:
        pass
    
    return saved, source_urls

def main():
    with open('data/products.json') as f:
        products = json.load(f)
    with open('image_mapping.json') as f:
        mapping = json.load(f)
    
    # Also try loading NSK official catalog
    nsk_official_pages = {}
    try:
        with open('nsk_official_catalog.json') as f:
            nsk_cat = json.load(f)
            for pid, info in nsk_cat.items():
                if info.get('url'):
                    nsk_official_pages[pid] = info['url']
    except:
        pass
    
    nsk_products = [p for p in products if p['brand'] == 'NSK']
    print(f'NSK products: {len(nsk_products)}')
    
    # Phase 1: Try fordent.ru known pages
    print('\n=== Phase 1: fordent.ru ===')
    fr_ok = 0
    for pid, url in NSK_PAGES.items():
        prod = next((p for p in nsk_products if p['id'] == pid), None)
        if not prod:
            continue
        saved, sources = scrape_fordent(pid, url)
        if saved:
            mapping[pid]['images'] = saved
            mapping[pid]['source_urls'] = sources
            fr_ok += 1
            print(f'  [{fr_ok}] {pid}: {prod["name"][:50]} -> {len(saved)} images')
    
    print(f'\nfordent.ru: {fr_ok} with images')
    
    # Phase 2: Search fordent.ru for remaining products
    print('\n=== Phase 2: fordent.ru search ===')
    for i, prod in enumerate(nsk_products, 1):
        pid = prod['id']
        existing = mapping.get(pid, {}).get('images', [])
        if existing:
            continue
        
        code = prod.get('code', '').lower().replace('-',' ').replace('_',' ')
        try:
            search_url = f'https://fordent.ru/?s={quote_plus(code)}&post_type=product'
            r = requests.get(search_url, headers=H, timeout=TIMEOUT, verify=False)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'lxml')
                product_links = soup.select('a.woocommerce-LoopProduct-link, .product a[href]')
                if product_links:
                    href = urljoin(search_url, product_links[0]['href'])
                    saved, sources = scrape_fordent(pid, href)
                    if saved:
                        mapping[pid]['images'] = saved
                        mapping[pid]['source_urls'] = sources
                        print(f'  {pid}: {prod["name"][:50]} -> {len(saved)} images')
        except:
            pass
        time.sleep(0.3)
    
    # Phase 3: Try nsk-dental.com official pages
    print('\n=== Phase 3: nsk-dental.com official ===')
    for pid, url in nsk_official_pages.items():
        existing = mapping.get(pid, {}).get('images', [])
        if existing:
            continue
        prod = next((p for p in nsk_products if p['id'] == pid), None)
        if not prod:
            continue
        saved, sources = scrape_nsk_official(pid, url)
        if saved:
            mapping[pid]['images'] = saved
            mapping[pid]['source_urls'] = sources
            print(f'  {pid}: {prod["name"][:50]} -> {len(saved)} images')
    
    # Save
    with open('image_mapping.json', 'w') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    # Update products.json
    for prod in products:
        pid = prod['id']
        d = f'images/{pid}'
        if os.path.isdir(d):
            prod['images'] = len(glob.glob(f'{d}/*'))
        else:
            prod['images'] = 0
    
    with open('data/products.json', 'w') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    with_img = sum(1 for p in nsk_products if p['images'] >= 3)
    print(f'\nNSK Done: {with_img}/{len(nsk_products)} with 3+ images')

if __name__ == '__main__':
    main()
