#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 ربات اسکرپر تصاویر محصولات یونیدنت
پشتیبانی از برندهای COXO، NSK و W&H
ورودی: products.json (آرایه‌ای از اشیاء با id, name, brand, code)
خروجی: image_mapping.json + تصاویر در پوشه images/{id}/
"""

import os
import json
import requests
import time
import re
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup

# ============================================================
#  تنظیمات
# ============================================================
CONFIG = {
    'PRODUCTS_FILE': 'products.json',
    'OUTPUT_DIR': 'images',
    'MAPPING_FILE': 'image_mapping.json',
    'MIN_IMAGES': 2,           # حداقل تعداد تصویر برای قبول
    'MAX_IMAGES': 5,           # حداکثر تعداد تصویر برای هر محصول
    'REQUEST_DELAY': 1.0,      # تاخیر بین درخواست‌ها (ثانیه)
    'TIMEOUT': 15,             # زمان انتظار برای هر درخواست
}

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ============================================================
#  کلاس ربات
# ============================================================
class SmartScraperBot:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.products = []
        self.mapping = {}
        self.load_products()
        self.load_mapping()
        # ایجاد پوشه خروجی
        os.makedirs(CONFIG['OUTPUT_DIR'], exist_ok=True)

    def load_products(self):
        """بارگذاری لیست محصولات از فایل JSON"""
        try:
            with open(CONFIG['PRODUCTS_FILE'], 'r', encoding='utf-8') as f:
                self.products = json.load(f)
            print(f"✅ {len(self.products)} محصول بارگذاری شد")
        except FileNotFoundError:
            print(f"❌ فایل {CONFIG['PRODUCTS_FILE']} یافت نشد!")
            self.create_sample_products()
        except Exception as e:
            print(f"❌ خطا در بارگذاری محصولات: {e}")

    def create_sample_products(self):
        """ایجاد فایل نمونه برای تست"""
        sample = [
            {"id": "coxo_1", "name": "COXO CX207-W Handpiece", "brand": "COXO", "code": "CX207-W"},
            {"id": "nsk_1", "name": "NSK Ti-Max Z900L", "brand": "NSK", "code": "Z900L"},
            {"id": "wh_1", "name": "W&H WH-SET", "brand": "W&H", "code": "WH-SET"}
        ]
        with open(CONFIG['PRODUCTS_FILE'], 'w', encoding='utf-8') as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)
        self.products = sample
        print(f"✅ نمونه {len(sample)} محصول ساخته شد")

    def load_mapping(self):
        """بارگذاری مپینگ قبلی (برای جلوگیری از دانلود مجدد)"""
        try:
            with open(CONFIG['MAPPING_FILE'], 'r', encoding='utf-8') as f:
                self.mapping = json.load(f)
            print(f"📋 مپینگ قبلی با {len(self.mapping)} محصول بارگذاری شد")
        except:
            self.mapping = {}

    def extract_images_from_html(self, html, base_url):
        """استخراج آدرس تصاویر از HTML با چندین روش"""
        if not html:
            return []
        soup = BeautifulSoup(html, 'lxml')
        images = []

        # ۱. متا تگ og:image
        og = soup.find('meta', property='og:image')
        if og and og.get('content'):
            img = og['content']
            if img.startswith('//'):
                img = 'https:' + img
            elif img.startswith('/'):
                img = urljoin(base_url, img)
            elif not img.startswith('http'):
                img = urljoin(base_url, img)
            images.append(img)

        # ۲. تگ‌های img با کلاس‌های محتوایی
        for img in soup.find_all('img', src=True):
            src = img.get('src') or img.get('data-src')
            if not src:
                continue
            # فیلتر لوگو و آیکون
            if any(x in src.lower() for x in ['logo', 'icon', 'avatar', 'pixel', '1x1', 'thumb']):
                continue
            full = src
            if src.startswith('//'):
                full = 'https:' + src
            elif src.startswith('/'):
                full = urljoin(base_url, src)
            elif not src.startswith('http'):
                full = urljoin(base_url, src)
            if re.search(r'\.(jpg|jpeg|png|webp|svg)(\?.*)?$', full, re.I):
                images.append(full)

        # ۳. JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if 'image' in data:
                        img_val = data['image']
                        if isinstance(img_val, str):
                            images.append(img_val)
                        elif isinstance(img_val, list):
                            for item in img_val:
                                if isinstance(item, dict) and 'url' in item:
                                    images.append(item['url'])
                                elif isinstance(item, str):
                                    images.append(item)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'image' in item:
                            img_val = item['image']
                            if isinstance(img_val, str):
                                images.append(img_val)
            except:
                pass

        # حذف تکراری‌ها
        return list(dict.fromkeys(images))

    # ---------- جستجوی اختصاصی برای هر برند ----------
    def search_coxo(self, product):
        """جستجوی تصویر برای محصول COXO از coxotec.com"""
        name = product.get('name', '')
        code = product.get('code', '')
        base_url = 'https://coxotec.com'

        # استخراج مدل از نام
        model_part = re.sub(r'^COXO\s*', '', name, flags=re.I)
        model_part = re.sub(r'[^a-zA-Z0-9]+', '-', model_part).strip('-').lower()
        if not model_part:
            model_part = code.lower().replace('_', '-').replace(' ', '-')

        urls = [
            f"{base_url}/product/{model_part}/",
            f"{base_url}/en/product/{model_part}/",
            f"{base_url}/product/{model_part}-handpiece/",
            f"{base_url}/search/?q={quote(code)}"
        ]

        all_images = []
        for url in urls:
            try:
                resp = self.session.get(url, timeout=CONFIG['TIMEOUT'])
                if resp.status_code == 200:
                    imgs = self.extract_images_from_html(resp.text, base_url)
                    if imgs:
                        all_images.extend(imgs)
                        break
            except:
                pass
            time.sleep(0.5)

        return list(dict.fromkeys(all_images))[:CONFIG['MAX_IMAGES']]

    def search_nsk(self, product):
        """جستجوی تصویر برای محصول NSK از fordent.ru"""
        name = product.get('name', '')
        code = product.get('code', '')
        base_url = 'https://fordent.ru'

        query = code if code else name
        search_url = f"{base_url}/search/?q={quote(query)}"

        try:
            resp = self.session.get(search_url, timeout=CONFIG['TIMEOUT'])
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, 'lxml')
            images = []

            # تصاویر موجود در صفحه جستجو (معمولاً در /catalog/product/)
            for img in soup.find_all('img', src=True):
                src = img.get('src')
                if src and '/catalog/product/' in src and re.search(r'\.(jpg|jpeg|png|webp)', src, re.I):
                    full = src
                    if src.startswith('//'):
                        full = 'https:' + src
                    elif src.startswith('/'):
                        full = urljoin(base_url, src)
                    elif not src.startswith('http'):
                        full = urljoin(base_url, src)
                    images.append(full)

            # همچنین سعی می‌کنیم لینک محصول را پیدا کرده و وارد آن شویم
            product_links = soup.find_all('a', href=True)
            for a in product_links:
                href = a.get('href')
                if href and '/product/' in href:
                    product_url = urljoin(base_url, href)
                    try:
                        prod_resp = self.session.get(product_url, timeout=CONFIG['TIMEOUT'])
                        if prod_resp.status_code == 200:
                            imgs = self.extract_images_from_html(prod_resp.text, base_url)
                            images.extend(imgs)
                    except:
                        pass
                    break  # فقط اولین محصول را بررسی کن

            return list(dict.fromkeys(images))[:CONFIG['MAX_IMAGES']]
        except Exception as e:
            print(f"   ⚠️ خطا در جستجوی NSK: {e}")
            return []

    def search_wh(self, product):
        """جستجوی تصویر برای محصول W&H از expo-dent.com"""
        name = product.get('name', '')
        code = product.get('code', '')
        base_url = 'https://expo-dent.com'

        query = code if code else name
        search_url = f"{base_url}/catalog/?q={quote(query)}"

        try:
            resp = self.session.get(search_url, timeout=CONFIG['TIMEOUT'])
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, 'lxml')
            images = []

            # تصاویر در /upload/
            for img in soup.find_all('img', src=True):
                src = img.get('src')
                if src and '/upload/' in src and re.search(r'\.(jpg|jpeg|png|webp)', src, re.I):
                    full = src
                    if src.startswith('//'):
                        full = 'https:' + src
                    elif src.startswith('/'):
                        full = urljoin(base_url, src)
                    elif not src.startswith('http'):
                        full = urljoin(base_url, src)
                    images.append(full)

            # لینک محصول
            product_links = soup.find_all('a', href=True)
            for a in product_links:
                href = a.get('href')
                if href and '/product/' in href:
                    product_url = urljoin(base_url, href)
                    try:
                        prod_resp = self.session.get(product_url, timeout=CONFIG['TIMEOUT'])
                        if prod_resp.status_code == 200:
                            imgs = self.extract_images_from_html(prod_resp.text, base_url)
                            images.extend(imgs)
                    except:
                        pass
                    break

            return list(dict.fromkeys(images))[:CONFIG['MAX_IMAGES']]
        except Exception as e:
            print(f"   ⚠️ خطا در جستجوی W&H: {e}")
            return []

    # ---------- تابع اصلی جستجو ----------
    def find_images(self, product):
        """مسیریابی درخواست به برند مربوطه"""
        brand = product.get('brand', '').upper()
        if brand == 'COXO':
            return self.search_coxo(product)
        elif brand == 'NSK':
            return self.search_nsk(product)
        elif brand == 'W&H':
            return self.search_wh(product)
        else:
            print(f"   ⚠️ برند ناشناخته: {brand}")
            return []

    def download_images(self, product_id, image_urls):
        """دانلود تصاویر و ذخیره در پوشه مخصوص محصول"""
        folder = os.path.join(CONFIG['OUTPUT_DIR'], product_id)
        os.makedirs(folder, exist_ok=True)
        saved = []

        for i, url in enumerate(image_urls[:CONFIG['MAX_IMAGES']], 1):
            try:
                resp = self.session.get(url, timeout=CONFIG['TIMEOUT'])
                if resp.status_code == 200:
                    # تشخیص پسوند
                    content_type = resp.headers.get('content-type', '').lower()
                    if 'png' in content_type:
                        ext = 'png'
                    elif 'webp' in content_type:
                        ext = 'webp'
                    elif 'svg' in content_type:
                        ext = 'svg'
                    else:
                        ext = 'jpg'

                    filename = f"{i}.{ext}"
                    path = os.path.join(folder, filename)
                    with open(path, 'wb') as f:
                        f.write(resp.content)
                    saved.append(path)
                    print(f"   ✅ {i}.{ext} دانلود شد")
                else:
                    print(f"   ❌ خطا {resp.status_code} برای {url}")
            except Exception as e:
                print(f"   ❌ خطا در دانلود: {e}")

        return saved

    # ---------- اجرای اصلی ----------
    def run(self):
        print("\n🔄 شروع اسکرپ تصاویر...")
        processed = 0
        skipped = 0

        for product in self.products:
            pid = product.get('id')
            if not pid:
                print("⚠️ محصول بدون id – رد شد")
                continue

            # بررسی اینکه آیا از قبل تصویر دارد
            if pid in self.mapping and self.mapping[pid].get('images'):
                print(f"⏭️ {product.get('name')} از قبل پردازش شده")
                skipped += 1
                continue

            print(f"\n📦 {product.get('name')} ({product.get('brand')})")
            images = self.find_images(product)

            if len(images) >= CONFIG['MIN_IMAGES']:
                saved = self.download_images(pid, images)
                if saved:
                    self.mapping[pid] = {
                        'name': product.get('name', ''),
                        'brand': product.get('brand', ''),
                        'images': saved
                    }
                    processed += 1
                    print(f"   ✅ {len(saved)} تصویر ذخیره شد")
                else:
                    print(f"   ❌ دانلود ناموفق")
            else:
                print(f"   ❌ تعداد تصاویر کافی نیست ({len(images)} یافت شد)")

            time.sleep(CONFIG['REQUEST_DELAY'])

        # ذخیره مپینگ
        with open(CONFIG['MAPPING_FILE'], 'w', encoding='utf-8') as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)

        print(f"\n✅ خلاصه: {processed} محصول جدید پردازش شد، {skipped} محصول از قبل موجود بود")
        print(f"📄 فایل {CONFIG['MAPPING_FILE']} به‌روز شد.")

# ============================================================
#  اجرا
# ============================================================
if __name__ == "__main__":
    bot = SmartScraperBot()
    bot.run()
