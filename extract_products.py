import json
import re

# خواندن فایل index.html
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# پیدا کردن تابع generateProducts
match = re.search(r'function generateProducts\(\) \{([\s\S]*?)\n\s*return products;\n\s*\}', html)
if not match:
    print("❌ تابع generateProducts پیدا نشد")
    exit()

# استخراج آرایه products از داخل تابع
func_body = match.group(1)
# پیدا کردن جایی که products.push اتفاق می‌افتد
# ساده‌ترین روش: اجرای کد در یک محیط ایمن (استفاده از exec)

# ساخت یک محیط مجزا
namespace = {}
exec(func_body, namespace)

# حالا باید تابع را فراخوانی کنیم
# اما تابع به products نیاز دارد که در namespace نیست
# بهتر است کد را به صورت مستقیم اجرا کنیم

# روش جایگزین: استفاده از ast.literal_eval برای استخراج آرایه
# اما چون کد شامل متغیرها و حلقه‌هاست، باید اجرا شود

# راه‌حل: کل کد تابع را با یک wrapper اجرا کنیم
wrapper_code = f"""
def generate_products():
    {func_body}
    return products

result = generate_products()
"""
namespace = {}
exec(wrapper_code, namespace)
products = namespace.get('result', [])

if not products:
    print("❌ محصولات استخراج نشدند")
    exit()

# تبدیل به فرمت مورد نیاز ربات
output = []
for p in products:
    output.append({
        'id': p.get('id', ''),
        'name': p.get('name', ''),
        'brand': p.get('brand', ''),
        'code': p.get('code', '')
    })

# ذخیره در products.json
with open('products.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ {len(output)} محصول استخراج و در products.json ذخیره شد")
