#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, requests, time, re
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup

CONFIG = {
    'PRODUCTS_FILE': 'products.json',
    'OUTPUT_DIR': 'images',
    'MAPPING_FILE': 'image_mapping.json',
    'MIN_IMAGES': 2,
    'MAX_IMAGES': 5,
    'DELAY': 1.0
}

class SmartBot:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        self.load_products()
        self.mapping = {}
        self.load_mapping()
        os.makedirs(CONFIG['OUTPUT_DIR'], exist_ok=True)

    def load_products(self):
        with open(CONFIG['PRODUCTS_FILE'], 'r', encoding='utf-8') as f:
            self.products = json.load(f)
        print(f"✅ {len(self.products)} محصول")

    def load_mapping(self):
        try:
            with open(CONFIG['MAPPING_FILE'], 'r', encoding='utf-8') as f:
                self.mapping = json.load(f)
        except:
            self.mapping = {}

    def extract_images(self, html, base_url):
        if not html: return []
        soup = BeautifulSoup(html, 'lxml')
        images = []
        og = soup.find('meta', property='og:image')
        if og and og.get('content'):
            images.append(og['content'])
        for img in soup.find_all('img', src=True):
            src = img['src']
            if any(x in src.lower() for x in ['logo', 'icon', 'thumb']): continue
            if src.startswith('//'): src = 'https:' + src
            elif src.startswith('/'): src = urljoin(base_url, src)
            elif not src.startswith('http'): src = urljoin(base_url, src)
            if re.search(r'\.(jpg|jpeg|png|webp)', src, re.I):
                images.append(src)
        return list(dict.fromkeys(images))

    def search_coxo(self, product):
        name = product.get('name', '')
        code = product.get('code', '')
        base = 'https://coxotec.com'
        slug = re.sub(r'[^\w\-]', '', name.lower().replace(' ', '-'))
        urls = [
            f"{base}/product/{slug}/",
            f"{base}/en/product/{slug}/",
            f"{base}/search/?q={quote(code)}"
        ]
        for url in urls:
            try:
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    imgs = self.extract_images(r.text, base)
                    if imgs:
                        return imgs[:CONFIG['MAX_IMAGES']]
            except: pass
            time.sleep(0.5)
        return []

    def search_nsk(self, product):
        name = product.get('name', '')
        code = product.get('code', '')
        base = 'https://fordent.ru'
        query = code if code else name
        url = f"{base}/search/?q={quote(query)}"
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code != 200: return []
            soup = BeautifulSoup(r.text, 'lxml')
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                if '/catalog/product/' in src and re.search(r'\.(jpg|jpeg|png|webp)', src, re.I):
                    if src.startswith('//'): src = 'https:' + src
                    elif src.startswith('/'): src = urljoin(base, src)
                    images.append(src)
            for a in soup.find_all('a', href=True):
                if '/product/' in a['href']:
                    prod_url = urljoin(base, a['href'])
                    try:
                        r2 = self.session.get(prod_url, timeout=15)
                        if r2.status_code == 200:
                            imgs = self.extract_images(r2.text, base)
                            images.extend(imgs)
                    except: pass
                    break
            return list(dict.fromkeys(images))[:CONFIG['MAX_IMAGES']]
        except: return []

    def search_wh(self, product):
        name = product.get('name', '')
        code = product.get('code', '')
        base = 'https://expo-dent.com'
        query = code if code else name
        url = f"{base}/catalog/?q={quote(query)}"
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code != 200: return []
            soup = BeautifulSoup(r.text, 'lxml')
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                if '/upload/' in src and re.search(r'\.(jpg|jpeg|png|webp)', src, re.I):
                    if src.startswith('//'): src = 'https:' + src
                    elif src.startswith('/'): src = urljoin(base, src)
                    images.append(src)
            for a in soup.find_all('a', href=True):
                if '/product/' in a['href']:
                    prod_url = urljoin(base, a['href'])
                    try:
                        r2 = self.session.get(prod_url, timeout=15)
                        if r2.status_code == 200:
                            imgs = self.extract_images(r2.text, base)
                            images.extend(imgs)
                    except: pass
                    break
            return list(dict.fromkeys(images))[:CONFIG['MAX_IMAGES']]
        except: return []

    def find_images(self, product):
        brand = product.get('brand', '').upper()
        if brand == 'COXO': return self.search_coxo(product)
        if brand == 'NSK': return self.search_nsk(product)
        if brand == 'W&H': return self.search_wh(product)
        return []

    def download(self, pid, urls):
        folder = os.path.join(CONFIG['OUTPUT_DIR'], pid)
        os.makedirs(folder, exist_ok=True)
        saved = []
        for i, url in enumerate(urls[:CONFIG['MAX_IMAGES']], 1):
            try:
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    ext = 'jpg'
                    ct = r.headers.get('content-type', '')
                    if 'png' in ct: ext = 'png'
                    elif 'webp' in ct: ext = 'webp'
                    path = os.path.join(folder, f"{i}.{ext}")
                    with open(path, 'wb') as f: f.write(r.content)
                    saved.append(path)
                    print(f"   ✅ {i}.{ext}")
            except Exception as e:
                print(f"   ❌ {e}")
        return saved

    def run(self):
        for p in self.products:
            pid = p.get('id')
            if not pid: continue
            if pid in self.mapping: continue
            print(f"\n📦 {p.get('name')}")
            images = self.find_images(p)
            if len(images) >= CONFIG['MIN_IMAGES']:
                saved = self.download(pid, images)
                if saved:
                    self.mapping[pid] = {
                        'name': p.get('name'),
                        'brand': p.get('brand'),
                        'images': saved
                    }
            else:
                print(f"   ❌ فقط {len(images)} تصویر")
            time.sleep(CONFIG['DELAY'])
        with open(CONFIG['MAPPING_FILE'], 'w', encoding='utf-8') as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)
        print(f"\n✅ {len(self.mapping)} محصول ذخیره شد")

if __name__ == "__main__":
    bot = SmartBot()
    bot.run()
