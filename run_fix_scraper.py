#!/usr/bin/env python3
"""Run fix_scraper functions only for NSK and W&H missing products"""
import json, os, time, glob
from fix_scraper import scrape_nsk_fordent, scrape_wh_swallowdental, download_image

with open('image_mapping.json') as f:
    mapping = json.load(f)

todo = []
for pid, info in mapping.items():
    brand = pid.split('_')[0].upper()
    if brand == 'COXO':
        continue
    d = f'images/{pid}'
    files = glob.glob(f'{d}/*') if os.path.isdir(d) else []
    if len(files) >= 3:
        continue
    todo.append((pid, info))

print(f'Products to scrape: {len(todo)}')
scraper_map = {'NSK': scrape_nsk_fordent, 'WH': scrape_wh_swallowdental}

ok = 0
nsksaved = whsaved = 0

for i, (pid, info) in enumerate(todo, 1):
    brand = pid.split('_')[0].upper()
    name = info.get('name', '')
    code = info.get('code', '')
    fn = scraper_map.get(brand)

    if not fn:
        continue

    print(f'[{i}/{len(todo)}] {name[:50]} ...', end=' ', flush=True)
    urls = fn(code, name)

    if not urls:
        print('0 images')
        time.sleep(0.3)
        continue

    print(f'{len(urls)} urls ...', end=' ', flush=True)

    img_dir = f'images/{pid}'
    saved = []
    for j, url in enumerate(urls, 1):
        ext = 'png' if '.png' in url.lower() else 'jpg'
        path = f'{img_dir}/{j}.{ext}'
        if download_image(url, path):
            saved.append(path)
        time.sleep(0.15)

    mapping[pid]['images'] = saved
    mapping[pid]['source_urls'] = urls

    if len(saved) >= 3:
        ok += 1
        if brand == 'NSK':
            nsksaved += 1
        else:
            whsaved += 1
    print(f'{len(saved)} saved')

    if i % 5 == 0:
        with open('image_mapping.json', 'w') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

    time.sleep(0.3)

with open('image_mapping.json', 'w') as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)

print(f'\nDone: {ok}/{len(todo)} with 3+ images (NSK={nsksaved}, WH={whsaved})')
