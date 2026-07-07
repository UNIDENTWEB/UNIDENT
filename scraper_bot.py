import os, json, requests, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin

CONFIG = {
    'PRODUCTS_FILE': 'products.json',
    'OUTPUT_DIR': 'images',
    'MAPPING_FILE': 'image_mapping.json',
    'MIN_IMAGES': 3,
    'MAX_IMAGES': 5,
}

class Scraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        self.products = []
        self.mapping = {}
        self.load_products()
        self.load_mapping()
    
    def load_products(self):
        with open(CONFIG['PRODUCTS_FILE'], 'r', encoding='utf-8') as f:
            self.products = json.load(f)
    
    def load_mapping(self):
        try:
            with open(CONFIG['MAPPING_FILE'], 'r', encoding='utf-8') as f:
                self.mapping = json.load(f)
        except:
            self.mapping = {}
    
    def extract_from_page(self, url):
        images = []
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code != 200: return []
            soup = BeautifulSoup(r.text, 'html.parser')
            og = soup.find('meta', property='og:image')
            if og and og.get('content'): images.append(og['content'])
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src:
                    full = urljoin(url, src)
                    if not any(x in full.lower() for x in ['logo', 'icon', 'thumb']):
                        images.append(full)
            return images[:5]
        except:
            return []
    
    def find_images(self, product):
        brand = product.get('brand', '')
        name = product.get('name', '')
        all_images = []
        if brand == 'COXO':
            slug = re.sub(r'[^\w\-]', '', name.lower().replace(' ', '-').replace('/', '-'))
            url = f"https://coxotec.com/product/{slug}/"
            all_images = self.extract_from_page(url)
        return all_images[:CONFIG['MAX_IMAGES']]
    
    def download_images(self, product_id, urls):
        folder = os.path.join(CONFIG['OUTPUT_DIR'], product_id)
        os.makedirs(folder, exist_ok=True)
        saved = []
        for i, url in enumerate(urls[:CONFIG['MAX_IMAGES']], 1):
            try:
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    ext = 'jpg'
                    if 'png' in r.headers.get('content-type', ''): ext = 'png'
                    elif 'webp' in r.headers.get('content-type', ''): ext = 'webp'
                    path = os.path.join(folder, f"{i}.{ext}")
                    with open(path, 'wb') as f: f.write(r.content)
                    saved.append(path)
            except:
                continue
        return saved
    
    def run(self):
        for p in self.products:
            pid = p.get('id', '')
            if pid in self.mapping and self.mapping[pid].get('images'): continue
            images = self.find_images(p)
            if len(images) >= CONFIG['MIN_IMAGES']:
                saved = self.download_images(pid, images)
                if saved:
                    self.mapping[pid] = {'name': p.get('name', ''), 'brand': p.get('brand', ''), 'images': saved}
        with open(CONFIG['MAPPING_FILE'], 'w', encoding='utf-8') as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    Scraper().run()
