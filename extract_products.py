import json
import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

products = []

brand_blocks = re.findall(
    r"const\s+\w+\s*=\s*\[([\s\S]*?)\];",
    html
)

push_pattern = re.compile(r"products\.push\(\{([^}]+(?:'[^']*'[^}]*)*)\}\)", re.MULTILINE)

found_any = False
for block in brand_blocks:
    for match in push_pattern.finditer(block):
        found_any = True
        raw = match.group(1)
        fields = {}
        field_pat = re.compile(r"(\w+)\s*:\s*(.+?)(?=\s*,\s*\w+\s*:|\s*$)")
        for fm in field_pat.finditer(raw):
            key = fm.group(1)
            val = fm.group(2).strip().rstrip(',')
            val = val.strip("'").strip('"')
            fields[key] = val
        if fields:
            products.append(fields)

if not found_any:
    print("Could not extract products from HTML.")
    exit()

output = []
for p in products:
    output.append({
        'id': p.get('id', ''),
        'name': p.get('name', ''),
        'brand': p.get('brand', ''),
        'code': p.get('code', '')
    })

with open('products.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"{len(output)} products extracted and saved to products.json")
