#!/usr/bin/env python3
"""Multi-source W&H image scraper - tries 3+ retailers for exact model match"""
import json, os, re, time, requests, glob, urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
TIMEOUT = 15

SOURCES = [
    {
        'name': 'bencowood',
        'search': 'https://www.bencowood.com/catalogsearch/result/?q={q}',
        'selector': '.product-item-info',
        'image_attr': 'src',
        'link_selector': 'a.product-item-link',
    },
    {
        'name': 'swallowdental',
        'search': 'https://www.swallowdental.co.uk/catalogsearch/result/?q={q}',
        'selector': '.product-item-info',
        'image_attr': 'src',
        'link_selector': 'a',
    },
    {
        'name': 'dentalsky',
        'search': 'https://www.dentalsky.com/catalogsearch/result/?q={q}',
        'selector': '.product-item-info',
        'image_attr': 'src',
        'link_selector': 'a',
    },
    {
        'name': 'hagerwerken',
        'search': 'https://www.hagerwerken.de/shop/index.php?sSuche={q}&sSearchSubmit=1',
        'selector': '.product--box',
        'image_attr': 'src',
        'link_selector': 'a.product--title',
    },
]

def find_images(code, model_flat):
    """Search all sources for exact W&H model match"""
    all_imgs = []
    
    search_terms = [code.lower().replace('-',' '), model_flat]
    
    for source in SOURCES:
        for term in search_terms:
            try:
                url = source['search'].format(q=quote_plus(term))
                r = requests.get(url, headers=H, timeout=TIMEOUT, allow_redirects=True, verify=False)
                if r.status_code != 200:
                    continue
                
                soup = BeautifulSoup(r.text, 'lxml')
                items = soup.select(source['selector'])
                
                for item in items:
                    item_text = item.get_text(strip=True).lower()
                    item_clean = item_text.replace('-','').replace(' ','').replace('_','')
                    
                    # Check if this product item matches our model
                    if model_flat not in item_clean:
                        continue
                    
                    # Get images
                    for img in item.find_all('img'):
                        src = img.get(source.get('image_attr', 'src'))
                        if not src:
                            src = img.get('data-src', '') or img.get('data-original', '')
                        if not src:
                            continue
                        full = urljoin(r.url, src)
                        # Check image is from product media
                        if any(d in full.lower() for d in ['/media/', '/product/', '/images/product', '/wp-content', '/shop/images']):
                            if full not in all_imgs:
                                all_imgs.append(full)
                        elif re.search(r'w[-_]?h[-_]?[a-z]*[-\s]?\d{2,3}', full.lower()):
                            if full not in all_imgs:
                                all_imgs.append(full)
            
            except Exception as e:
                continue
            
            if all_imgs:
                break
        if all_imgs:
            break
    
    return all_imgs[:8]  # Max 8 images

def main():
    # Also try direct product pages on bencowood (known W&H distributor)
    bencowood_pages = {
        'syneta98': 'https://www.bencowood.com/catalogsearch/result/?q=synea+TA+98',
        'alegrate98': 'https://www.bencowood.com/catalogsearch/result/?q=alegra+TE+98',
        'syneawk93': 'https://www.bencowood.com/catalogsearch/result/?q=synea+WK+93',
        'syneata92': 'https://www.bencowood.com/catalogsearch/result/?q=synea+TA+92',
        'alegrate95': 'https://www.bencowood.com/catalogsearch/result/?q=alegra+TE+95',
        'tk98': 'https://www.bencowood.com/catalogsearch/result/?q=SYNEA+VISION+TK-98',
    }
    
    with open('data/products.json') as f:
        products = json.load(f)
    with open('image_mapping.json') as f:
        mapping = json.load(f)
    
    wh_products = [(p['id'], p['code'], p['name']) for p in products if p['brand'] == 'W&H']
    
    # Only re-scrape products without images
    todo = []
    for pid, code, name in wh_products:
        mm = re.search(r'([A-Z]{2})[-\s]?(\d{2,3})', code, re.I)
        if not mm:
            continue
        model_flat = f"{mm.group(1).lower()}{mm.group(2)}"
        existing = mapping.get(pid, {}).get('images', []) 
        if not existing:
            todo.append((pid, code, name, model_flat))
    
    print(f'W&H to re-scrape ({len(SOURCES)} sources): {len(todo)}')
    
    ok = 0
    for i, (pid, code, name, model_flat) in enumerate(todo, 1):
        print(f'[{i}/{len(todo)}] {name[:50]} (code={model_flat}) ...', end=' ', flush=True)
        
        urls = find_images(code, model_flat)
        
        if not urls:
            print('not found on any site')
            time.sleep(0.3)
            continue
        
        print(f'{len(urls)} urls ...', end=' ', flush=True)
        
        # Download images
        saved = []
        for j, url in enumerate(urls, 1):
            ext = 'png' if '.png' in url.lower() else 'jpg'
            path = f'images/{pid}/{j}.{ext}'
            try:
                r = requests.get(url, headers=H, timeout=TIMEOUT, verify=False)
                if r.status_code == 200 and len(r.content) > 2000:
                    os.makedirs(f'images/{pid}', exist_ok=True)
                    with open(path, 'wb') as f:
                        f.write(r.content)
                    saved.append(path)
            except:
                pass
            time.sleep(0.1)
        
        mapping[pid]['images'] = saved
        mapping[pid]['source_urls'] = urls
        if len(saved) >= 3:
            ok += 1
        print(f'{len(saved)} saved')
        
        if i % 10 == 0:
            with open('image_mapping.json', 'w') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
        time.sleep(0.3)
    
    with open('image_mapping.json', 'w') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    # Also update products.json
    for p in products:
        if p['id'] in mapping:
            imgs = mapping[p['id']]['images']
            d = f'images/{p["id"]}'
            if os.path.isdir(d):
                p['images'] = len(glob.glob(f'{d}/*'))
            else:
                p['images'] = 0
    
    with open('data/products.json', 'w') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    print(f'\nDone: {ok}/{len(todo)} with 3+ images')

if __name__ == '__main__':
    main()
