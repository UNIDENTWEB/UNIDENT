#!/usr/bin/env python3
"""Fix scraper — scrape missing product images from official brand sites"""

import json, os, re, time, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
OUTPUT_DIR = 'images'
TIMEOUT = 10


def is_bad_image(url):
    bad = ('logo','icon','avatar','banner','placeholder','wpcf7','rating',
           'flag','payment','gravatar','thumb-video','video-thumb','-150x150',
           '-100x100','-80x80','-64x64')
    return any(x in url.lower() for x in bad)


def extract_images(soup, base_url, path_filter=None):
    images = []
    for tag in soup.find_all(['img','a']):
        if tag.name == 'a':
            href = tag.get('href','')
            if any(href.lower().endswith(e) for e in ('.jpg','.jpeg','.png','.webp')):
                src = href
            else:
                continue
        else:
            src = tag.get('src') or tag.get('data-src') or tag.get('data-lazy-src') or ''
        if not src:
            continue
        full = urljoin(base_url, src)
        if is_bad_image(full):
            continue
        if path_filter and not path_filter(full):
            continue
        images.append(full)
    return images


def download_image(url, save_path):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200 and len(r.content) > 1000:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(r.content)
            return True
    except:
        pass
    return False


def slugify(text):
    t = text.lower().strip()
    t = re.sub(r'[^\w\s-]', '', t)
    t = re.sub(r'[\s_]+', '-', t)
    return t.strip('-')


def scrape_coxotec(code, name):
    """Scrape COXO product from coxotec.com"""
    model = code.lower().replace(' ','-').replace('_','-')
    name_slug = slugify(name.replace('COXO','').strip())
    
    urls = [
        f'https://coxotec.com/product/{model}/',
        f'https://coxotec.com/product/{name_slug}/',
        f'https://coxotec.com/en/product/{model}/',
        f'https://coxotec.com/en/product/{name_slug}/',
    ]
    
    all_images = []
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, 'lxml')
            
            imgs = extract_images(soup, 'https://coxotec.com',
                lambda u: any(x in u.lower() for x in ('uploads','product','wp-content')))
            
            if imgs:
                all_images.extend(imgs)
                break
        except:
            continue
    
    # Deduplicate
    seen = set()
    unique = []
    for img in all_images:
        base = img.split('?')[0].rstrip('/')
        if base not in seen:
            seen.add(base)
            unique.append(img)
    
    return unique[:8]


def scrape_wh_swallowdental(code, name):
    """Scrape W&H product from swallowdental.co.uk with relaxed matching"""
    base = 'https://www.swallowdental.co.uk'
    
    # Extract model number from code e.g. SYNEA-TA-98 -> TA-98
    search_terms = [code]
    m = re.search(r'([A-Z]{2,3})[-\s]?(\d{2,3})', code, re.I)
    if m:
        search_terms.append(f'{m.group(1)}-{m.group(2)}')
    
    all_images = []
    for term in search_terms[:2]:
        try:
            search_url = f'{base}/catalogsearch/result/?q={quote_plus(term)}'
            resp = requests.get(search_url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, 'lxml')
            
            for item in soup.select('.product-item-info'):
                a_tag = item.find('a', href=True)
                if not a_tag:
                    continue
                
                # Get images from search results
                for img in item.find_all('img'):
                    src = img.get('src') or img.get('data-src') or ''
                    if '/media/catalog/product' in src:
                        all_images.append(urljoin(base, src))
                
                # Visit product detail page
                detail_url = a_tag['href']
                if not detail_url.startswith('http'):
                    detail_url = urljoin(base, detail_url)
                
                try:
                    time.sleep(0.3)
                    dr = requests.get(detail_url, headers=HEADERS, timeout=TIMEOUT)
                    if dr.status_code == 200:
                        ds = BeautifulSoup(dr.text, 'lxml')
                        for img in ds.find_all('img'):
                            src = img.get('src') or img.get('data-src') or ''
                            if '/media/catalog/product' in src:
                                all_images.append(urljoin(base, src))
                except:
                    pass
                
                if all_images:
                    break
            
            if all_images:
                break
        except:
            continue
    
    seen = set()
    unique = []
    for img in all_images:
        base = img.split('?')[0].rstrip('/')
        if base not in seen and not is_bad_image(img):
            seen.add(base)
            unique.append(img)
    
    return unique[:8]


def scrape_nsk_fordent(code, name):
    """Scrape NSK product from fordent.ru (for products not on nsk-dental.com)"""
    base = 'https://fordent.ru'
    all_images = []
    
    search_terms = [code]
    if '-' in code:
        search_terms.append(code.replace('-',' '))
    
    for term in search_terms[:2]:
        try:
            search_url = f'{base}/search/?q={quote_plus(term)}'
            resp = requests.get(search_url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, 'lxml')
            
            for card in soup.find_all(class_='product-card'):
                a = card.find('a', href=True)
                if not a:
                    continue
                card_text = card.get_text(strip=True).lower()
                if code.lower().replace('-','').replace(' ','') in card_text.replace('-','').replace(' ',''):
                    product_url = urljoin(base, a['href'])
                    try:
                        time.sleep(0.3)
                        pr = requests.get(product_url, headers=HEADERS, timeout=TIMEOUT)
                        if pr.status_code == 200:
                            ps = BeautifulSoup(pr.text, 'lxml')
                            all_images.extend(extract_images(ps, base,
                                lambda u: '/upload/' in u or '/catalog/' in u))
                    except:
                        pass
                    if all_images:
                        break
            if all_images:
                break
        except:
            continue
    
    seen = set()
    unique = []
    for img in all_images:
        base = img.split('?')[0].rstrip('/')
        if base not in seen and not is_bad_image(img):
            seen.add(base)
            unique.append(img)
    
    return unique[:8]


def main():
    with open('image_mapping.json') as f:
        mapping = json.load(f)
    
    stats = {'COXO': 0, 'W&H': 0, 'NSK': 0}
    
    for pid, info in list(mapping.items()):
        if len(info.get('images', [])) >= 3:
            continue
        
        brand = info.get('brand', '')
        code = info.get('code', '')
        name = info.get('name', '')
        
        print(f'[{pid}] {name} ...', end=' ', flush=True)
        
        image_urls = []
        if brand == 'COXO':
            image_urls = scrape_coxotec(code, name)
        elif brand == 'W&H':
            image_urls = scrape_wh_swallowdental(code, name)
        elif brand == 'NSK':
            image_urls = scrape_nsk_fordent(code, name)
        
        if not image_urls:
            print('NO IMAGES')
            time.sleep(0.3)
            continue
        
        print(f'{len(image_urls)} urls ...', end=' ', flush=True)
        
        img_dir = os.path.join(OUTPUT_DIR, pid)
        saved = []
        for i, url in enumerate(image_urls, 1):
            ext = 'png' if '.png' in url.lower() else 'jpg'
            path = os.path.join(img_dir, f'{i}.{ext}')
            if download_image(url, path):
                saved.append(path)
            time.sleep(0.2)
        
        if saved:
            mapping[pid]['images'] = saved
            mapping[pid]['source_urls'] = image_urls
            stats[brand] += 1
            print(f'{len(saved)} saved')
        else:
            print('download failed')
        
        # Save after each product
        with open('image_mapping.json', 'w') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        
        time.sleep(0.5)
    
    print(f'\nDone: COXO={stats["COXO"]}, WH={stats["W&H"]}, NSK={stats["NSK"]}')
    
    # Final summary
    total_ok = sum(1 for v in mapping.values() if len(v.get('images',[])) >= 3)
    print(f'Total products with 3+ images: {total_ok}/300')

if __name__ == '__main__':
    main()
