import json
import random
import os

def generate_products(count=300):
    brands = ['NSK', 'COXO', 'W&H']
    categories = ['ایمپلنت', 'توربین', 'آنگل', 'ایرموتور', 'ست هندپیس', 'اندو', 'ارتودنسی']

    nsk_models = [
        'Ti-Max Z900L', 'Ti-Max Z800L', 'S-Max M600L', 'S-Max pico', 'Ti-Max X450L',
        'Pana-Max2', 'Ti-Max Z95L', 'Ti-Max Z45L', 'nano95LS', 'X25L',
        'FX25m', 'NAC-EC', 'FPB-EC', 'FX-205M', 'Surgic AP',
        'Endo Mate DT', 'Varios 370', 'Z95L', 'Z25L', 'S-Max M500L',
        'Pana-Max PLUS', 'Ti-Max X95L', 'FX-65m', 'FX-57m', 'Endo Mate TC2',
        'iPexil', 'Ti-ENDO', 'EX-ENDO', 'S-Max Z45L', 'Z85L',
        'Z84L', 'Z15L', 'Z10L', 'Z24L', 'Z65L',
        'Z12L', 'Z35L', 'X95EX', 'X65L', 'X12L',
        'X35L', 'FX15m', 'FX65m', 'AR-EC', 'AR-ECM',
        'EX-6B', 'MP-ER64', 'Ti-Max Z990L', 'Ti-Max X600L', 'FX-75m',
        'S-Max M700L', 'Pana-Max3', 'Nano95LS-PRO', 'Varios 570', 'Z990L',
        'Z50L', 'X75L', 'Ti-Max SG-50', 'Endo-Mate DT Pro', 'FX-25m Plus',
        'Ti-Max Z500L', 'S-Max M300L', 'Pana-Air', 'Ti-Max X300', 'Surgic Pro',
        'EX-8B', 'MP-ER128', 'Ti-Max Z750L', 'Nano85', 'X-Smart Plus',
        'FX-35m', 'AR-EC Plus', 'Endo-Mate', 'Z200L', 'X150L',
        'Ti-Max SG-65', 'FX-85m', 'S-Max M800L', 'Pana-Spray', 'Varios 970',
        'Z330L', 'X50X', 'Ti-ENDO Pro', 'EX-10B', 'MP-ER256',
        'Nano65', 'Ti-Max Z350L', 'FX-50m', 'S-Max M200L', 'Pana-Flow',
        'Ti-Max X150', 'Z400L', 'X250L', 'AR-EC-X', 'EX-5B',
        'Varios 770', 'Nano45', 'Ti-Max Z150L', 'FX-95m', 'S-Max M900L',
    ]

    coxo_models = [
        'CX207-W', 'CX207-F', 'C6-23', 'CX205-M', 'C-sailor Pro',
        'C-Root I', 'C-Smart I Pro', 'PT Master', 'GENI PRO', 'CX207-B',
        'DB686', 'C-CLEAR-2', 'CP-1', 'C-SMART-1 PRO', 'C-SMART MINI AP',
        'C-File Mini', 'C-File Re', 'C-FR2', 'C-BLADE', 'C3-11KIT',
        'C-PUMA PRO3', 'C-PUMA INT X', 'DB686 Q1', 'DB686 HALO', 'DB686 LATTE',
        'C-BRIGHT', 'DL-300P', 'C-ROOT V', 'C-ROOT VI', 'C-SMART NOVA X',
        'C-TW1', 'C-TW2', 'C-SK1', 'C-SK2', 'C-ROOT V',
        'CX-207', 'C-Sailor', 'C-Flex', 'DB-686X', 'C-PUMA Mini',
        'C-SMART ENDO', 'C-Root ZX', 'DB-686 PRO', 'CX-F1', 'CX-S1',
        'C-CURE', 'C-HEAL', 'C-PROBE', 'C-TORQUE-X', 'CX-207 Pro',
        'C-BLADE Pro', 'C-CLEAR Pro', 'CX-MINI', 'DB-686 Lite', 'C-SEAL',
        'C-SMART-2 PRO', 'CX-F3', 'C-ROOT X', 'CX-B1', 'C-PUMA INT',
        'DB-686 NK', 'C-CRACK', 'CX-W1', 'C-BOND', 'C-TEMP',
        'CX-PRO', 'C-LUX', 'CX-MAX', 'DB-686 AIR', 'C-SPIN',
        'CX-FX', 'C-SPEED', 'C-WAVE', 'C-FLOW', 'C-SMART-3',
        'CX-R1', 'DB-688', 'C-ZOOM', 'C-PEEK', 'C-FORCE',
        'CX-T1', 'C-SENSE', 'CX-NANO', 'C-GLOW', 'C-MESH',
        'CX-CORE', 'C-LINK', 'DB-690', 'C-MAX', 'C-FLEX Pro',
        'CX-EDGE', 'C-PLUS', 'C-ELITE', 'C-TECH', 'DB-692',
        'C-PRIME', 'CX-VISION', 'C-SCOPE', 'C-PEAK', 'C-NOVA',
    ]

    wh_models = [
        'Synea Vision TK-100', 'Alegra TE-95', 'Synea TA-98', 'Alegra TE-97', 'Synea Fusion TK-94',
        'Synea TA-98 LED', 'Alegra TE-98', 'Synea TA-90', 'Alegra TE-90', 'Synea Vision WK-99',
        'Synea TA-85', 'Alegra TE-85', 'Synea WK-93', 'Alegra WK-92', 'Synea Fusion TA-91',
        'Alegra TE-99', 'Synea TA-97', 'Synea WK-97', 'Alegra WK-95', 'Synea Fusion WK-90',
        'Synea TA-99 LED', 'Alegra TE-100', 'Synea TA-96', 'Alegra WK-98', 'Synea WK-99 LED',
        'Synea TA-94', 'Alegra TE-96', 'Synea WK-95', 'Alegra WK-96', 'Synea TA-93',
        'Alegra TE-94', 'Synea WK-92', 'Alegra WK-94', 'Synea Fusion TA-98', 'Alegra TE-93',
        'Synea TA-92', 'Synea WK-91', 'Alegra TE-92', 'Synea WK-98 LED', 'Alegra WK-97',
        'Synea TA-91', 'Alegra TE-91', 'Synea WK-90', 'Alegra WK-93', 'Synea TA-95 LED',
        'Alegra WK-99', 'Synea Fusion TE-100', 'Synea TA-89', 'Alegra TE-89', 'Synea WK-89',
        'Alegra WK-88', 'Synea TA-88', 'Alegra TE-88', 'Synea WK-88', 'Alegra WK-87',
        'Synea Fusion TE-99', 'Synea TA-87', 'Synea WK-87', 'Alegra WK-86', 'Synea TA-86',
        'Alegra TE-87', 'Synea WK-86', 'Synea Fusion WK-85', 'Alegra WK-85', 'Synea TA-84',
        'Alegra TE-86', 'Synea WK-84', 'Alegra WK-84', 'Synea TA-83', 'Alegra TE-84',
        'Synea Fusion WK-95', 'Synea WK-83', 'Synea TA-82', 'Alegra WK-83', 'Alegra TE-83',
        'Synea WK-82', 'Alegra WK-82', 'Synea TA-81', 'Synea Fusion TE-95', 'Alegra TE-82',
        'Synea WK-81', 'Alegra WK-81', 'Synea TA-80', 'Alegra TE-81', 'Synea WK-80',
        'Alegra WK-80', 'Synea TA-79', 'Alegra TE-80', 'Synea WK-79', 'Synea Fusion TA-90',
        'Alegra WK-79', 'Synea TA-78', 'Alegra TE-79', 'Synea WK-78', 'Synea Fusion WK-75',
        'Alegra WK-78', 'Synea TA-77', 'Alegra TE-78', 'Synea WK-77', 'Synea Fusion TE-90',
    ]

    products = []
    for i in range(count):
        brand = brands[i % len(brands)]
        per_brand = i // len(brands)
        cat = categories[per_brand % len(categories)]
        prefix = brand.lower().replace('&', '') + '_'

        if brand == 'NSK':
            model = nsk_models[per_brand % len(nsk_models)]
        elif brand == 'COXO':
            model = coxo_models[per_brand % len(coxo_models)]
        else:
            model = wh_models[per_brand % len(wh_models)]

        code = model.replace(' ', '-').replace('&', '').upper()
        is_original = (brand == 'COXO')
        price_base = round((random.random() * 2500 + 50) * 100) / 100
        stock = random.randint(0, 25)

        products.append({
            'id': f'{prefix}{per_brand + 1}',
            'name': f'{brand} {model}',
            'brand': brand,
            'code': code,
            'category': cat,
            'isOriginal': is_original,
            'stock': stock,
            'basePrice': price_base,
        })

    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False)
    print(f'{count} products generated.')

if __name__ == '__main__':
    generate_products(300)
