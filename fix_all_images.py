#!/usr/bin/env python3
"""NSK + COXO fix: scrape nsk-dental.com and fix coxotec.cn fallback"""
import json, os, re, time, requests, glob, urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
TIMEOUT = 12

def download_images(pid, urls):
    """Download images from URL list"""
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
    return saved

# ====== NSK: scrape nsk-dental.com ======
def scrape_nsk_official(pid, product_name):
    """Search nsk-dental.com for product page"""
    saved = []
    source_urls = []
    
    # Try direct product URL pattern
    code = product_name.lower().replace(' ', '-').replace('/', '-')
    code_clean = re.sub(r'[^a-z0-9-]', '', code)
    
    try_urls = [
        f'https://www.nsk-dental.com/products/{code_clean}',
        f'https://www.nsk-dental.com/products/handpieces/{code_clean}',
        f'https://www.nsk-dental.com/products/turbines/{code_clean}',
    ]
    
    for url in try_urls:
        try:
            r = requests.get(url, headers=H, timeout=TIMEOUT, verify=False)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'lxml')
            
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or ''
                if not src or 'placeholder' in src.lower():
                    continue
                full = urljoin(url, src)
                if any(x in full.lower() for x in ['logo', 'icon', 'avatar']):
                    continue
                source_urls.append(full)
            
            if source_urls:
                break
        except:
            continue
    
    if source_urls:
        saved = download_images(pid, source_urls[:8])
    
    return saved, source_urls

# ====== COXO: fix coxotec.cn ======
COXOTEC_PAGES = {
    'coxo_us': 'https://www.coxotec.cn/cp-2/',
    'coxo_ia': 'https://www.coxotec.cn/c-activator/',
    'coxo_bs': 'https://www.coxotec.cn/c-surge/',
    'coxo_im2': 'https://www.coxotec.cn/c-sailor-ii/',
    'coxo_sb': 'https://www.coxotec.cn/c-blaster/',
    'coxo_csm': 'https://www.coxotec.cn/c-smart-mini/',
    'coxo_csi': 'https://www.coxotec.cn/c-smart-i-pilot/',
    'coxo_csp': 'https://www.coxotec.cn/c-smart-i-pro/',
    'coxo_d85': 'https://www.coxotec.cn/db-685/',
    'coxo_d86': 'https://www.coxotec.cn/db-686-lattre/',
    'coxo_d8s': 'https://www.coxotec.cn/db-686-swift/',
    'coxo_d8h': 'https://www.coxotec.cn/db-686-honor/',
    'coxo_d8m': 'https://www.coxotec.cn/db-686-mocha/',
    'coxo_15': 'https://www.coxotec.cn/cx235-1-5/',
    'coxo_h01': 'https://www.coxotec.cn/h01-d1sp/',
    'coxo_c73': 'https://www.coxotec.cn/c7-3s1/',
    'coxo_cxf': 'https://www.coxotec.cn/cx207-f/',
    'coxo_led': 'https://www.coxotec.cn/cx-led/',
    'coxo_mp': 'https://www.coxotec.cn/mini-pedo/',
    'coxo_tor': 'https://www.coxotec.cn/cx-tornado/',
    'coxo_cma': 'https://www.coxotec.cn/c-smart-mini-ap/',
    'coxo_crv': 'https://www.coxotec.cn/c-root-vi/',
    'coxo_csn': 'https://www.coxotec.cn/c-smart-nova/',
    'coxo_cri': 'https://www.coxotec.cn/c-root-i-plus/',
    'coxo_cfm': 'https://www.coxotec.cn/c-fill-mini/',
    'coxo_cfx': 'https://www.coxotec.cn/c-fill-x/',
    'coxo_cbl': 'https://www.coxotec.cn/c-blade/',
    'coxo_ccl': 'https://www.coxotec.cn/c-clear/',
    'coxo_cc2': 'https://www.coxotec.cn/c-clear-2/',
    'coxo_ccd': 'https://www.coxotec.cn/c-clear-2-dlx/',
    'coxo_im3': 'https://www.coxotec.cn/c-sailor-iii/',
    'coxo_sch': 'https://www.coxotec.cn/sc-ch/',
    'coxo_sp8': 'https://www.coxotec.cn/sc-pro-2018/',
    'coxo_spr': 'https://www.coxotec.cn/sc-pro/',
    'coxo_cf1': 'https://www.coxotec.cn/c-fr1/',
    'coxo_bfr': 'https://www.coxotec.cn/c-fr2/',
    'coxo_csa': 'https://www.coxotec.cn/c-sailor-air/',
    'coxo_csp2': 'https://www.coxotec.cn/c-sailor-pro/',
    'coxo_100': 'https://www.coxotec.cn/cx100/',
    'coxo_gen': 'https://www.coxotec.cn/geni-pro/',
    'coxo_200': 'https://www.coxotec.cn/cx200/',
    'coxo_cma2': 'https://www.coxotec.cn/c-smart-mini-ap-plus/',
    'coxo_cpm': 'https://www.coxotec.cn/c-puma-master/',
}

def scrape_coxotec(pid, url):
    """Scrape coxotec.cn - get all product images"""
    source_urls = []
    try:
        r = requests.get(url, headers=H, timeout=TIMEOUT, verify=False)
        if r.status_code != 200:
            return [], []
        
        soup = BeautifulSoup(r.text, 'lxml')
        
        # Get all images except logos/icons/placeholders
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            if not src:
                continue
            # Skip non-product images
            src_lower = src.lower()
            if any(x in src_lower for x in ['placeholder', 'blank', 'logo', 'icon', 'avatar', 'flag', '1x1', 'pixel']):
                continue
            full = urljoin(url, src)
            source_urls.append(full)
        
        # Deduplicate
        source_urls = list(dict.fromkeys(source_urls))
        
    except Exception as e:
        pass
    
    if source_urls:
        return download_images(pid, source_urls), source_urls
    return [], []

def main():
    with open('data/products.json') as f:
        products = json.load(f)
    with open('image_mapping.json') as f:
        mapping = json.load(f)
    
    # ====== FIX COXO: Run coxotec.cn for products still without images ======
    print('=== COXO: coxotec.cn fallback ===')
    cn_ok = 0
    cn_fail = 0
    for prod in products:
        if prod['brand'] != 'COXO':
            continue
        pid = prod['id']
        if prod['images'] > 0:
            continue
        if pid not in COXOTEC_PAGES:
            continue
        
        url = COXOTEC_PAGES[pid]
        saved, sources = scrape_coxotec(pid, url)
        if saved:
            mapping[pid]['images'] = saved
            mapping[pid]['source_urls'] = sources
            cn_ok += 1
            print(f'  {pid}: {prod["name"][:50]} -> {len(saved)} CN images')
        else:
            cn_fail += 1
            if cn_fail <= 3:
                print(f'  {pid}: FAILED - {url}')
    
    print(f'coxotec.cn: {cn_ok} ok, {cn_fail} failed')
    
    # ====== NSK: nsk-dental.com ======
    print('\n=== NSK: nsk-dental.com ===')
    nsk_ok = 0
    for i, prod in enumerate(products[:50], 1):  # Process in batches with progress
        if prod['brand'] != 'NSK':
            continue
        pid = prod['id']
        if prod['images'] > 0:
            continue
        
        saved, sources = scrape_nsk_official(pid, prod['name'])
        if saved:
            mapping[pid]['images'] = saved
            mapping[pid]['source_urls'] = sources
            nsk_ok += 1
            print(f'  [{nsk_ok}] {pid}: {prod["name"][:50]} -> {len(saved)} images')
        elif i % 10 == 0:
            print(f'  ...processed {i}/77 NSK products...')
    
    print(f'nsk-dental.com: {nsk_ok} with images')
    
    # Save
    with open('image_mapping.json', 'w') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    for prod in products:
        pid = prod['id']
        d = f'images/{pid}'
        if os.path.isdir(d):
            prod['images'] = len(glob.glob(f'{d}/*'))
        else:
            prod['images'] = 0
    
    with open('data/products.json', 'w') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    # Final stats
    coxo_img = sum(1 for p in products if p['brand']=='COXO' and p['images']>=3)
    nsk_img = sum(1 for p in products if p['brand']=='NSK' and p['images']>=3)
    wh_img = sum(1 for p in products if p['brand']=='W&H' and p['images']>=3)
    print(f'\nFinal: COXO {coxo_img}/78, NSK {nsk_img}/77, W&H {wh_img}/100')
    print(f'Total: {coxo_img+nsk_img+wh_img}/255 with 3+ images')

if __name__ == '__main__':
    main()
