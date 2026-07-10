#!/usr/bin/env python3
# scraper_bot.py - دریافت ۳+ تصویر برای هر محصول از سایت‌های مرجع

import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

HEADERS_COXO = {
    'User-Agent': 'curl/8.0',
    'Accept': 'text/html,application/xhtml+xml',
}

HEADERS_DEFAULT = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,fa;q=0.8',
}

OUTPUT_DIR = 'images'
MIN_IMAGES = 3
MAX_IMAGES = 8
TIMEOUT = 15


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text


def download_image(url, save_path):
    try:
        resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=TIMEOUT)
        if resp.status_code == 200 and len(resp.content) > 1000:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            return save_path
    except requests.RequestException:
        pass
    return None


def normalize_url(url, base_url):
    url = urljoin(base_url, url) if not url.startswith('http') else url
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def deduplicate(urls):
    seen = set()
    unique = []
    for u in urls:
        k = u.split('?')[0].rstrip('/')
        if k not in seen:
            seen.add(k)
            unique.append(u)
    return unique


def prefer_large_images(urls):
    pref = []
    rest = []
    for u in urls:
        lower = u.lower()
        if '512x512' in lower or '1024x1024' in lower or '800x800' in lower or 'large' in lower:
            pref.append(u)
        elif '280x280' in lower or '150x150' in lower or 'thumb' in lower or '100x100' in lower:
            rest.append(u)
        else:
            pref.append(u)
    return pref + rest


def is_logo_or_icon(url):
    lower = url.lower()
    bad = ['logo', 'icon', 'favicon', 'avatar', 'banner', 'placeholder']
    return any(kw in lower for kw in bad)


def get_coxo_images(name, code):
    session = requests.Session()
    session.headers.update(HEADERS_COXO)

    base = 'https://coxotec.com'
    all_images = []

    slug = slugify(name.replace('COXO', '').strip())
    code_slug = slugify(code) if code else ''

    candidates = []
    if code_slug:
        candidates.append(f'{base}/product/{code_slug}/')
    candidates.append(f'{base}/product/{slug}/')
    candidates.append(f'{base}/en/product/{slug}/')

    for url in candidates:
        try:
            time.sleep(1)
            resp = session.get(url, timeout=TIMEOUT)
            if resp.status_code != 200 or len(resp.text) < 1000:
                continue

            soup = BeautifulSoup(resp.text, 'lxml')

            og = soup.find('meta', property='og:image')
            if og and og.get('content'):
                all_images.append(urljoin(url, og['content']))

            img_sources = set()
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or ''
                if not src:
                    continue
                full = urljoin(url, src)
                if is_logo_or_icon(full):
                    continue
                if 'wp-content/uploads' in full:
                    all_images.append(full)
                    img_sources.add(full)

            for a in soup.find_all('a', href=True):
                href = a['href']
                if any(href.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    full = urljoin(url, href)
                    if 'wp-content' in full and not is_logo_or_icon(full):
                        all_images.append(full)

        except requests.RequestException:
            continue

        if len(all_images) >= MIN_IMAGES:
            break

    result = deduplicate(all_images)
    result = prefer_large_images(result)
    return result[:MAX_IMAGES]


def get_nsk_images(name, code):
    base = 'https://fordent.ru'
    query = code or slugify(name.replace('NSK', '').strip())
    all_images = []
    detail_pages = []

    search_url = f'{base}/search/?q={query}'
    try:
        resp = requests.get(search_url, headers=HEADERS_DEFAULT, timeout=TIMEOUT)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, 'lxml')

        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True).lower()
            if ('/products/' in href or '/product/' in href) and not href.startswith('#'):
                if any(w in href.lower() for w in query.lower().replace('-', '_').split('_')):
                    full = urljoin(base, href)
                    if full not in detail_pages:
                        detail_pages.append(full)

        if not detail_pages:
            for a in soup.find_all('a', href=True):
                href = a['href']
                if ('/products/' in href or '/product/' in href) and 'nsk' in href.lower():
                    full = urljoin(base, href)
                    if full not in detail_pages:
                        detail_pages.append(full)

        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            if not src:
                continue
            full = urljoin(base, src)
            if is_logo_or_icon(full):
                continue
            if '/upload/' in full or '/catalog/' in full:
                all_images.append(full)

        for detail_url in detail_pages[:2]:
            try:
                dr = requests.get(detail_url, headers=HEADERS_DEFAULT, timeout=TIMEOUT)
                if dr.status_code != 200:
                    continue
                ds = BeautifulSoup(dr.text, 'lxml')
                for img in ds.find_all('img'):
                    src = img.get('src') or img.get('data-src') or ''
                    if not src:
                        continue
                    full = urljoin(base, src)
                    if is_logo_or_icon(full):
                        continue
                    if '/upload/' in full or '/catalog/' in full:
                        all_images.append(full)
            except requests.RequestException:
                continue

    except requests.RequestException:
        return []

    result = deduplicate(all_images)
    return result[:MAX_IMAGES]


def get_wh_images(name, code):
    base = 'https://www.swallowdental.co.uk'
    query = code or slugify(name.replace('W&H', '').replace('WH-', '').strip())
    all_images = []
    detail_pages = []

    search_url = f'{base}/catalogsearch/result/?q={query}'
    try:
        resp = requests.get(search_url, headers=HEADERS_DEFAULT, timeout=TIMEOUT)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, 'lxml')

        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            if not src:
                continue
            full = urljoin(base, src)
            if is_logo_or_icon(full):
                continue
            if '/media/catalog/product' in full:
                all_images.append(full)

        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.endswith('.html') or '/catalog/product/' in href:
                full = urljoin(base, href)
                if full not in detail_pages:
                    detail_pages.append(full)

        for detail_url in detail_pages[:3]:
            try:
                dr = requests.get(detail_url, headers=HEADERS_DEFAULT, timeout=TIMEOUT)
                if dr.status_code != 200:
                    continue
                ds = BeautifulSoup(dr.text, 'lxml')
                for img in ds.find_all('img'):
                    src = img.get('src') or img.get('data-src') or ''
                    if not src:
                        continue
                    full = urljoin(base, src)
                    if is_logo_or_icon(full):
                        continue
                    if '/media/catalog/product' in full:
                        all_images.append(full)
            except requests.RequestException:
                continue

    except requests.RequestException:
        return []

    result = deduplicate(all_images)
    return result[:MAX_IMAGES]


def main():
    try:
        with open('products.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
    except FileNotFoundError:
        print('products.json not found! Run generate_products.py first.')
        return

    mapping = {}
    if os.path.exists('image_mapping.json'):
        try:
            with open('image_mapping.json', 'r', encoding='utf-8') as f:
                mapping = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    total = len(products)
    print(f'Scraping images for {total} products (target: {MIN_IMAGES}-{MAX_IMAGES} each)\n')

    scrapers = {'COXO': get_coxo_images, 'NSK': get_nsk_images, 'W&H': get_wh_images}

    for idx, p in enumerate(products, 1):
        brand = p.get('brand', '')
        name = p.get('name', '')
        code = p.get('code', '')
        pid = p.get('id', '')

        if pid in mapping and mapping[pid].get('images') and len(mapping[pid]['images']) >= MIN_IMAGES:
            print(f'[{idx}/{total}] {name} - already has {len(mapping[pid]["images"])} images, skipping')
            continue

        scraper = scrapers.get(brand)
        if not scraper:
            print(f'[{idx}/{total}] {name} - unknown brand: {brand}')
            continue

        print(f'[{idx}/{total}] {brand} {name}')

        image_urls = scraper(name, code)
        if not image_urls:
            print(f'  No images found')
            time.sleep(0.5)
            continue

        print(f'  Found {len(image_urls)} image URLs, downloading...')

        saved_paths = []
        img_dir = os.path.join(OUTPUT_DIR, pid)
        download_failed = False

        for i, img_url in enumerate(image_urls, 1):
            ext = 'jpg'
            lu = img_url.lower()
            if '.png' in lu:
                ext = 'png'
            elif '.webp' in lu:
                ext = 'webp'
            local = os.path.join(img_dir, f'{i}.{ext}')
            result = download_image(img_url, local)
            if result:
                saved_paths.append(result)
                print(f'    [{len(saved_paths)}] saved: {os.path.relpath(result)}')
            else:
                download_failed = True
            time.sleep(0.3)

        if not saved_paths and image_urls:
            mapping[pid] = {
                'name': name,
                'brand': brand,
                'images': image_urls,
                'source_urls': image_urls,
                'note': 'images not downloadable, using source URLs directly'
            }
            print(f'    Using {len(image_urls)} source URLs directly (download blocked)')
        elif saved_paths:
            mapping[pid] = {
                'name': name,
                'brand': brand,
                'images': saved_paths,
                'source_urls': image_urls
            }

        with open('image_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        time.sleep(1.5)

    successful = sum(1 for v in mapping.values() if v.get('images') and len(v['images']) >= MIN_IMAGES)
    print(f'\nDone. {successful}/{total} products have {MIN_IMAGES}+ images.')
    print(f'Images: {OUTPUT_DIR}/')
    print(f'Mapping: image_mapping.json')


if __name__ == '__main__':
    main()
