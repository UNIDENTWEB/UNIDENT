#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 ربات اسکرپر تصاویر محصولات دندانپزشکی - نسخه پیشرفته
✅ پشتیبانی از COXO, NSK, W&H
✅ مدیریت خطا و retry
✅ User-Agent تصادفی
✅ ذخیره تصاویر در پوشه images/ و تولید image_mapping.json
"""

import os
import json
import time
import re
import random
from urllib.parse import urljoin, quote
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# ============================================================
#  تنظیمات
# ============================================================
CONFIG = {
    'PRODUCTS_FILE': 'products.json',
    'OUTPUT_DIR': 'images',
    'MAPPING_FILE': 'image_mapping.json',
    'MIN_IMAGES': 2,
    'MAX_IMAGES': 5,
    'DELAY': 1.5,
    'RETRY_COUNT': 3,
    'TIMEOUT': 20
}

# ============================================================
#  کلاس اصلی ربات
# ============================================================
class DentalImageScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.ua.random})
        self.products = []
        self.mapping = {}
        self.load_products()
        self.load_mapping()
        os.makedirs(CONFIG['OUTPUT_DIR'], exist_ok=True)
        print(f"🔹 ربات راه‌اندازی شد | {len(self.products)} محصول")

    def load_products(self):
        try:
            with open(CONFIG['PRODUCTS_FILE'], 'r', encoding='utf-8') as f:
                self.products = json.load(f)
        except FileNotFoundError:
            print("❌ products.json یافت نشد! نمونه ساخته شد.")
            self.create_sample_products()

    def create_sample_products(self):
        sample = []
        for i in range(10):
            sample.append({
                'id': f'coxo_{i+1}',
                'name': f'COXO CX207-{chr(65+i)}',
                'brand': 'COXO',
                'code': f'CX207-{chr(65+i)}'
            })
        with open(CONFIG['PRODUCTS_FILE'], 'w', encoding='utf-8') as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)
        self.products = sample

    def load_mapping(self):
        try:
            with open(CONFIG['MAPPING_FILE'], 'r', encoding='utf-8') as f:
                self.mapping = json.load(f)
        except:
            self.mapping = {}

    def get_headers(self):
        return {'User-Agent': self.ua.random}

    def fetch_with_retry(self, url, method='GET', **kwargs):
        for attempt in range(CONFIG['RETRY_COUNT']):
            try:
                headers = self.get_headers()
                if 'headers' in kwargs:
                    headers.update(kwargs['headers'])
                kwargs['headers'] = headers
                kwargs['timeout'] = CONFIG['TIMEOUT']
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 200:
                    return response
            except Exception as e:
                print(f"   ⚠️ تلاش {attempt+1} ناموفق: {e}")
                time.sleep(2 ** attempt)
        return None

    def extract_images_from_html(self, html, base_url):
        """استخراج تصاویر از HTML با اولویت‌بندی"""
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'lxml')
        images = []
        seen = set()

        # 1. متا og:image (معمولاً بهترین کیفیت)
        og = soup.find('meta', property='og:image')
        if og and og.get('content'):
            img_url = self.normalize_url(og['content'], base_url)
            if img_url and img_url not in seen:
                seen.add(img_url)
                images.append(img_url)

        # 2. متا twitter:image
        twitter = soup.find('meta', attrs={'name': 'twitter:image'})
        if twitter and twitter.get('content'):
            img_url = self.normalize_url(twitter['content'], base_url)
            if img_url and img_url not in seen:
                seen.add(img_url)
                images.append(img_url)

        # 3. تصاویر داخل المنت‌های اصلی
        for selector in ['.product-image img', '.product-gallery img', '.product-photo img', '.main-image img', '.image img']:
            for img in soup.select(selector):
                src = img.get('src') or img.get('data-src')
                if src:
                    img_url = self.normalize_url(src, base_url)
                    if img_url and img_url not in seen and self.is_image_url(img_url):
                        seen.add(img_url)
                        images.append(img_url)

        # 4. تصاویر با کلاس‌های خاص
        for img in soup.find_all('img', class_=re.compile(r'(product|main|gallery|photo|image|slide)')):
            src = img.get('src') or img.get('data-src')
            if src:
                img_url = self.normalize_url(src, base_url)
                if img_url and img_url not in seen and self.is_image_url(img_url):
                    seen.add(img_url)
                    images.append(img_url)

        # 5. تمام تصاویر با پسوند مناسب
        for img in soup.find_all('img', src=True):
            src = img['src']
            img_url = self.normalize_url(src, base_url)
            if img_url and self.is_image_url(img_url) and not self.is_excluded(img_url):
                if img_url not in seen:
                    seen.add(img_url)
                    images.append(img_url)

        return images[:CONFIG['MAX_IMAGES'] * 2]  # بیشتر برای فیلتر نهایی

    def normalize_url(self, url, base_url):
        if not url:
            return None
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = urljoin(base_url, url)
        elif not url.startswith(('http://', 'https://')):
            url = urljoin(base_url, url)
        # حذف پارامترهای اضافی
        return re.sub(r'\?.*$', '', url)

    def is_image_url(self, url):
        return bool(re.search(r'\.(jpg|jpeg|png|webp|gif|svg)', url, re.I))

    def is_excluded(self, url):
        excluded = ['logo', 'icon', 'thumb', 'small', 'banner', 'placeholder', 'no-image', 'default']
        return any(x in url.lower() for x in excluded)

    # ============================================================
    #  جستجوی اختصاصی هر برند
    # ============================================================

    def search_coxo(self, product):
        name = product.get('name', '')
        code = product.get('code', '')
        base = 'https://coxotec.com'
        
        # تولید slug از نام
        slug = re.sub(r'[^\w\-]', '', name.lower().replace(' ', '-'))
        
        urls = [
            f"{base}/product/{slug}/",
            f"{base}/product/{slug}-handpiece/",
            f"{base}/en/product/{slug}/",
            f"{base}/search/?q={quote(code)}"
        ]
        
        all_images = []
        for url in urls:
            resp = self.fetch_with_retry(url)
            if resp and resp.status_code == 200:
                images = self.extract_images_from_html(resp.text, base)
                all_images.extend(images)
                if len(all_images) >= CONFIG['MAX_IMAGES']:
                    break
            time.sleep(0.3)
        
        return list(dict.fromkeys(all_images))[:CONFIG['MAX_IMAGES']]

    def search_nsk(self, product):
        name = product.get('name', '')
        code = product.get('code', '')
        base = 'https://fordent.ru'
        query = code if code else name
        
        # جستجو در fordent.ru
        search_url = f"{base}/search/?q={quote(query)}"
        resp = self.fetch_with_retry(search_url)
        if not resp:
            return []
        
        soup = BeautifulSoup(resp.text, 'lxml')
        images = []
        
        # استخراج تصاویر از نتایج جستجو
        for img in soup.find_all('img', src=True):
            src = img['src']
            if '/catalog/product/' in src:
                img_url = self.normalize_url(src, base)
                if img_url and self.is_image_url(img_url):
                    images.append(img_url)
        
        # اگر تصویری نبود، لینک اولین محصول را دنبال کن
        if not images:
            first_link = soup.find('a', href=re.compile(r'/product/'))
            if first_link:
                prod_url = urljoin(base, first_link['href'])
                resp2 = self.fetch_with_retry(prod_url)
                if resp2:
                    images = self.extract_images_from_html(resp2.text, base)
        
        return list(dict.fromkeys(images))[:CONFIG['MAX_IMAGES']]

    def search_wh(self, product):
        name = product.get('name', '')
        code = product.get('code', '')
        base = 'https://expo-dent.com'
        query = code if code else name
        
        search_url = f"{base}/catalog/?q={quote(query)}"
        resp = self.fetch_with_retry(search_url)
        if not resp:
            return []
        
        soup = BeautifulSoup(resp.text, 'lxml')
        images = []
        
        # استخراج تصاویر از نتایج جستجو
        for img in soup.find_all('img', src=True):
            src = img['src']
            if '/upload/' in src:
                img_url = self.normalize_url(src, base)
                if img_url and self.is_image_url(img_url):
                    images.append(img_url)
        
        # اگر تصویری نبود، لینک اولین محصول را دنبال کن
        if not images:
            first_link = soup.find('a', href=re.compile(r'/product/'))
            if first_link:
                prod_url = urljoin(base, first_link['href'])
                resp2 = self.fetch_with_retry(prod_url)
                if resp2:
                    images = self.extract_images_from_html(resp2.text, base)
        
        return list(dict.fromkeys(images))[:CONFIG['MAX_IMAGES']]

    # ============================================================
    #  دانلود و ذخیره‌سازی
    # ============================================================

    def find_images(self, product):
        brand = product.get('brand', '').upper()
        if brand == 'COXO':
            return self.search_coxo(product)
        elif brand == 'NSK':
            return self.search_nsk(product)
        elif brand == 'W&H':
            return self.search_wh(product)
        else:
            return []

    def download_images(self, product_id, urls):
        folder = os.path.join(CONFIG['OUTPUT_DIR'], product_id)
        os.makedirs(folder, exist_ok=True)
        
        saved = []
        for i, url in enumerate(urls[:CONFIG['MAX_IMAGES']], 1):
            try:
                resp = self.fetch_with_retry(url)
                if resp and resp.status_code == 200:
                    # تشخیص پسوند
                    content_type = resp.headers.get('content-type', '')
                    ext = 'jpg'
                    if 'png' in content_type:
                        ext = 'png'
                    elif 'webp' in content_type:
                        ext = 'webp'
                    elif 'svg' in content_type:
                        ext = 'svg'
                    elif 'gif' in content_type:
                        ext = 'gif'
                    else:
                        # استخراج از URL
                        m = re.search(r'\.(jpg|jpeg|png|webp|gif|svg)', url, re.I)
                        if m:
                            ext = m.group(1).lower()
                    
                    filename = f"{i}.{ext}"
                    filepath = os.path.join(folder, filename)
                    with open(filepath, 'wb') as f:
                        f.write(resp.content)
                    saved.append(filepath)
                    print(f"   ✅ دانلود: {filename}")
            except Exception as e:
                print(f"   ❌ خطا در دانلود {url}: {e}")
            time.sleep(0.3)
        
        return saved

    # ============================================================
    #  اجرای اصلی
    # ============================================================

    def run(self):
        total = len(self.products)
        success = 0
        failed = 0
        skipped = 0
        
        for idx, product in enumerate(self.products, 1):
            pid = product.get('id')
            if not pid:
                continue
                
            # اگر قبلاً تصویر دارد، رد کن
            if pid in self.mapping:
                skipped += 1
                continue
                
            print(f"\n📦 [{idx}/{total}] {product.get('name')} ({product.get('brand')})")
            
            # جستجوی تصاویر
            image_urls = self.find_images(product)
            print(f"   🔍 {len(image_urls)} تصویر پیدا شد")
            
            if len(image_urls) >= CONFIG['MIN_IMAGES']:
                saved = self.download_images(pid, image_urls)
                if saved:
                    self.mapping[pid] = {
                        'name': product.get('name'),
                        'brand': product.get('brand'),
                        'images': saved
                    }
                    success += 1
                    print(f"   ✅ {len(saved)} تصویر ذخیره شد")
                else:
                    failed += 1
            else:
                failed += 1
                print(f"   ❌ تعداد تصاویر کافی نیست ({len(image_urls)})")
            
            # ذخیره مپینگ بعد از هر محصول (برای جلوگیری از از دست رفتن)
            with open(CONFIG['MAPPING_FILE'], 'w', encoding='utf-8') as f:
                json.dump(self.mapping, f, ensure_ascii=False, indent=2)
            
            time.sleep(CONFIG['DELAY'])
        
        # گزارش نهایی
        print("\n" + "="*50)
        print(f"✅ موفق: {success} محصول")
        print(f"❌ ناموفق: {failed} محصول")
        print(f"⏩ رد شده: {skipped} محصول (قبلاً ذخیره شده)")
        print(f"📁 تصاویر ذخیره شده در: {CONFIG['OUTPUT_DIR']}")
        print(f"📄 مپینگ: {CONFIG['MAPPING_FILE']}")

# ============================================================
#  اجرا
# ============================================================
if __name__ == "__main__":
    scraper = DentalImageScraper()
    scraper.run()
