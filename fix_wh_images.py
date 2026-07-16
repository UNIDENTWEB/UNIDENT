#!/usr/bin/env python3
"""Accurate W&H scraper - exact model matching only"""
import json, os, re, time, requests, glob, urllib3
urllib3.disable_warnings()
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
BASE = 'https://www.swallowdental.co.uk'
TIMEOUT = 10

def scrape_wh_product(code, name):
    """Scrape W&H with exact model match only"""
    mm = re.search(r'([A-Z]{2,3})[-\s]?(\d{2,3})', code, re.I)
    if not mm:
        return []
    prefix = mm.group(1).lower()
    number = mm.group(2)
    model = f"{prefix}-{number}"
    model_flat = f"{prefix}{number}"

    all_imgs = []
    detail_url = None

    # Search for exact model
    search_terms = [model, code.lower().replace('-',' '), f"{prefix} {number}"]
    for term in search_terms[:3]:
        try:
            url = f'{BASE}/catalogsearch/result/?q={quote_plus(term)}'
            r = requests.get(url, headers=H, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'lxml')

            for item in soup.select('.product-item-info'):
                item_text = item.get_text(strip=True).lower()
                item_clean = item_text.replace('-','').replace(' ','')
                if model_flat not in item_clean:
                    continue

                a_tag = item.find('a', href=True)
                if a_tag:
                    href = a_tag['href']
                    if '/catalog/product/' in href or href.endswith('.html'):
                        detail_url = urljoin(BASE, href)

                for img in item.find_all('img'):
                    src = img.get('src') or img.get('data-src') or ''
                    if not src: continue
                    full = urljoin(BASE, src)
                    if '/media/catalog/product' not in full:
                        continue
                    fn = full.lower().split('/')[-1].replace('-','').replace('_','').replace(' ','')
                    if model_flat in fn:
                        all_imgs.append(full)

            if detail_url or all_imgs:
                break
        except:
            continue

    if detail_url:
        try:
            time.sleep(0.3)
            dr = requests.get(detail_url, headers=H, timeout=TIMEOUT)
            if dr.status_code == 200:
                ds = BeautifulSoup(dr.text, 'lxml')
                for img in ds.find_all('img'):
                    src = img.get('src') or img.get('data-src') or ''
                    if not src: continue
                    full = urljoin(BASE, src).split('?')[0]
                    if '/media/catalog/product' not in full:
                        continue
                    fn = full.lower().split('/')[-1].replace('-','').replace('_','').replace(' ','')
                    if model_flat in fn:
                        all_imgs.append(full)
                # Also check <a> links for gallery
                for a in ds.find_all('a', href=True):
                    href = a['href']
                    if not any(href.lower().endswith(e) for e in ('.jpg','.png','.jpeg','.webp')):
                        continue
                    full = urljoin(BASE, href).split('?')[0]
                    if '/media/catalog/product' not in full:
                        continue
                    fn = full.lower().split('/')[-1].replace('-','').replace('_','').replace(' ','')
                    if model_flat in fn:
                        all_imgs.append(full)
        except:
            pass

    # Deduplicate
    seen = set()
    unique = []
    for u in all_imgs:
        k = u.split('?')[0].rstrip('/')
        if k not in seen:
            seen.add(k)
            unique.append(u)
    return unique[:8]


def main():
    with open('image_mapping.json') as f:
        mapping = json.load(f)

    todo = []
    for pid, info in mapping.items():
        if not pid.startswith('wh_'):
            continue
        # Check if images are correct
        urls = info.get('source_urls', [])
        code = info.get('code', '')
        mm = re.search(r'([A-Z]{2,3})[-\s]?(\d{2,3})', code, re.I)
        if not mm:
            todo.append(pid)
            continue
        model_flat = mm.group(1).lower() + mm.group(2)
        matching = sum(1 for u in urls if model_flat in u.lower().replace('-','').replace('_','').replace(' ',''))
        if matching < 3 or len(info.get('images',[])) < 3:
            todo.append(pid)

    print(f'W&H products to re-scrape: {len(todo)}')

    ok = 0
    for i, pid in enumerate(todo, 1):
        info = mapping[pid]
        name = info.get('name', '')
        code = info.get('code', '')
        print(f'[{i}/{len(todo)}] {name[:50]} ...', end=' ', flush=True)

        urls = scrape_wh_product(code, name)
        if not urls:
            # Clear wrong images
            mapping[pid]['images'] = []
            mapping[pid]['source_urls'] = []
            print('0 images')
            time.sleep(0.2)
            continue

        print(f'{len(urls)} urls ...', end=' ', flush=True)
        saved = []
        for j, url in enumerate(urls, 1):
            ext = 'png' if '.png' in url.lower() else 'jpg'
            path = f'images/{pid}/{j}.{ext}'
            try:
                r = requests.get(url, headers=H, timeout=TIMEOUT)
                if r.status_code == 200 and len(r.content) > 1000:
                    os.makedirs(f'images/{pid}', exist_ok=True)
                    with open(path, 'wb') as f:
                        f.write(r.content)
                    saved.append(path)
            except:
                pass
            time.sleep(0.15)

        mapping[pid]['images'] = saved
        mapping[pid]['source_urls'] = urls
        if len(saved) >= 3:
            ok += 1
        print(f'{len(saved)} saved')

        if i % 10 == 0:
            with open('image_mapping.json', 'w') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
        time.sleep(0.2)

    with open('image_mapping.json', 'w') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f'\nDone: {ok}/{len(todo)} with 3+ exact images')

if __name__ == '__main__':
    main()
