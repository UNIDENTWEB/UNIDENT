#!/usr/bin/env python3
"""scraper_bot.py - جستجوی هوشمند و دریافت تصاویر محصولات از سایت‌های مرجع

برای هر محصول، بر اساس کد و نام، در سایت مرجع برند جستجو می‌کند و
دقیق‌ترین صفحه محصول را پیدا کرده، تصاویر را استخراج و دانلود می‌کند.

سایت‌های مرجع:
  COXO -> jmudental.com (Shopify API)
  NSK  -> fordent.ru
  W&H  -> swallowdental.co.uk
"""

import json
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote_plus

# ---------- Config ----------
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8,fa;q=0.7',
}

OUTPUT_DIR = 'images'
MIN_IMAGES = 3
MAX_IMAGES = 8
TIMEOUT = 15
REQUEST_DELAY = 1.0

# ---------- Helpers ----------

def slugify(text):
    t = text.lower().strip()
    t = re.sub(r'[^\w\s-]', '', t)
    t = re.sub(r'[\s_]+', '-', t)
    return t.strip('-')


def download_image(url, save_path, headers=None):
    if headers is None:
        headers = HEADERS
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        if resp.status_code == 200 and len(resp.content) > 1000:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            return save_path
    except requests.RequestException:
        pass
    return None


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
    large = []
    medium = []
    small = []
    for u in urls:
        lo = u.lower()
        if any(s in lo for s in ('1024x1024', '800x800', '600x600', 'large', '-scaled')):
            large.append(u)
        elif any(s in lo for s in ('512x512', '400x400', '300x300')):
            medium.append(u)
        elif any(s in lo for s in ('150x150', '100x100', 'thumb', 'icon', '80x80', '64x64')):
            small.append(u)
        else:
            medium.append(u)
    return large + medium + small


def is_logo_or_icon(url):
    lo = url.lower()
    bad = ('logo', 'icon', 'favicon', 'avatar', 'banner', 'placeholder',
           'screenshot', 'cropped-', 'wpcf7', 'rating', 'flag', 'payment')
    return any(kw in lo for kw in bad)


def extract_page_images(soup, base_url, path_filter):
    """Extract all images from soup, filtered by path_filter and not logo/icon."""
    found = []
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original') or ''
        if not src:
            continue
        full = urljoin(base_url, src)
        if is_logo_or_icon(full):
            continue
        if path_filter(full):
            found.append(full)
    return found


def extract_og_image(soup, base_url):
    og = soup.find('meta', property='og:image')
    if og and og.get('content'):
        return urljoin(base_url, og['content'])
    return None


def extract_link_images(soup, base_url, path_filter):
    """Extract images from <a href> links, e.g. gallery links."""
    found = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if any(href.lower().endswith(e) for e in ('.jpg', '.jpeg', '.png', '.webp')):
            full = urljoin(base_url, href)
            if is_logo_or_icon(full):
                continue
            if path_filter(full):
                found.append(full)
    return found


# ---------- Brand-Specific Scrapers ----------

def scrape_coxo(name, code):
    """اسکرپر COXO — از کاتالوگ محلی jmudental.com (products.json)
    
    کاتالوگ یکبار از Shopify API دانلود شده و در فایل coxo_catalog.json ذخیره شده.
    تطابق بر اساس کد مدل با scoring دقیق انجام می‌شود.
    """
    raw_name = name.replace('COXO', '').strip()
    model = code or raw_name

    # Load catalog once
    if not hasattr(scrape_coxo, '_catalog'):
        try:
            with open('coxo_catalog.json') as f:
                scrape_coxo._catalog = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            scrape_coxo._catalog = {}
        # Build index for each catalog entry
        scrape_coxo._index = {}
        for handle, info in scrape_coxo._catalog.items():
            codes = set()
            for m in re.finditer(r'(cx\d+[a-z]*-?\d*|c\d+-?\d+[a-z]*|db\d+|dl-?\d+|c-\w+|c\s*\d+)', handle, re.I):
                codes.add(re.sub(r'[-\s]', '', m.group(0).upper()))
            for m in re.finditer(r'(CX\d+[A-Z]*-?\d*|C\d+-?\d+[A-Z]*|DB\d+|DL-?\d+)', info['title']):
                codes.add(re.sub(r'[-\s]', '', m.group(0).upper()))
            scrape_coxo._index[handle] = codes

    if not scrape_coxo._catalog:
        return []

    # Match our product against catalog
    search_code = model.upper().replace('-', '').replace(' ', '')
    search_name = raw_name.upper()
    
    best_handle = None
    best_score = 0
    
    for handle, chandles in scrape_coxo._index.items():
        score = 0
        for hc in chandles:
            if hc and search_code and hc in search_code:
                score += 20
            elif hc and search_code and search_code in hc:
                score += 15
        
        title = scrape_coxo._catalog[handle]['title'].upper()
        product_words = set(search_name.split())
        title_words = set(title.split())
        common = product_words & title_words - {'COXO', 'DENTAL', 'HAND', 'WITH', 'AND', 'FOR', 'THE', 'OF', 'IN', 'TO', 'A'}
        score += len(common) * 5
        
        if score > best_score:
            best_score = score
            best_handle = handle

    # Only return if confident (code match required)
    if best_handle and best_score >= 20:
        return scrape_coxo._catalog[best_handle]['images'][:MAX_IMAGES]

    return []


def scrape_nsk(name, code):
    """اسکرپر NSK از fordent.ru

    در fordent.ru/search/?q= جستجو می‌کند، نتایج را بر اساس کد/نام امتیازدهی
    می‌کند و از بهترین صفحه محصول جزئیات، تصاویر را استخراج می‌کند.
    """
    base = 'https://fordent.ru'
    all_images = []

    # کلمات جستجو: کد محصول مهمترین است
    search_terms = []
    if code:
        search_terms.append(code.strip())
    raw = name.replace('NSK', '').strip()
    # استخراج مدل از نام
    model_match = re.search(r'(?:Ti-Max|S-Max|Varios|Pana-Max|FX|Z\d+|M\d+)[^\s,]*', raw, re.I)
    if model_match:
        search_terms.append(model_match.group(0))
    search_terms.append(slugify(raw))

    detail_pages = []

    for term in search_terms[:2]:  # حداکثر ۲ جستجو
        try:
            search_url = f'{base}/search/?q={quote_plus(term)}'
            resp = requests.get(search_url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'lxml')

            # فقط از صفحات جزئیات محصول تصویر بگیر (نه از thumbnails صفحه جستجو)
            # thumbnailهای صفحه جستجو برای محصولات مختلف تکراری هستند

            # پیدا کردن لینک‌های صفحه محصول با امتیازدهی سختگیرانه
            scored = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text(strip=True).lower()
                href_lower = href.lower()

                if not ('/products/' in href_lower or '/product/' in href_lower):
                    continue
                if href.startswith('#'):
                    continue

                score = 0
                # امتیاز برای تطابق با کد (مهمترین)
                if code and code.lower() in href_lower:
                    score += 15
                if code and code.lower() in text:
                    score += 10

                # امتیاز برای تطابق با نام محصول
                model_parts = term.lower().replace('-', ' ').split()
                for word in model_parts:
                    if len(word) < 2:
                        continue
                    if word in href_lower:
                        score += 5
                    if word in text:
                        score += 3

                # امتیاز برای کلمه nsk
                if 'nsk' in href_lower or 'nsk' in text:
                    score += 2

                # فقط لینک‌های با امتیاز بالا قبول می‌شوند (حداقل یک تطابق کد یا مدل)
                if score >= 5:
                    full = urljoin(base, href)
                    scored.append((score, full))

            scored.sort(key=lambda x: x[0], reverse=True)
            for _, url in scored:
                if url not in detail_pages:
                    detail_pages.append(url)

            if detail_pages:
                break  # جستجوی اول نتیجه داد

        except requests.RequestException:
            continue

    # دنبال کردن صفحات جزئیات (بهترین امتیازها اول)
    for detail_url in detail_pages[:3]:
        try:
            time.sleep(0.5)
            dr = requests.get(detail_url, headers=HEADERS, timeout=TIMEOUT)
            if dr.status_code != 200:
                continue
            ds = BeautifulSoup(dr.text, 'lxml')

            all_images.extend(extract_page_images(
                ds, base,
                lambda u: '/upload/' in u or '/catalog/' in u
            ))

            all_images.extend(extract_link_images(
                ds, base,
                lambda u: '/upload/' in u or '/catalog/' in u
            ))

        except requests.RequestException:
            continue

    result = deduplicate(all_images)
    result = prefer_large_images(result)
    return result[:MAX_IMAGES]


def scrape_wh(name, code):
    """اسکرپر W&H از swallowdental.co.uk

    در swallowdental.co.uk/catalogsearch/result/?q= جستجو می‌کند.
    """
    base = 'https://www.swallowdental.co.uk'
    all_images = []
    detail_pages = []

    # کلمات جستجو
    search_terms = []
    if code:
        search_terms.append(code.strip())
    raw = name.replace('W&H', '').replace('WH-', '').strip()
    search_terms.append(slugify(raw))
    # حذف کلمات اضافی
    clean = re.sub(r'\b(synea|vision|alegra|handpiece|set)\b', '', raw, flags=re.I).strip()
    if clean and slugify(clean) not in search_terms:
        search_terms.append(slugify(clean))

    for term in search_terms[:2]:
        try:
            search_url = f'{base}/catalogsearch/result/?q={quote_plus(term)}'
            resp = requests.get(search_url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, 'lxml')

            # تصاویر از نتایج جستجو — فقط اگر با نام/کد محصول تطابق داشته باشند
            raw_code = code.strip().lower() if code else ''
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or ''
                if not src:
                    continue
                full = urljoin(base, src)
                if '/media/catalog/product' not in full:
                    continue
                if is_logo_or_icon(full):
                    continue
                # فقط تصاویری که در alt یا parent anchor با نام محصول تطابق دارند
                alt = (img.get('alt') or '').lower()
                parent_text = ''
                parent_a = img.find_parent('a')
                if parent_a:
                    parent_text = parent_a.get_text(strip=True).lower()
                product_text = alt + ' ' + parent_text
                name_lower = raw.lower()
                if (raw_code and raw_code in product_text) or \
                   any(w in product_text for w in name_lower.split() if len(w) > 3):
                    all_images.append(full)

            # لینک صفحات جزئیات
            for a in soup.find_all('a', href=True):
                href = a['href']
                href_lower = href.lower()
                if '/catalog/product/' in href_lower or href_lower.endswith('.html'):
                    full = urljoin(base, href)
                    if full not in detail_pages:
                        detail_pages.append(full)

            # لینک‌های دسته‌بندی
            for a in soup.find_all('a', href=True):
                href = a['href']
                href_lower = href.lower()
                term_lower = term.lower()
                if '/catalog/category/' in href_lower and any(
                    w in href_lower for w in term_lower.replace('-', ' ').split()
                ):
                    full = urljoin(base, href)
                    if full not in detail_pages:
                        detail_pages.append(full)

            if detail_pages or all_images:
                break

        except requests.RequestException:
            continue

    # صفحات جزئیات
    for detail_url in detail_pages[:3]:
        try:
            time.sleep(0.5)
            dr = requests.get(detail_url, headers=HEADERS, timeout=TIMEOUT)
            if dr.status_code != 200:
                continue
            ds = BeautifulSoup(dr.text, 'lxml')

            all_images.extend(extract_page_images(
                ds, base,
                lambda u: '/media/catalog/product' in u
            ))

            all_images.extend(extract_link_images(
                ds, base,
                lambda u: '/media/catalog/product' in u
            ))

        except requests.RequestException:
            continue

    result = deduplicate(all_images)
    result = prefer_large_images(result)
    return result[:MAX_IMAGES]


# ---------- Main ----------

SCRAPERS = {
    'COXO': scrape_coxo,
    'NSK': scrape_nsk,
    'W&H': scrape_wh,
}


def main():
    try:
        with open('products.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
    except FileNotFoundError:
        print('[ERROR] products.json not found! Run generate_products.py first.')
        return

    mapping = {}
    if os.path.exists('image_mapping.json'):
        try:
            with open('image_mapping.json', 'r', encoding='utf-8') as f:
                mapping = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    total = len(products)
    print(f'Scraping images for {total} products')
    print(f'Target: {MIN_IMAGES}-{MAX_IMAGES} images each')
    print(f'Reference sites: COXO=jmudental.com, NSK=fordent.ru, W&H=swallowdental.co.uk')
    print('=' * 60)
    print()

    success_count = 0
    for idx, p in enumerate(products, 1):
        brand = p.get('brand', '')
        name = p.get('name', '')
        code = p.get('code', '')
        pid = p.get('id', '')

        scraper = SCRAPERS.get(brand)
        if not scraper:
            print(f'[{idx}/{total}] {name} — unknown brand: {brand}')
            continue

        # Skip if already has enough images — but still update metadata
        if pid in mapping:
            existing = mapping[pid].get('images', [])
            if existing and len(existing) >= MIN_IMAGES:
                count = len(existing)
                # Update name/brand/code in case they're missing from previous runs
                if not mapping[pid].get('name'):
                    mapping[pid]['name'] = name
                    mapping[pid]['brand'] = brand
                    mapping[pid]['code'] = code
                print(f'[{idx}/{total}] {name} — has {count} images, skipping')
                success_count += 1
                continue

        print(f'[{idx}/{total}] {name} (code: {code})', end='', flush=True)

        try:
            image_urls = scraper(name, code)
        except Exception as e:
            print(f'  ERROR: {e}')
            time.sleep(REQUEST_DELAY)
            continue

        if not image_urls:
            print(f'  [0 images found]')
            if pid not in mapping or not mapping[pid].get('images'):
                mapping[pid] = {
                    'name': name,
                    'brand': brand,
                    'code': code,
                    'images': [],
                    'source_urls': [],
                }
            time.sleep(REQUEST_DELAY)
            continue

        print(f'  -> {len(image_urls)} images', end='', flush=True)
        saved_paths = []
        img_dir = os.path.join(OUTPUT_DIR, pid)

        for i, img_url in enumerate(image_urls, 1):
            ext = 'jpg'
            lu = img_url.lower()
            if '.png' in lu:
                ext = 'png'
            elif '.webp' in lu:
                ext = 'webp'
            elif '.gif' in lu:
                ext = 'gif'

            local = os.path.join(img_dir, f'{i}.{ext}')
            result = download_image(img_url, local)
            if result:
                saved_paths.append(result)
            time.sleep(0.3)

        if saved_paths:
            mapping[pid] = {
                'name': name,
                'brand': brand,
                'code': code,
                'images': saved_paths,
                'source_urls': image_urls,
            }
            print(f'  [{len(saved_paths)} saved]')
            if len(saved_paths) >= MIN_IMAGES:
                success_count += 1
        else:
            mapping[pid] = {
                'name': name,
                'brand': brand,
                'code': code,
                'images': [],
                'source_urls': image_urls,
            }
            print(f'  [download failed]')

        with open('image_mapping.json', 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        time.sleep(REQUEST_DELAY)

    print()
    print('=' * 60)
    print(f'Done: {success_count}/{total} products have {MIN_IMAGES}+ images')
    print(f'Mapping: image_mapping.json ({len(mapping)} entries)')
    print(f'Images: {OUTPUT_DIR}/')


if __name__ == '__main__':
    main()
