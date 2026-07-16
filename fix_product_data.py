#!/usr/bin/env python3
"""Fix product data: English names, catalog titles, prices in Rial, Persian categories, stock"""
import json, os, random, re, glob as gbl

with open('data/products.json') as f:
    products = json.load(f)
with open('image_mapping.json') as f:
    mapping = json.load(f)

# ===== COXO coxotec.cn English names =====
coxotec_cn_en = {
    'coxo_us':  ('COXO Ultrasonic Scaler CP-2', 'CP-2'),
    'coxo_ia':  ('COXO Implant Activator C-ACTIVATOR', 'C-ACTIVATOR'),
    'coxo_bs':  ('COXO Ultrasonic Bone Surgery C-SURGE', 'C-SURGE'),
    'coxo_im2': ('COXO 2nd Gen Implant Motor C-SAILOR-II', 'C-SAILOR-II'),
    'coxo_sb':  ('COXO External Sandblaster C-BLASTER', 'C-BLASTER'),
    'coxo_csm': ('COXO C-SMART Mini Endo Motor', 'C-SMART-MINI'),
    'coxo_csi': ('COXO C-SMART i Pilot Endo Motor', 'C-SMART-I-PILOT'),
    'coxo_csp': ('COXO C-SMART-I PRO Endo Motor', 'C-SMART-I-PRO'),
    'coxo_d85': ('COXO DB-685 Penguin Curing Light', 'DB-685'),
    'coxo_d86': ('COXO DB-686 Lattre Curing Light', 'DB-686-LATTRE'),
    'coxo_d8s': ('COXO DB-686 Swift Curing Light', 'DB-686-SWIFT'),
    'coxo_d8h': ('COXO DB-686 Honor Curing Light', 'DB-686-HONOR'),
    'coxo_d8m': ('COXO DB-686 Mocha LED Curing Light', 'DB-686-MOCHA'),
    'coxo_15':  ('COXO CX235 1:5 Speed Handpiece', 'CX235-1-5'),
    'coxo_h01': ('COXO H01-D1SP 45° High Speed Turbine', 'H01-D1SP'),
    'coxo_c73': ('COXO C7-3S1 45° Extraction Handpiece', 'C7-3S1'),
    'coxo_cxf': ('COXO CX207-F Caries Removal Handpiece', 'CX207-F'),
    'coxo_led': ('COXO LED Wind-Electric Handpiece', 'CX-LED'),
    'coxo_mp':  ('COXO MINI Pediatric Handpiece', 'MINI-PEDO'),
    'coxo_tor': ('COXO Tornado Single-Spray Handpiece', 'CX-TORNADO'),
    'coxo_cma': ('COXO C-SMART MINI AP Endo Motor', 'C-SMART-MINI-AP'),
    'coxo_crv': ('COXO C-ROOT I(VI) Apex Locator', 'C-ROOT-VI'),
    'coxo_csn': ('COXO C-SMART NOVA Endo Motor', 'C-SMART-NOVA'),
    'coxo_cri': ('COXO C-ROOT I+ Apex Locator', 'C-ROOT-I-PLUS'),
    'coxo_cfm': ('COXO C-FILL Mini Obturation System', 'C-FILL-MINI'),
    'coxo_cfx': ('COXO C-FILL X Obturation System', 'C-FILL-X'),
    'coxo_cbl': ('COXO C-BLADE Gutta-Percha Cutter', 'C-BLADE'),
    'coxo_ccl': ('COXO C-CLEAR Dental Microscope', 'C-CLEAR'),
    'coxo_cc2': ('COXO C-CLEAR2 Premium Dental Microscope', 'C-CLEAR-2'),
    'coxo_ccd': ('COXO C-CLEAR2 Deluxe Dental Microscope', 'C-CLEAR-2-DLX'),
    'coxo_im3': ('COXO 3rd Gen Implant Motor C-SAILOR-III', 'C-SAILOR-III'),
    'coxo_sch': ('COXO SC-CH Pediatric NiTi Files', 'SC-CH'),
    'coxo_sp8': ('COXO SC-PRO 2018 NiTi File System', 'SC-PRO-2018'),
    'coxo_spr': ('COXO SC-PRO NiTi Files', 'SC-PRO'),
    'coxo_cf1': ('COXO C-FR1 Broken File Remover', 'C-FR1'),
    'coxo_bfr': ('COXO C-FR2 Broken File Remover Kit', 'C-FR2'),
    'coxo_csa': ('COXO C-SAILOR AIR Implant Motor', 'C-SAILOR-AIR'),
    'coxo_csp2':('COXO C-SAILOR PRO+ Implant Motor', 'C-SAILOR-PRO'),
    'coxo_100': ('COXO CX100 Dental Chair', 'CX100'),
    'coxo_gen': ('COXO GENI PRO Anesthesia Device', 'GENI-PRO'),
    'coxo_200': ('COXO CX200 Dental Chair', 'CX200'),
    'coxo_cma2':('COXO C-SMART MINI AP+ Endo Motor', 'C-SMART-MINI-AP+'),
    'coxo_cpm': ('COXO C-PUMA MASTER Electric Motor', 'C-PUMA-MASTER'),
}

# ===== Type to Persian category =====
type_to_category = {
    '高速手机': 'توربین', '弯手机': 'آنگل', '直手机': 'آنگل',
    '低速手机': 'آنگل', '根管治疗': 'اندو', '根管测定': 'اندو',
    '根管锉': 'اندو', '根管配件': 'اندو', '牙胶充填': 'اندو',
    '电动手机': 'توربین', '电动马达': 'ایرموتور',
    '种植机': 'ایمپلنت', '种植/外科': 'ایمپلنت', '种植配件': 'ایمپلنت',
    '外科手术': 'ایمپلنت', '骨刀机': 'ایمپلنت',
    '光固化机': 'ارتودنسی', '洁牙机': 'ارتودنسی', '喷砂设备': 'ارتودنسی',
    '显微镜': 'ارتودنسی', '口内扫描仪': 'ارتودنسی', '麻醉设备': 'ارتودنسی',
    '牙椅': 'ست هندپیس', '卫生维护': 'ست هندپیس',
    '拔牙手机': 'ایمپلنت', '手机': 'توربین',
}

# ===== Price ranges by category (USD) =====
price_ranges = {
    'توربین': (80, 350), 'آنگل': (120, 450), 'اندو': (200, 900),
    'ایرموتور': (400, 1800), 'ایمپلنت': (600, 2500),
    'ارتودنسی': (100, 500), 'ست هندپیس': (1500, 3500),
}
USD_TO_RIAL = 650000

# ===== Load coxo_catalog.json for better names =====
with open('coxo_catalog.json') as f:
    coxo_catalog = json.load(f)
code_to_title = {}
for handle, info in coxo_catalog.items():
    title = info['title']
    codes = set()
    for m in re.finditer(r'(cx\d+[a-z]*-?\d*|c\d+-?\d+[a-z]*|db\d+[a-z]*|dl-?\d+|c-\w+|c\s*\d+)', handle, re.I):
        codes.add(re.sub(r'[-\s]', '', m.group(0).upper()))
    for m in re.finditer(r'(CX\d+[A-Z]*-?\d*|C\d+-?\d+[A-Z]*|DB\d+[A-Z]*|DL-?\d+)', title):
        codes.add(re.sub(r'[-\s]', '', m.group(0).upper()))
    for c in codes:
        if c not in code_to_title:
            code_to_title[c] = title

# ===== Update all products =====
for prod in products:
    pid = prod['id']
    brand = prod.get('brand', '')

    # Fix COXO coxotec.cn names → English
    if pid in coxotec_cn_en:
        en_name, en_code = coxotec_cn_en[pid]
        prod['name'] = en_name
        prod['code'] = en_code
        if pid in mapping:
            mapping[pid]['name'] = en_name
            mapping[pid]['code'] = en_code

    # Fix COXO jmudental names from catalog
    if brand == 'COXO' and pid not in coxotec_cn_en:
        code = prod.get('code', '').upper().replace('-','').replace(' ','')
        if code in code_to_title:
            catalog_name = code_to_title[code]
            if 'sold' not in catalog_name.lower():
                if not catalog_name.startswith('COXO'):
                    catalog_name = 'COXO ' + catalog_name
                if len(catalog_name) > len(prod.get('name','')) or 'sold' in prod.get('name','').lower():
                    prod['name'] = catalog_name
                    if pid in mapping:
                        mapping[pid]['name'] = catalog_name

    # Set Persian category
    ptype = prod.get('type', '')
    prod['category'] = type_to_category.get(ptype, 'توربین')

    # Generate price (USD)
    cat = prod.get('category', 'توربین')
    low, high = price_ranges.get(cat, (100, 500))
    if 'basePrice' not in prod or prod['basePrice'] == 0:
        seed_val = sum(ord(c) for c in pid)
        random.seed(seed_val)
        prod['basePrice'] = round(random.uniform(low, high), 2)

    # Rial price
    prod['priceRial'] = int(prod['basePrice'] * USD_TO_RIAL)

    # Stock
    if 'stock' not in prod or prod['stock'] == 0:
        random.seed(sum(ord(c) for c in pid) + 100)
        prod['stock'] = random.randint(5, 25)

    # isOriginal
    if 'isOriginal' not in prod:
        prod['isOriginal'] = True

    # Accurate image count from disk
    d = f'images/{pid}'
    if os.path.isdir(d):
        files = gbl.glob(f'{d}/*')
        prod['images'] = len(files)
    else:
        prod['images'] = 0

with open('data/products.json', 'w') as f:
    json.dump(products, f, ensure_ascii=False, indent=2)
with open('image_mapping.json', 'w') as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)

# Stats
cats = {}
for p in products:
    c = p.get('category', 'N/A')
    cats[c] = cats.get(c, 0) + 1
print('Categories:')
for c, n in sorted(cats.items(), key=lambda x: -x[1]):
    print(f'  {c}: {n}')

# Check Chinese names
cn_count = sum(1 for p in products if any('\u4e00' <= c <= '\u9fff' for c in p.get('name','')))
print(f'Chinese names: {cn_count}')

# Price stats
prices = [p['basePrice'] for p in products]
print(f'Price range: ${min(prices):.2f} - ${max(prices):.2f} USD')
print(f'Rial range: {int(min(prices)*USD_TO_RIAL):,} - {int(max(prices)*USD_TO_RIAL):,} Rial')

# Image stats
with_img = sum(1 for p in products if p['images'] >= 3)
print(f'Products with 3+ images: {with_img}/{len(products)}')
print(f'Total products: {len(products)}, Fields: {len(products[0])}')
