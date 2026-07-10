#!/usr/bin/env python3
"""scraper_bot.py - جستجوی هوشمند و دریافت تصاویر محصولات از سایت‌های مرجع

برای هر محصول، بر اساس کد و نام، در سایت مرجع برند جستجو می‌کند و
دقیق‌ترین صفحه محصول را پیدا کرده، تصاویر را استخراج و دانلود می‌کند.

سایت‌های مرجع:
  COXO -> coxotec.com
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

HEADERS_CURL = {
    'User-Agent': 'curl/8.0',
    'Accept': 'text/html,application/xhtml+xml',
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
    """اسکرپر COXO - جستجوی Bing Images (منبع اصلی مسدود است)

    coxotec.com توسط CDN SiteGround مسدود شده است. از موتور جستجوی
    تصاویر Bing برای یافتن تصاویر محصولات COXO استفاده می‌کند.
    """
    all_images = []

    raw_name = name.replace('COXO', '').strip()
    model = code or raw_name

    # چندین جستجوی مختلف
    queries = [
        f'COXO {model} dental equipment product',
        f'"COXO {model}"',
        f'COXO {raw_name} product photo',
        f'COXO dental {model}',
    ]

    for query in queries:
        if len(all_images) >= MAX_IMAGES:
            break
        try:
            imgs = _bing_image_search(query, count=20)
            if imgs:
                # امتیازدهی نرم‌تر — فقط تصاویر خیلی نامربوط فیلتر می‌شوند
                scored = []
                for u in imgs:
                    s = 1  # امتیاز پایه
                    ul = u.lower()
                    # امتیاز مثبت
                    for kw in ('coxo', 'dental', 'handpiece', 'motor', 'medical', 'product', 'equipment'):
                        if kw in ul:
                            s += 3
                    for kw in ('600x600', '800x800', 'large', '1024', '2048', 'original'):
                        if kw in ul:
                            s += 2
                    # امتیاز منفی
                    for kw in ('icon', 'logo', 'avatar', 'favicon', 'thumb', '150x150', '80x80', '64x64',
                               'sprite', 'pixel', 'transparent', 'banner', 'screenshot', 'watermark'):
                        if kw in ul:
                            s -= 3
                    scored.append((s, u))

                scored.sort(key=lambda x: x[0], reverse=True)
                # قبول تصاویر با امتیاز >= 0 (قبلا فقط > 0)
                all_images.extend([u for _, u in scored if _ >= 0])
        except Exception:
            continue

    result = deduplicate(all_images)
    result = [u for u in result if not is_logo_or_icon(u)]
    result = prefer_large_images(result)
    return result[:MAX_IMAGES]


def _bing_image_search(query, count=16):
    """جستجوی Bing Images و استخراج URL تصاویر"""
    import html as html_mod
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    url = f'https://www.bing.com/images/search?q={quote_plus(query)}&first=1'
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT)
        if resp.status_code != 200:
            return []

        all_urls = set()
        for m in re.finditer(r'murl&quot;:&quot;(.+?)&quot;', resp.text):
            raw = m.group(1)
            clean = html_mod.unescape(raw)
            clean = clean.replace('\\u002f', '/').replace('\\u003a', ':').replace('\\/', '/')
            if clean.startswith('http') and len(clean) < 400:
                all_urls.add(clean)

        skip_domains = ('google.com', 'gstatic.com', 'bing.com', 'microsoft.com',
                        'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com')
        valid = []
        for u in all_urls:
            if any(d in u.lower() for d in skip_domains):
                continue
            if 'icon' in u.lower() or 'logo' in u.lower() or 'avatar' in u.lower():
                continue
            valid.append(u)

        return valid[:count]
    except Exception:
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

            # استخراج تصاویر از نتایج جستجو (thumbnails)
            all_images.extend(extract_page_images(
                soup, base,
                lambda u: '/upload/' in u or '/catalog/' in u
            ))

            # پیدا کردن لینک‌های صفحه محصول با امتیازدهی
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
                # امتیاز برای تطابق با کد
                if code and code.lower() in href_lower:
                    score += 10
                if code and code.lower() in text:
                    score += 8

                # امتیاز برای تطابق با نام
                for word in term.lower().replace('-', ' ').split():
                    if word in href_lower:
                        score += 3
                    if word in text:
                        score += 2

                # امتیاز برای کلمه nsk
                if 'nsk' in href_lower or 'nsk' in text:
                    score += 1

                if score > 0:
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

            # تصاویر از نتایج جستجو
            all_images.extend(extract_page_images(
                soup, base,
                lambda u: '/media/catalog/product' in u
            ))

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
    print(f'Reference sites: COXO=coxotec.com, NSK=fordent.ru, W&H=swallowdental.co.uk')
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

        # Skip if already has enough images
        if pid in mapping:
            existing = mapping[pid].get('images', [])
            if existing and len(existing) >= MIN_IMAGES:
                count = len(existing)
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
                'images': image_urls,
                'source_urls': image_urls,
                'note': 'download blocked, using source URLs',
            }
            print(f'  [urls only, download blocked]')

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
