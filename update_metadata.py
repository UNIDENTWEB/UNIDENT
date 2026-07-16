#!/usr/bin/env python3
"""Update product metadata (name, code, brand, type) from source sites"""
import json, re, os

with open('image_mapping.json') as f:
    mapping = json.load(f)
with open('data/products.json') as f:
    products = json.load(f)

# ===== 1. COXO from coxotec.cn - Chinese names & categories =====
coxotec_cn_meta = {
    'coxo_us':  {'name': 'COXO 超声喷砂洁牙机', 'code': 'CP-2', 'type': '洁牙机'},
    'coxo_ia':  {'name': 'COXO 种植体亲水活化仪', 'code': 'C-ACTIVATOR', 'type': '种植配件'},
    'coxo_bs':  {'name': 'COXO 超声骨刀机 C-SURGE', 'code': 'C-SURGE', 'type': '骨刀机'},
    'coxo_im2': {'name': 'COXO 2代牙科种植机', 'code': 'C-SAILOR-II', 'type': '种植机'},
    'coxo_sb':  {'name': 'COXO 口外喷砂枪', 'code': 'C-BLASTER', 'type': '喷砂设备'},
    'coxo_csm': {'name': 'COXO C-SMART mini 根管预备机', 'code': 'C-SMART-MINI', 'type': '根管治疗'},
    'coxo_csi': {'name': 'COXO C-SMART i pilot 领航者', 'code': 'C-SMART-I-PILOT', 'type': '根管治疗'},
    'coxo_csp': {'name': 'COXO C-SMART-I PRO 根管预备机', 'code': 'C-SMART-I-PRO', 'type': '根管治疗'},
    'coxo_d85': {'name': 'COXO 光固化灯 DB-685 PENGUIN', 'code': 'DB-685', 'type': '光固化机'},
    'coxo_d86': {'name': 'COXO 光固化灯 DB-686 LATTRE', 'code': 'DB-686-LATTRE', 'type': '光固化机'},
    'coxo_d8s': {'name': 'COXO 光固化灯 DB686 Swift', 'code': 'DB-686-SWIFT', 'type': '光固化机'},
    'coxo_d8h': {'name': 'COXO 光固化灯 DB686 Honor', 'code': 'DB-686-HONOR', 'type': '光固化机'},
    'coxo_d8m': {'name': 'COXO LED光固化灯 DB-686 Mocha', 'code': 'DB-686-MOCHA', 'type': '光固化机'},
    'coxo_15':  {'name': 'COXO 1:5 增速手机 CX235', 'code': 'CX235-1-5', 'type': '低速手机'},
    'coxo_h01': {'name': 'COXO H01-D1SP 45度高速气涡轮手机', 'code': 'H01-D1SP', 'type': '高速手机'},
    'coxo_c73': {'name': 'COXO C7-3S1 45度拔牙手机', 'code': 'C7-3S1', 'type': '拔牙手机'},
    'coxo_cxf': {'name': 'COXO CX207-F H65 探迂去腐手机', 'code': 'CX207-F', 'type': '高速手机'},
    'coxo_led': {'name': 'COXO LED 风电手机', 'code': 'CX-LED', 'type': '高速手机'},
    'coxo_mp':  {'name': 'COXO MINI 儿牙手机', 'code': 'MINI-PEDO', 'type': '高速手机'},
    'coxo_tor': {'name': 'COXO 旋风系列单点喷水手机', 'code': 'CX-TORNADO', 'type': '高速手机'},
    'coxo_cma': {'name': 'COXO C-SMART MINI AP 根管预备机', 'code': 'C-SMART-MINI-AP', 'type': '根管治疗'},
    'coxo_crv': {'name': 'COXO C-ROOT I(VI) 根管长度测定仪', 'code': 'C-ROOT-VI', 'type': '根管测定'},
    'coxo_csn': {'name': 'COXO C-SMART NOVA 根管治疗仪', 'code': 'C-SMART-NOVA', 'type': '根管治疗'},
    'coxo_cri': {'name': 'COXO C-ROOT I+ 根管长度测定仪', 'code': 'C-ROOT-I-PLUS', 'type': '根管测定'},
    'coxo_cfm': {'name': 'COXO C-FILL mini 牙胶充填仪', 'code': 'C-FILL-MINI', 'type': '牙胶充填'},
    'coxo_cfx': {'name': 'COXO C-FILL X 牙胶充填仪（套装）', 'code': 'C-FILL-X', 'type': '牙胶充填'},
    'coxo_cbl': {'name': 'COXO C-BLADE 牙胶尖切断器', 'code': 'C-BLADE', 'type': '牙胶充填'},
    'coxo_ccl': {'name': 'COXO C-CLEAR 口腔显微镜', 'code': 'C-CLEAR', 'type': '显微镜'},
    'coxo_cc2': {'name': 'COXO C-CLEAR2 高配版口腔显微镜', 'code': 'C-CLEAR-2', 'type': '显微镜'},
    'coxo_ccd': {'name': 'COXO C-CLEAR2 豪华版口腔显微镜', 'code': 'C-CLEAR-2-DLX', 'type': '显微镜'},
    'coxo_im3': {'name': 'COXO 3代牙科种植机', 'code': 'C-SAILOR-III', 'type': '种植机'},
    'coxo_sch': {'name': 'COXO SC-CH 乳牙镍钛锉', 'code': 'SC-CH', 'type': '根管锉'},
    'coxo_sp8': {'name': 'COXO SC-PRO 2018 镍钛锉系统', 'code': 'SC-PRO-2018', 'type': '根管锉'},
    'coxo_spr': {'name': 'COXO SC-PRO 镍钛锉', 'code': 'SC-PRO', 'type': '根管锉'},
    'coxo_cf1': {'name': 'COXO 根管锉取出器 C-FR1', 'code': 'C-FR1', 'type': '根管配件'},
    'coxo_bfr': {'name': 'COXO 根管锉取出器 C-FR2', 'code': 'C-FR2', 'type': '根管配件'},
    'coxo_csa': {'name': 'COXO C-SAILOR AIR 猛禽牙科种植机', 'code': 'C-SAILOR-AIR', 'type': '种植机'},
    'coxo_csp2':{'name': 'COXO C-SAILOR PRO+ 牙科种植机', 'code': 'C-SAILOR-PRO', 'type': '种植机'},
    'coxo_100': {'name': 'COXO CX100 牙科治疗椅', 'code': 'CX100', 'type': '牙椅'},
    'coxo_gen': {'name': 'COXO GENI PRO 麻醉助推仪', 'code': 'GENI-PRO', 'type': '麻醉设备'},
    'coxo_200': {'name': 'COXO CX200 牙科治疗椅', 'code': 'CX200', 'type': '牙椅'},
    'coxo_cma2':{'name': 'COXO C-SMART MINI AP+ 根管预备机', 'code': 'C-SMART-MINI-AP+', 'type': '根管治疗'},
    'coxo_cpm': {'name': 'COXO C-PUMA MASTER 牙科电动马达', 'code': 'C-PUMA-MASTER', 'type': '电动马达'},
}

# ===== 2. COXO from jmudental - match coxo_catalog.json =====
with open('coxo_jmudental_all.json') as f:
    jmudental_products = json.load(f)

# ===== 3. NSK categories from nsk_official_catalog.json paths =====
with open('nsk_official_catalog.json') as f:
    nsk_cat = json.load(f)

# ===== 4. Build category from nsk path =====
def nsk_category(code, name):
    for path, info in nsk_cat.items():
        txt = info.get('text','').lower().replace('-','').replace(' ','')
        sc = code.lower().replace('-','').replace(' ','')
        if sc in txt:
            if '/turbines/' in path:
                return '高速手机'
            if '/contra-angles/' in path or '/contra/' in path:
                return '弯手机'
            if '/handpieces/' in path:
                return '直手机'
            if '/endodontic/' in path or '/endo/' in path:
                return '根管治疗'
            if '/surgical/' in path:
                return '外科手术'
            if '/hygiene/' in path or '/maintenance/' in path:
                return '卫生维护'
            if '/scalers/' in path:
                return '洁牙机'
            if '/laboratory/' in path:
                return '技工设备'
            return '手机'
    return 'N/A'

# ===== 5. Update all products =====
pid_to_product = {p['id']: p for p in products}

# Second pass: infer types for products still N/A
def infer_coxo_type(name, code):
    t = (name + ' ' + code).lower()
    if 'turbine' in t or 'high speed' in t or 'high-speed' in t or 'cx-207' in t or 'cx207' in t:
        return '高速手机'
    if 'low-speed' in t or 'low speed' in t or 'contra' in t or 'c3-' in t:
        return '低速手机'
    if 'endodontic' in t or 'endo' in t or 'apex' in t:
        return '根管治疗'
    if 'curing' in t or 'led' in t or 'db-68' in t or 'db68' in t or 'bright' in t:
        return '光固化机'
    if 'implant' in t or 'surgical' in t or 'surgery' in t or 'sailor' in t or 'tw1' in t or 'tw2' in t:
        return '种植/外科'
    if 'handpiece' in t:
        return '手机'
    if 'motor' in t or 'electric' in t or 'puma' in t:
        return '电动马达'
    if 'scaler' in t or 'ultrasonic' in t or 'cp-1' in t or 'cp1' in t:
        return '洁牙机'
    if 'microscope' in t or 'clear' in t:
        return '显微镜'
    if 'obturation' in t or 'gutta' in t or 'fill' in t or 'pt master' in t:
        return '牙胶充填'
    if 'file' in t or 'ni-ti' in t or 'smart-1' in t or 'smart-2' in t or 'smart-3' in t or 'smart nova' in t:
        return '根管治疗'
    if 'chair' in t:
        return '牙椅'
    if 'blade' in t or 'cutter' in t:
        return '牙胶充填'
    if 'anesthesia' in t:
        return '麻醉设备'
    if 'sandblast' in t or 'blaster' in t:
        return '喷砂设备'
    if 'bone' in t:
        return '骨刀机'
    if 'activator' in t:
        return '种植配件'
    if 'apex' in t or 'root' in t:
        return '根管测定'
    if 'scanner' in t or 'dl-' in t or 'dl3' in t:
        return '口内扫描仪'
    return 'N/A'


for pid, info in mapping.items():
    if pid not in pid_to_product:
        continue
    prod = pid_to_product[pid]
    brand = info.get('brand', '').upper()

    if brand == 'COXO':
        if pid in coxotec_cn_meta:
            # coxotec.cn source
            meta = coxotec_cn_meta[pid]
            prod['name'] = meta['name']
            prod['code'] = meta['code']
            prod['type'] = meta['type']
        else:
            # Try jmudental catalog
            code = info.get('code', '').upper().replace('-','').replace(' ','')
            best_title = None
            for handle, title in jmudental_products.items():
                h = handle.upper().replace('-','').replace(' ','')
                if code and code in h:
                    best_title = title
                    break
                # Also try partial match
                parts = code.split('-') if '-' in code else [code]
                for part in parts:
                    part_clean = part.replace('-','').replace(' ','')
                    if len(part_clean) >= 3 and part_clean.upper() in h:
                        best_title = title
                        break
                if best_title:
                    break

            if best_title:
                prod['name'] = best_title
                # Extract type from title keywords
                t = best_title.lower()
                if 'turbine' in t or 'high speed' in t or 'high-speed' in t:
                    prod['type'] = '高速手机'
                elif 'low-speed' in t or 'low speed' in t or 'contra' in t:
                    prod['type'] = '低速手机'
                elif 'endodontic' in t or 'endo' in t or 'apex' in t:
                    prod['type'] = '根管治疗'
                elif 'curing light' in t or 'led' in t:
                    prod['type'] = '光固化机'
                elif 'implant' in t or 'surgical' in t:
                    prod['type'] = '种植/外科'
                elif 'handpiece' in t:
                    prod['type'] = '手机'
                elif 'motor' in t:
                    prod['type'] = '电动马达'
                elif 'scaler' in t:
                    prod['type'] = '洁牙机'
                elif 'microscope' in t:
                    prod['type'] = '显微镜'
                elif 'obturation' in t or 'gutta' in t:
                    prod['type'] = '牙胶充填'
                elif 'file' in t:
                    prod['type'] = '根管锉'
                elif 'chair' in t:
                    prod['type'] = '牙椅'
                else:
                    prod['type'] = 'N/A'
            else:
                # Keep original name but try to infer type
                prod['type'] = infer_coxo_type(prod.get('name', ''), prod.get('code', ''))

            # Still N/A? Try one more time
            if prod.get('type') == 'N/A':
                prod['type'] = infer_coxo_type(prod.get('name', ''), prod.get('code', ''))

    elif brand == 'NSK':
        code = info.get('code', '')
        name = info.get('name', '')
        prod['type'] = nsk_category(code, name)

        # Refine NSK names based on known patterns
        n = name.upper()
        c = code.upper().replace('-','').replace(' ','')
        if 'ENDODONTIC' in n or 'ENDO' in n and 'MATE' in n:
            prod['type'] = '根管治疗'
        elif 'SURGIC' in n:
            prod['type'] = '外科手术'
        elif 'VARIOS' in n:
            prod['type'] = '洁牙机'
        elif 'PANA-SPRAY' in n or 'PANA SPRAY' in n:
            prod['type'] = '卫生维护'
        elif 'NAC-EC' in c or 'FPB-EC' in c or 'AR-EC' in c:
            prod['type'] = '电动马达'
        elif 'EX-' in c or 'EX' in c[:2]:
            prod['type'] = '根管治疗'
        elif 'ENDO' in c or 'IPEX' in c:
            prod['type'] = '根管治疗'
        elif 'X-SMART' in c or 'XSMART' in c:
            prod['type'] = '根管治疗'
        elif 'TI-ENDO' in c:
            prod['type'] = '根管治疗'
        elif 'FX' in c[:3] or c.startswith('FX'):
            prod['type'] = '低速手机'
        elif 'S-MAX' in c or 'SMAX' in c:
            prod['type'] = '弯手机'
        elif 'TI-MAX' in c or 'TIMAX' in c:
            prod['type'] = '弯手机'
        elif 'NANO' in c or 'NANO95' in c:
            prod['type'] = '高速手机'
        elif c.startswith('Z') and any(d in c for d in ['L','M','S']):
            prod['type'] = '弯手机'
        elif c.startswith('X') and any(d in c for d in ['L','M','S']):
            prod['type'] = '高速手机'
        elif 'PANA-MAX' in c or 'PANAMAX' in c:
            prod['type'] = '高速手机'
        elif 'SG-' in c:
            prod['type'] = '直手机'

    elif brand == 'W&H':
        code = info.get('code', '')
        name = info.get('name', '')
        c = code.upper()
        n = name.upper()

        if 'SYNEA VISION' in n or 'SYNEA-VISION' in c:
            prod['type'] = '高速手机'
        elif 'SYNEA FUSION' in n or 'SYNEA-FUSION' in c:
            prod['type'] = '电动手机'
        elif 'ALEGRA' in n or 'ALEGRA' in c:
            prod['type'] = '高速手机'
        elif 'SYNEA' in n or 'SYNEA' in c:
            prod['type'] = '高速手机'
        else:
            prod['type'] = '手机'

# ===== Second pass: fix any remaining N/A =====
for p in products:
    if p.get('type') == 'N/A':
        brand = p.get('brand', '')
        name = p.get('name', '')
        code = p.get('code', '')
        if brand == 'COXO':
            p['type'] = infer_coxo_type(name, code)
        elif brand == 'NSK':
            # Already covered by code pattern matching above, but try again
            n = name.upper()
            c = code.upper().replace('-','').replace(' ','')
            if 'ENDO' in c or 'IPEX' in c or 'EX-' in c:
                p['type'] = '根管治疗'
            elif 'FX' in c[:3]:
                p['type'] = '低速手机'
            elif any(x in c for x in ['S-MAX','SMAX','TI-MAX','TIMAX']):
                p['type'] = '弯手机'
            elif 'NANO' in c:
                p['type'] = '高速手机'
            elif c[0] in 'ZX' and any(d in c[1:] for d in '0123456789'):
                p['type'] = '手机'
            elif 'SG-' in c:
                p['type'] = '直手机'
            else:
                p['type'] = '手机'  # Default NSK = handpiece

# Save
os.makedirs('data', exist_ok=True)
with open('data/products.json', 'w') as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

# Stats
types = {}
for p in products:
    t = p.get('type', 'N/A')
    types[t] = types.get(t, 0) + 1
print('Product types updated:')
for t, c in sorted(types.items(), key=lambda x: -x[1]):
    print(f'  {t}: {c}')
print(f'Total: {len(products)}')

# Show samples
print('\n=== COXO samples (coxotec.cn) ===')
for p in products:
    if p['id'] in coxotec_cn_meta:
        print(f'  {p["id"]}: {p["name"]} | {p["code"]} | {p["type"]}')
        break

print('\n=== COXO samples (jmudental) ===')
for p in products:
    if p['brand'] == 'COXO' and p['id'] not in coxotec_cn_meta:
        print(f'  {p["id"]}: {p["name"]} | {p["code"]} | {p["type"]}')
        break

print('\n=== NSK samples ===')
for p in products:
    if p['brand'] == 'NSK':
        print(f'  {p["id"]}: {p["name"]} | {p["code"]} | {p["type"]}')
        break

print('\n=== W&H samples ===')
for p in products:
    if p['brand'] == 'W&H':
        print(f'  {p["id"]}: {p["name"]} | {p["code"]} | {p["type"]}')
        break
