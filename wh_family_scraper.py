#!/usr/bin/env python3
"""W&H official image scraper - extracts family-level product images from wh.com"""
import json, os, re, time, asyncio, glob
from playwright.async_api import async_playwright

HANDLE = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Product family pages with image URLs (found from sitemap + exploration)
FAMILY_PAGES = {
    'synea_turbine': 'https://www.wh.com/en_global/dental-products/restoration-prosthetics/turbines/synea/',
    'synea_handpiece': 'https://www.wh.com/en_global/dental-products/restoration-prosthetics/handpieces/synea',
    'alegra_turbine': 'https://www.wh.com/en_global/dental-products/restoration-prosthetics/turbines/alegra',
    'alegra_handpiece': 'https://www.wh.com/en_global/dental-products/restoration-prosthetics/handpieces/alegra',
    'implantmed': 'https://www.wh.com/en_global/dental-products/oralsurgery-implantology/surgical-devices/implantmed',
    'piezomed': 'https://www.wh.com/en_global/dental-products/oralsurgery-implantology/surgical-devices/piezomed',
    'lisa': 'https://www.wh.com/en_global/dental-products/sterilization-hygienic-maintenance/sterilizers/lisa-autoclave',
    'assistina': 'https://www.wh.com/en_global/dental-products/sterilization-hygienic-maintenance/reprocessing-devices/assistina-twin',
    'proxeo': 'https://www.wh.com/en_global/dental-products/prophylaxis-periodontology/air-polisher/proxeo-aura',
}

# Map W&H product families to their page source
# The model number within a family varies only by connection type/speed - visual appearance is identical
FAMILY_MAP = {
    'SYNEA-TA': 'synea_turbine',
    'SYNEA-FUSION-TA': 'synea_turbine',
    'SYNEA-FUSION-TK': 'synea_turbine',
    'SYNEA-FUSION': 'synea_handpiece',  
    'SYNEA-FUSION-TE': 'synea_handpiece',
    'SYNEA-FUSION-WK': 'synea_handpiece',
    'SYNEA-VISION-TK': 'synea_turbine',
    'SYNEA-VISION-WK': 'synea_handpiece',
    'SYNEA-WK': 'synea_handpiece',
    'ALEGRA-TE': 'alegra_turbine',
    'ALEGRA-WK': 'alegra_handpiece',
}

async def extract_images_from_page(page, url, family_name):
    """Navigate to product page and extract product images"""
    print(f'Loading: {family_name} -> {url}')
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        # Wait for JS rendering - Storyblok loads content dynamically
        await page.wait_for_timeout(8000)
        
        # Try clicking "Show details" buttons to reveal galleries
        buttons = await page.evaluate('''() => {
            return document.querySelectorAll('button, a, .btn, [role="button"]').length;
        }''')
        
        # Look for product images with storyblok CDN
        imgs = await page.evaluate('''() => {
            const allImgs = document.querySelectorAll('img[src], picture source[srcset], [style*="background"]');
            const results = [];
            allImgs.forEach(el => {
                const src = el.src || el.getAttribute('srcset') || '';
                const bg = window.getComputedStyle(el).backgroundImage || '';
                if (bg && bg.includes('url(')) {
                    const urlMatch = bg.match(/url\(["']?([^"')]+)["']?\)/);
                    if (urlMatch && urlMatch[1].includes('storyblok.com')) {
                        results.push({src: urlMatch[1], type: 'bg'});
                    }
                }
                if (src && src.includes('storyblok.com')) {
                    results.push({src: src, type: el.tagName.toLowerCase()});
                }
            });
            return results;
        }''')
        
        # Also check for images loaded by JS (might be in data attributes)
        all_imgs = await page.evaluate('''() => {
            const imgs = document.querySelectorAll('img[src]');
            return Array.from(imgs).map(img => ({
                src: img.src,
                alt: img.alt || '',
                width: img.naturalWidth,
                height: img.naturalHeight
            }));
        }''')
        
        product_imgs = [i for i in all_imgs if i['width'] > 80 and i['height'] > 80]
        
        print(f'  Storyblok imgs: {len(imgs)}, Product imgs >80px: {len(product_imgs)}')
        for img in product_imgs[:8]:
            print(f'    {img["src"][:120]} ({img["width"]}x{img["height"]})')
        
        # Combine unique storyblok image URLs
        unique = {}
        for img in imgs:
            src = img['src']
            # Get high-res version from storyblok
            if '/m/' in src:
                # Convert to full size: remove /m/ filter
                base = re.sub(r'/m/\d+x\d+', '', src)
                base = re.sub(r'/filters:[^/]+', '', base)
            else:
                base = src
            unique[base] = src
        
        return list(unique.values())
        
    except Exception as e:
        print(f'  Failed: {e}')
        return []

async def download_image(page, url, path):
    """Download image"""
    try:
        resp = await page.request.get(url, timeout=15000)
        if resp.status == 200:
            body = await resp.body()
            if len(body) > 2000:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'wb') as f:
                    f.write(body)
                return True
    except:
        pass
    return False

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=HANDLE,
            ignore_https_errors=True
        )
        page = await context.new_page()
        
        # Load product mapping
        with open('data/products.json') as f:
            products = json.load(f)
        with open('image_mapping.json') as f:
            mapping = json.load(f)
        
        # Find W&H products without images
        todo = {}
        for prod in products:
            if prod['brand'] != 'W&H':
                continue
            pid = prod['id']
            existing = mapping.get(pid, {}).get('images', [])
            if existing:
                continue
            
            code = prod.get('code', '')
            # Determine product family
            mm = re.match(r'([A-Z]+-?[A-Z]*(?:-FUSION|-VISION)?)', code, re.I)
            if mm:
                family_key = mm.group(1).upper().replace(' ', '-')
                if family_key in FAMILY_MAP:
                    source = FAMILY_MAP[family_key]
                    if source not in todo:
                        todo[source] = []
                    todo[source].append((pid, code, prod['name']))
        
        print(f'W&H products to fill: {sum(len(v) for v in todo.values())}')
        print(f'Family pages to scrape: {len(todo)}')
        print()
        
        # Scrape each family page and save images
        for family_name, products_in_family in todo.items():
            url = FAMILY_PAGES[family_name]
            image_urls = await extract_images_from_page(page, url, family_name)
            
            if not image_urls:
                print(f'  No images found for {family_name}, skipping {len(products_in_family)} products\n')
                continue
            
            # Download images once per family
            family_dir = f'images/wh_family/{family_name}'
            saved_paths = []
            for i, img_url in enumerate(image_urls[:8], 1):
                ext = '.png' if '.png' in img_url.lower() else '.jpg'
                path = f'{family_dir}/{i}{ext}'
                if await download_image(page, img_url, path):
                    saved_paths.append(path)
                await page.wait_for_timeout(200)
            
            print(f'  Downloaded {len(saved_paths)} images for {family_name}')
            
            # Copy to each product in this family
            for pid, code, name in products_in_family:
                product_dir = f'images/{pid}'
                if os.path.isdir(product_dir) and glob.glob(f'{product_dir}/*'):
                    continue  # Skip if already has images
                
                os.makedirs(product_dir, exist_ok=True)
                product_paths = []
                for j, src_path in enumerate(saved_paths, 1):
                    ext = os.path.splitext(src_path)[1]
                    dst = f'{product_dir}/{j}{ext}'
                    if not os.path.exists(dst):
                        with open(src_path, 'rb') as sf:
                            with open(dst, 'wb') as df:
                                df.write(sf.read())
                    product_paths.append(dst)
                
                mapping[pid]['images'] = product_paths
                print(f'    {pid}: {name[:50]} -> {len(product_paths)} images')
            
            print()
            
            # Save periodically
            with open('image_mapping.json', 'w') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
        
        # Update products.json
        for prod in products:
            pid = prod['id']
            d = f'images/{pid}'
            if os.path.isdir(d):
                prod['images'] = len(glob.glob(f'{d}/*'))
            else:
                prod['images'] = 0
        
        with open('data/products.json', 'w') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        await browser.close()
        
        # Stats
        filled = sum(1 for p in products if p['brand'] == 'W&H' and p['images'] >= 3)
        print(f'\nDone. W&H products with 3+ images: {filled}/100')

if __name__ == '__main__':
    asyncio.run(main())
