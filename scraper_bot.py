#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ربات اسکرپر یونیدنت
دریافت تصاویر محصولات از سایت‌های مرجع:
- COXO: coxotec.com
- NSK: fordent.ru
- W&H: swallowdental.co.uk
"""

import os
import json
import time
import re
import asyncio
from typing import Dict, List, Optional
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class DentalScraper:
    """ربات اسکرپر محصولات دندانپزشکی"""
    
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.session = None
        self.results = {}
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={"User-Agent": self.user_agent}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_html(self, url: str) -> Optional[str]:
        """دریافت محتوای HTML از یک URL"""
        try:
            async with self.session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    return await response.text()
                return None
        except Exception as e:
            print(f"⚠️ خطا در دریافت {url}: {e}")
            return None
    
    def extract_images_from_html(self, html: str, base_url: str) -> List[str]:
        """استخراج تصاویر از HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        images = []
        
        # الگوهای مختلف برای یافتن تصاویر
        patterns = [
            # متا تگ‌های Open Graph
            soup.find('meta', property='og:image'),
            soup.find('meta', attrs={'name': 'twitter:image'}),
            # تگ‌های img با کلاس‌های خاص
            soup.find('img', class_='product-image'),
            soup.find('img', class_='product-img'),
            soup.find('img', class_='main-image'),
            soup.find('img', class_='featured-image'),
            # اولین تصویر بزرگ در صفحه
            soup.find('img', {'itemprop': 'image'}),
        ]
        
        for img in patterns:
            if img:
                src = img.get('content') or img.get('src')
                if src:
                    if not src.startswith('http'):
                        src = urljoin(base_url, src)
                    images.append(src)
        
        # جستجوی تمام تصاویر در مسیرهای خاص
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if src:
                # فیلتر کردن تصاویر کوچک و آیکون‌ها
                if any(pattern in src.lower() for pattern in ['product', 'catalog', 'upload', 'media', 'image']):
                    if not src.startswith('http'):
                        src = urljoin(base_url, src)
                    if src not in images:
                        images.append(src)
        
        return images
    
    async def scrape_coxo(self, model_name: str, product_code: str) -> Dict:
        """اسکرپ سایت COXO (coxotec.com)"""
        clean_name = re.sub(r'^[A-Z]+\s*', '', model_name).lower().strip()
        clean_name = re.sub(r'[^a-z0-9]+', '-', clean_name).strip('-')
        code = product_code.lower().strip() if product_code else ''
        
        urls = [
            f'https://coxotec.com/product/{clean_name}/',
            f'https://coxotec.com/en/product/{clean_name}/',
            f'https://coxotec.com/ja/product/{clean_name}/',
            f'https://coxotec.com/ru/product/{clean_name}/'
        ]
        
        for url in urls:
            html = await self.fetch_html(url)
            if html:
                images = self.extract_images_from_html(html, url)
                # فیلتر تصاویر محصول
                product_images = [img for img in images if any(x in img for x in ['product', 'handpiece', 'motor'])]
                if product_images:
                    return {
                        'url': url,
                        'images': product_images[:5],
                        'source': 'coxotec.com'
                    }
                time.sleep(self.delay)
        
        return {'url': None, 'images': [], 'source': 'coxotec.com'}
    
    async def scrape_nsk(self, model_name: str, product_code: str) -> Dict:
        """اسکرپ سایت NSK (fordent.ru)"""
        query = product_code or model_name
        base_url = 'https://fordent.ru'
        search_url = f'{base_url}/search/?q={query}'
        
        html = await self.fetch_html(search_url)
        if not html:
            return {'url': None, 'images': [], 'source': 'fordent.ru'}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # پیدا کردن لینک محصول
        product_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/catalog/product/' in href or '/product/' in href:
                full_url = urljoin(base_url, href)
                product_links.append(full_url)
        
        # بررسی اولین لینک محصول
        for product_url in product_links[:3]:
            product_html = await self.fetch_html(product_url)
            if product_html:
                images = self.extract_images_from_html(product_html, product_url)
                if images:
                    return {
                        'url': product_url,
                        'images': images[:5],
                        'source': 'fordent.ru'
                    }
                time.sleep(self.delay)
        
        return {'url': None, 'images': [], 'source': 'fordent.ru'}
    
    async def scrape_wh(self, model_name: str, product_code: str) -> Dict:
        """اسکرپ سایت W&H (swallowdental.co.uk)"""
        query = product_code or model_name
        base_url = 'https://www.swallowdental.co.uk'
        search_url = f'{base_url}/search/{query}'
        
        html = await self.fetch_html(search_url)
        if not html:
            return {'url': None, 'images': [], 'source': 'swallowdental.co.uk'}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # پیدا کردن لینک محصول
        product_links = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if '/product/' in href or '/catalog/product/' in href:
                full_url = urljoin(base_url, href)
                product_links.append(full_url)
        
        for product_url in product_links[:3]:
            product_html = await self.fetch_html(product_url)
            if product_html:
                images = self.extract_images_from_html(product_html, product_url)
                if images:
                    return {
                        'url': product_url,
                        'images': images[:5],
                        'source': 'swallowdental.co.uk'
                    }
                time.sleep(self.delay)
        
        return {'url': None, 'images': [], 'source': 'swallowdental.co.uk'}
    
    async def scrape_product(self, product: Dict) -> Dict:
        """اسکرپ یک محصول بر اساس برند آن"""
        brand = product.get('brand', '')
        name = product.get('name', '')
        code = product.get('code', '')
        product_id = product.get('id', '')
        
        result = {
            'id': product_id,
            'name': name,
            'brand': brand,
            'code': code,
            'images': [],
            'source_url': None,
            'source': ''
        }
        
        try:
            if brand.upper() == 'COXO':
                data = await self.scrape_coxo(name, code)
            elif brand.upper() == 'NSK':
                data = await self.scrape_nsk(name, code)
            elif brand.upper() == 'W&H':
                data = await self.scrape_wh(name, code)
            else:
                return result
            
            if data.get('images'):
                result['images'] = data['images']
                result['source_url'] = data.get('url')
                result['source'] = data.get('source', '')
                print(f"✅ {brand} - {name}: {len(result['images'])} تصویر یافت شد")
            else:
                print(f"❌ {brand} - {name}: تصویری یافت نشد")
                
        except Exception as e:
            print(f"⚠️ خطا در اسکرپ {brand} - {name}: {e}")
        
        return result
    
    async def scrape_products(self, products: List[Dict]) -> Dict:
        """اسکرپ لیست محصولات"""
        results = {}
        total = len(products)
        
        for idx, product in enumerate(products):
            print(f"⏳ اسکرپ محصول {idx+1}/{total}: {product.get('name', '')}")
            result = await self.scrape_product(product)
            results[result['id']] = result
            await asyncio.sleep(self.delay)
        
        return results


def load_products_from_localstorage() -> List[Dict]:
    """بارگذاری محصولات از فایل JSON (شبیه‌سازی localStorage)"""
    try:
        with open('products_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ فایل products_data.json یافت نشد.")
        return []


def generate_image_mapping(scrape_results: Dict, products: List[Dict]) -> Dict:
    """تولید فایل mapping تصاویر"""
    mapping = {}
    
    for product in products:
        product_id = product.get('id', '')
        if product_id in scrape_results:
            result = scrape_results[product_id]
            if result.get('images'):
                mapping[product_id] = {
                    'name': product.get('name', ''),
                    'brand': product.get('brand', ''),
                    'images': result['images'],
                    'source_url': result.get('source_url', ''),
                    'source': result.get('source', '')
                }
    
    return mapping


async def main():
    """تابع اصلی"""
    print("🦷 ربات اسکرپر یونیدنت")
    print("=" * 50)
    
    # بارگذاری محصولات
    products = load_products_from_localstorage()
    if not products:
        print("⚠️ هیچ محصولی برای اسکرپ یافت نشد.")
        print("📝 لطفاً فایل products_data.json را در مسیر جاری قرار دهید.")
        return
    
    print(f"📊 تعداد محصولات: {len(products)}")
    
    # اجرای اسکرپ
    async with DentalScraper(delay=1.5) as scraper:
        results = await scraper.scrape_products(products)
    
    # تولید mapping
    mapping = generate_image_mapping(results, products)
    
    # ذخیره نتایج
    with open('image_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    # ذخیره نتایج کامل
    with open('scrape_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("=" * 50)
    print(f"✅ اسکرپ کامل شد!")
    print(f"📁 تعداد محصولات اسکرپ شده: {len(results)}")
    print(f"📁 تعداد محصولات با تصویر: {len([r for r in results.values() if r.get('images')])}")
    print(f"📁 فایل image_mapping.json ذخیره شد.")


if __name__ == '__main__':
    asyncio.run(main())
