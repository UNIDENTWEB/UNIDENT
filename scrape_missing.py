#!/usr/bin/env python3
"""Scrape missing images for NSK and W&H products only"""
import json, os, re, time, requests, glob
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
TIMEOUT = 8
OUTPUT = 'images'

def dedupe(urls):
    seen = set()
    out = []
    for u in urls:
        k = u.split('?')[0].rstrip('/')
        if k not in seen:
            seen.add(k)
            out.append(u)
    return out

def is_trash(url):
    bad = ('logo','icon','avatar','banner','placeholder','wpcf7','rating','flag','payment','cropped','gravatar','-150x150','-100x100','-80x80')
    return any(x in url.lower() for x in bad)

def download_one(url, path):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200 and len(r.content) > 1000:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(r.content)
            return path
    except:
        pass
    return None

def prefer_large(urls):
    a, b, c = [], [], []
    for u in urls:
        lo = u.lower()
        if any(s in lo for s in ('1024x','800x','600x','large','-scaled')):
            a.append(u)
        elif any(s in lo for s in ('512x','400x','300x')):
            b.append(u)
        elif any(s in lo for s in ('150x','100x','thumb','icon','80x','64x')):
            c.append(u)
        else:
            b.append(u)
    return a + b + c

def extract_imgs(soup, base, filt):
    found = []
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original') or ''
        if not src: continue
        full = urljoin(base, src)
        if is_trash(full): continue
        if filt(full): found.append(full)
    for a in soup.find_all('a', href=True):
        href = a['href']
        if any(href.lower().endswith(e) for e in ('.jpg','.jpeg','.png','.webp')):
            full = urljoin(base, href)
            if is_trash(full): continue
            if filt(full): found.append(full)
    return found


# ============ NSK SCRAPER ============

def scrape_nsk(code, name):
    all_imgs = []

    # 1) nsk-dental.com official catalog
    if not hasattr(scrape_nsk, '_nsk_cat'):
        try:
            with open('nsk_official_catalog.json') as f:
                scrape_nsk._nsk_cat = json.load(f)
        except:
            scrape_nsk._nsk_cat = {}
    
    search_code = code.lower().replace('-','').replace(' ','')
    kw = set(re.findall(r'[a-z]+\d+|\d+[a-z]*|[a-z]{3,}', search_code))
    kw.discard('pro'); kw.discard('max'); kw.discard('led'); kw.discard('air')

    if scrape_nsk._nsk_cat and code:
        best, best_s = None, 0
        for path, info in scrape_nsk._nsk_cat.items():
            txt = info.get('text','').lower().replace('-','').replace(' ','')
            score = 0
            if search_code in txt: score += 50
            for k in kw:
                if k in txt: score += 10
            if score > best_s:
                best_s, best = score, path
        if best and best_s >= 50:
            for img_url in scrape_nsk._nsk_cat[best].get('images',[]):
                ic = img_url.lower().replace('-','').replace('_','')
                if any(k in ic for k in kw):
                    all_imgs.append(img_url)
    
    if all_imgs:
        return dedupe(all_imgs)[:8]

    # 2) fordent.ru catalog
    if not hasattr(scrape_nsk, '_ford_cat'):
        try:
            with open('nsk_fordent_catalog.json') as f:
                scrape_nsk._ford_cat = json.load(f)
        except:
            scrape_nsk._ford_cat = {}
    
    if scrape_nsk._ford_cat and code:
        for url, info in scrape_nsk._ford_cat.items():
            txt = info.get('text','').lower().replace('-','').replace(' ','')
            if search_code not in txt: continue
            for img_url in info.get('images',[]):
                ic = img_url.lower().replace('-','').replace('_','')
                if any(k in ic for k in kw):
                    all_imgs.append(img_url)
            if all_imgs: break

    if all_imgs:
        return dedupe(all_imgs)[:8]

    # 3) Live search on fordent.ru
    base = 'https://fordent.ru'
    terms = []
    if code:
        terms.append(code.strip())
        terms.append(code.replace('-',' ').strip())
    
    detail_url = None
    for term in terms[:2]:
        try:
            r = requests.get(f'{base}/search/?q={quote_plus(term)}', headers=HEADERS, timeout=TIMEOUT)
            if r.status_code != 200: continue
            s = BeautifulSoup(r.text, 'lxml')
            for card in s.find_all(class_='product-card'):
                a = card.find('a', href=True)
                if not a: continue
                ct = card.get_text(strip=True).lower().replace('-','').replace(' ','')
                if search_code in ct:
                    detail_url = urljoin(base, a['href'])
                    break
            if detail_url: break
        except: continue

    if detail_url:
        try:
            time.sleep(0.3)
            dr = requests.get(detail_url, headers=HEADERS, timeout=TIMEOUT)
            if dr.status_code == 200:
                ds = BeautifulSoup(dr.text, 'lxml')
                all_imgs.extend(extract_imgs(ds, base, lambda u: any(x in u for x in ('/upload/','/catalog/'))))
        except: pass

    return dedupe(all_imgs)[:8]


# ============ W&H SCRAPER ============

def scrape_wh(code, name):
    base = 'https://www.swallowdental.co.uk'
    all_imgs = []

    model_code = None
    if code:
        m = re.search(r'([A-Z]{2,3})[-\s]?(\d{2,3}[A-Z]*)', code, re.I)
        if m:
            model_code = (m.group(1)+m.group(2)).lower()

    search_terms = []
    if code:
        search_terms.append(code.strip().lower())
        search_terms.append(code.lower().replace(' ','-'))
    
    # Also extract from name
    raw = name.replace('W&H','').replace('W&H','').strip()
    nm = re.search(r'([A-Z]{2,3})\s*[-]?\s*(\d{2,3}[A-Z]*)', raw, re.I)
    if nm:
        t = f'{nm.group(1).lower()}-{nm.group(2).lower()}'
        if t not in search_terms:
            search_terms.append(t)

    detail_url = None
    for term in search_terms[:4]:
        try:
            r = requests.get(f'{base}/catalogsearch/result/?q={quote_plus(term)}', headers=HEADERS, timeout=TIMEOUT)
            if r.status_code != 200: continue
            s = BeautifulSoup(r.text, 'lxml')

            for item in s.select('.product-item-info'):
                it = item.get_text(strip=True).lower().replace('-','').replace(' ','')
                if model_code and model_code not in it: continue

                a_tag = item.find('a', href=True)
                if a_tag:
                    href = a_tag['href']
                    if '/catalog/product/' in href or href.endswith('.html'):
                        detail_url = urljoin(base, href)

                for img in item.find_all('img'):
                    src = img.get('src') or img.get('data-src') or ''
                    if not src: continue
                    full = urljoin(base, src)
                    if '/media/catalog/product' in full and not is_trash(full):
                        all_imgs.append(full)

            if detail_url or all_imgs: break
        except: continue

    if detail_url:
        try:
            time.sleep(0.3)
            dr = requests.get(detail_url, headers=HEADERS, timeout=TIMEOUT)
            if dr.status_code == 200:
                ds = BeautifulSoup(dr.text, 'lxml')
                all_imgs.extend(extract_imgs(ds, base, lambda u: '/media/catalog/product' in u))
        except: pass

    result = dedupe(all_imgs)
    result = prefer_large(result)
    return result[:8]


# ============ MAIN ============

def main():
    with open('image_mapping.json') as f:
        mapping = json.load(f)

    todo = []
    for pid, info in mapping.items():
        brand = pid.split('_')[0].upper()
        if brand == 'COXO':
            continue
        d = f'images/{pid}'
        files = glob.glob(f'{d}/*') if os.path.isdir(d) else []
        if len(files) >= 3:
            continue
        todo.append((pid, info))

    print(f'Missing products to scrape: {len(todo)}')
    scraper = {'NSK': scrape_nsk, 'WH': scrape_wh}

    ok = 0
    for i, (pid, info) in enumerate(todo, 1):
        brand = pid.split('_')[0].upper()
        name = info.get('name','')
        code = info.get('code','')
        fn = scraper.get(brand)
        if not fn:
            print(f'  [{i}/{len(todo)}] {name} — unknown brand {brand}')
            continue

        print(f'[{i}/{len(todo)}] {name} ...', end=' ', flush=True)
        urls = fn(code, name)
        if not urls:
            print('0 images')
            mapping[pid]['images'] = []
            time.sleep(0.2)
            continue

        print(f'{len(urls)} urls ...', end=' ', flush=True)
        saved = []
        for j, url in enumerate(urls, 1):
            ext = 'png' if '.png' in url.lower() else 'jpg'
            path = os.path.join(OUTPUT, pid, f'{j}.{ext}')
            if download_one(url, path):
                saved.append(path)
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

    print(f'\nDone: {ok}/{len(todo)} scraped with 3+ images')

if __name__ == '__main__':
    main()
