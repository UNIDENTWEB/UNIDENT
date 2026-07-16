#!/usr/bin/env python3
"""W&H official website scraper using Playwright"""
import json, os, re, time, asyncio, shutil, glob
from playwright.async_api import async_playwright

BASE = 'https://www.wh.com'
HANDLE = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

async def get_page_content(page, url, wait_sec=8):
    """Navigate to URL and return page content after rendering"""
    await page.goto(url, wait_until='networkidle', timeout=30000)
    await page.wait_for_timeout(wait_sec * 1000)
    return await page.content()

async def download_image(page, url, path):
    """Download image via fetch to a file"""
    try:
        resp = await page.request.get(url, timeout=15000)
        if resp.status == 200 and len(await resp.body()) > 2000:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(await resp.body())
            return True
    except:
        pass
    return False

async def explore_wh_site(page):
    """Explore W&H product pages and find image sources"""
    print("=== Exploring W&H official website ===\n")
    
    # Try the dental products page
    pages_to_try = [
        f'{BASE}/en_global/dental-products/handpieces/turbines/',
        f'{BASE}/en_global/dental-products/handpieces/contra-angle/',
        f'{BASE}/en_global/dental-products/handpieces/',
        f'{BASE}/en_global/dental-products/',
    ]
    
    all_product_links = {}
    
    for url in pages_to_try:
        try:
            content = await get_page_content(page, url)
            print(f'Page: {url}')
            print(f'  Content length: {len(content)}')
            
            # Extract all links
            links = await page.evaluate('''() => {
                const links = document.querySelectorAll('a[href]');
                return Array.from(links).map(a => ({
                    href: a.href,
                    text: a.textContent.trim().substring(0, 80)
                }));
            }''')
            
            # Find product-related links
            product_links = [(l['text'], l['href']) for l in links 
                           if any(kw in l['href'].lower() for kw in 
                                  ['product', 'synea', 'alegra', 'handpiece', 'turbine',
                                   'contra-angle', 'implantmed', 'elcomed', 'piezomed'])]
            
            print(f'  Product links: {len(product_links)}')
            for text, href in product_links[:10]:
                print(f'    {text[:60]} -> {href[:100]}')
            
            # Extract all images
            imgs = await page.evaluate('''() => {
                const imgs = document.querySelectorAll('img[src]');
                return Array.from(imgs).map(img => ({
                    src: img.src,
                    alt: (img.alt || '').substring(0, 60),
                    width: img.naturalWidth,
                    height: img.naturalHeight
                }));
            }''')
            
            product_imgs = [i for i in imgs if i['width'] > 100 and i['height'] > 100]
            print(f'  Product images (>100px): {len(product_imgs)}')
            for img in product_imgs[:5]:
                print(f'    {img["src"][:120]} ({img["width"]}x{img["height"]})')
            
            all_product_links[url] = product_links
            print()
        except Exception as e:
            print(f'  Failed: {e}\n')
    
    return all_product_links

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=HANDLE
        )
        page = await context.new_page()
        
        # Explore the site
        links = await explore_wh_site(page)
        
        # Save exploration results
        with open('wh_site_links.json', 'w') as f:
            json.dump(links, f, ensure_ascii=False, indent=2)
        
        await browser.close()
        print('Done exploring. Results saved to wh_site_links.json')

if __name__ == '__main__':
    asyncio.run(main())
