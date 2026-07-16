#!/usr/bin/env python3
"""COXO image scraper - jmudental.com (English) first, coxotec.cn (Chinese text) as fallback"""
import json, os, re, time, requests, glob, urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
TIMEOUT = 12

# ====== JMUNDENTAL SCRAPER (English images) ======
with open('coxo_catalog.json') as f:
    jm_catalog = json.load(f)

def scrape_jmudental(pid, code):
    """Scrape jmudental for English COXO images"""
    # Try to find matching product in catalog
    handle = None
    code_clean = code.lower().replace('-','').replace(' ','')
    
    for h in jm_catalog:
        h_clean = h.lower().replace('-','').replace(' ','').replace('_','')
        if code_clean in h_clean or (len(code_clean) > 4 and h_clean.find(code_clean[:4]) >= 0):
            handle = h
            break
    
    if not handle:
        return []
    
    urls = jm_catalog[handle].get('images', [])
    if not urls:
        return []
    
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
        time.sleep(0.15)
    
    return saved

# ====== COXOTEC.CN SCRAPER (Chinese text, but official) ======
# Product page URLs from previous scrape - we know the exact pages
COXOTEC_PAGES = [
    ('coxo_us', 'https://www.coxotec.cn/cp-2/'),
    ('coxo_ia', 'https://www.coxotec.cn/c-activator/'),
    ('coxo_bs', 'https://www.coxotec.cn/c-surge/'),
    ('coxo_im2', 'https://www.coxotec.cn/c-sailor-ii/'),
    ('coxo_sb', 'https://www.coxotec.cn/c-blaster/'),
    ('coxo_csm', 'https://www.coxotec.cn/c-smart-mini/'),
    ('coxo_csi', 'https://www.coxotec.cn/c-smart-i-pilot/'),
    ('coxo_csp', 'https://www.coxotec.cn/c-smart-i-pro/'),
    ('coxo_d85', 'https://www.coxotec.cn/db-685/'),
    ('coxo_d86', 'https://www.coxotec.cn/db-686-lattre/'),
    ('coxo_d8s', 'https://www.coxotec.cn/db-686-swift/'),
    ('coxo_d8h', 'https://www.coxotec.cn/db-686-honor/'),
    ('coxo_d8m', 'https://www.coxotec.cn/db-686-mocha/'),
    ('coxo_15', 'https://www.coxotec.cn/cx235-1-5/'),
    ('coxo_h01', 'https://www.coxotec.cn/h01-d1sp/'),
    ('coxo_c73', 'https://www.coxotec.cn/c7-3s1/'),
    ('coxo_cxf', 'https://www.coxotec.cn/cx207-f/'),
    ('coxo_led', 'https://www.coxotec.cn/cx-led/'),
    ('coxo_mp', 'https://www.coxotec.cn/mini-pedo/'),
    ('coxo_tor', 'https://www.coxotec.cn/cx-tornado/'),
    ('coxo_cma', 'https://www.coxotec.cn/c-smart-mini-ap/'),
    ('coxo_crv', 'https://www.coxotec.cn/c-root-vi/'),
    ('coxo_csn', 'https://www.coxotec.cn/c-smart-nova/'),
    ('coxo_cri', 'https://www.coxotec.cn/c-root-i-plus/'),
    ('coxo_cfm', 'https://www.coxotec.cn/c-fill-mini/'),
    ('coxo_cfx', 'https://www.coxotec.cn/c-fill-x/'),
    ('coxo_cbl', 'https://www.coxotec.cn/c-blade/'),
    ('coxo_ccl', 'https://www.coxotec.cn/c-clear/'),
    ('coxo_cc2', 'https://www.coxotec.cn/c-clear-2/'),
    ('coxo_ccd', 'https://www.coxotec.cn/c-clear-2-dlx/'),
    ('coxo_im3', 'https://www.coxotec.cn/c-sailor-iii/'),
    ('coxo_sch', 'https://www.coxotec.cn/sc-ch/'),
    ('coxo_sp8', 'https://www.coxotec.cn/sc-pro-2018/'),
    ('coxo_spr', 'https://www.coxotec.cn/sc-pro/'),
    ('coxo_cf1', 'https://www.coxotec.cn/c-fr1/'),
    ('coxo_bfr', 'https://www.coxotec.cn/c-fr2/'),
    ('coxo_csa', 'https://www.coxotec.cn/c-sailor-air/'),
    ('coxo_csp2', 'https://www.coxotec.cn/c-sailor-pro/'),
    ('coxo_100', 'https://www.coxotec.cn/cx100/'),
    ('coxo_gen', 'https://www.coxotec.cn/geni-pro/'),
    ('coxo_200', 'https://www.coxotec.cn/cx200/'),
    ('coxo_cma2', 'https://www.coxotec.cn/c-smart-mini-ap-plus/'),
    ('coxo_cpm', 'https://www.coxotec.cn/c-puma-master/'),
]

def scrape_coxotec(pid, url):
    """Scrape coxotec.cn product page"""
    saved = []
    source_urls = []
    try:
        r = requests.get(url, headers=H, timeout=TIMEOUT, verify=False)
        if r.status_code != 200:
            return [], []
        
        soup = BeautifulSoup(r.text, 'lxml')
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            if not src:
                continue
            if 'placeholder' in src.lower() or 'blank' in src.lower():
                continue
            full = urljoin(url, src)
            # Only product images (not icons/logos)
            if any(skip in full.lower() for skip in ['logo', 'icon', 'avatar', 'flag']):
                continue
            source_urls.append(full)
        
        for j, url_img in enumerate(source_urls, 1):
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

# ====== MAIN ======
def main():
    with open('data/products.json') as f:
        products = json.load(f)
    with open('image_mapping.json') as f:
        mapping = json.load(f)
    
    coxo_products = [p for p in products if p['brand'] == 'COXO']
    print(f'COXO products: {len(coxo_products)}')
    
    # Phase 1: Try jmudental (English) for all COXO products
    print('\n=== Phase 1: jmudental (English images) ===')
    jm_ok = 0
    for i, prod in enumerate(coxo_products, 1):
        pid = prod['id']
        saved = scrape_jmudental(pid, prod['code'])
        if saved:
            mapping[pid]['images'] = saved
            mapping[pid]['source_urls'] = ['(jmudental.com)']
            jm_ok += 1
            if jm_ok <= 5 or jm_ok % 10 == 0:
                print(f'  [{jm_ok}] {pid}: {prod["name"][:50]} -> {len(saved)} EN images')
    
    print(f'\njmudental: {jm_ok}/{len(coxo_products)} with images')
    
    # Phase 2: For remaining, use coxotec.cn (Chinese text but official)
    print('\n=== Phase 2: coxotec.cn (Chinese text - fallback) ===')
    cn_pages = {pid: url for pid, url in COXOTEC_PAGES}
    
    cn_ok = 0
    for i, prod in enumerate(coxo_products, 1):
        pid = prod['id']
        # Only if no images from jmudental and page exists on coxotec.cn
        existing = mapping.get(pid, {}).get('images', [])
        if not existing and pid in cn_pages:
            saved, sources = scrape_coxotec(pid, cn_pages[pid])
            if saved:
                mapping[pid]['images'] = saved
                mapping[pid]['source_urls'] = sources
                cn_ok += 1
                if cn_ok <= 5:
                    print(f'  [{cn_ok}] {pid}: {prod["name"][:50]} -> {len(saved)} CN images')
    
    print(f'\ncoxotec.cn: {cn_ok} additional products')
    print(f'Total COXO with images: {jm_ok + cn_ok}/{len(coxo_products)}')
    
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

if __name__ == '__main__':
    main()
