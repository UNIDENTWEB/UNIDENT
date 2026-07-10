"""
🤖 ربات هوشمند دریافت و آپلود تصاویر محصولات (نسخه All-in-One)
✅ بدون نیاز به فایل‌های جداگانه - فقط این یک فایل را اجرا کنید
"""

import os
import json
import requests
import time
import re
import hashlib
import threading
import schedule
from datetime import datetime
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify

# ============================================================
#  تنظیمات
# ============================================================
CONFIG = {
    'PRODUCTS_FILE': 'products.json',
    'OUTPUT_DIR': 'images',
    'MAPPING_FILE': 'image_mapping.json',
    'MIN_IMAGES': 3,
    'MAX_IMAGES': 5,
    'SEARCH_TIMEOUT': 15,
    'DELAY': 1,
    'AUTO_CHECK_INTERVAL': 3600,  # 1 ساعت
    'SERVER_HOST': 'your-server.com',
    'SERVER_USER': 'username',
    'SERVER_PASS': 'password',
    'SERVER_PATH': '/public_html/images/',
    'UNSPLASH_API_KEY': '',  # اختیاری
}

# ============================================================
#  کلاس ربات اصلی
# ============================================================
class SmartImageBot:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.products = []
        self.pending = []
        self.approved = []
        self.rejected = []
        self.mapping = {}
        self.load_state()
        self.load_products()
        
    def load_products(self):
        try:
            with open(CONFIG['PRODUCTS_FILE'], 'r', encoding='utf-8') as f:
                self.products = json.load(f)
            print(f"✅ {len(self.products)} محصول بارگذاری شد")
        except (FileNotFoundError, json.JSONDecodeError):
            print("products.json not found! Creating sample...")
            self.create_sample_products()
            
    def create_sample_products(self):
        """ایجاد نمونه products.json برای تست"""
        sample = []
        for i in range(10):
            sample.append({
                'id': f'coxo_{i+1}',
                'name': f'COXO CX207-{chr(65+i)} Handpiece',
                'brand': 'COXO',
                'code': f'CX207-{chr(65+i)}',
                'model': f'cx207-{chr(65+i)}-handpiece'
            })
        with open(CONFIG['PRODUCTS_FILE'], 'w', encoding='utf-8') as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)
        self.products = sample
        print(f"✅ نمونه {len(sample)} محصول ساخته شد")
        
    def load_state(self):
        try:
            with open('approval_state.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.pending = data.get('pending', [])
                self.approved = data.get('approved', [])
                self.rejected = data.get('rejected', [])
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    def save_state(self):
        with open('approval_state.json', 'w', encoding='utf-8') as f:
            json.dump({
                'pending': self.pending,
                'approved': self.approved,
                'rejected': self.rejected
            }, f, ensure_ascii=False, indent=2)
    
    def find_images(self, product):
        """جستجوی تصاویر برای یک محصول"""
        brand = product.get('brand', '')
        name = product.get('name', '')
        code = product.get('code', '')
        
        print(f"🔍 جستجوی {brand} - {name}")
        all_images = []
        
        # ۱. جستجو در سایت برند (coxotec.com)
        if brand == 'COXO':
            slug = name.lower().replace(' ', '-').replace('/', '-')
            slug = re.sub(r'[^\w\-]', '', slug)
            url = f"https://coxotec.com/product/{slug}/"
            images = self.extract_from_page(url)
            all_images.extend(images)
            print(f"   📸 از coxotec: {len(images)}")
        
        # ۲. جستجوی گوگل (با کلمات کلیدی)
        google_images = self.search_google(f"{brand} {name} {code} dental")
        all_images.extend(google_images)
        print(f"   📸 از گوگل: {len(google_images)}")
        
        # ۳. حذف تکراری‌ها
        unique = []
        seen = set()
        for img in all_images:
            if img not in seen:
                seen.add(img)
                unique.append(img)
        
        return unique[:CONFIG['MAX_IMAGES']]
    
    def extract_from_page(self, url):
        """استخراج تصاویر از یک صفحه وب"""
        images = []
        try:
            response = self.session.get(url, timeout=CONFIG['SEARCH_TIMEOUT'])
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # og:image
            og = soup.find('meta', property='og:image')
            if og and og.get('content'):
                images.append(og['content'])
            
            # تمام تصاویر با کیفیت
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src')
                if src:
                    full = urljoin(url, src)
                    if not any(x in full.lower() for x in ['logo', 'icon', 'thumb', 'small']):
                        images.append(full)
            
            # JSON-LD
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if 'image' in data:
                        if isinstance(data['image'], str):
                            images.append(data['image'])
                        elif isinstance(data['image'], list):
                            for img in data['image']:
                                if isinstance(img, dict) and 'url' in img:
                                    images.append(img['url'])
                except (json.JSONDecodeError, AttributeError):
                    pass
            
            return images[:10]
        except requests.RequestException:
            return []
    
    def search_google(self, query):
        """جستجوی تصاویر در گوگل (با استفاده از کتابخانه googlesearch)"""
        try:
            import googlesearch
            images = []
            search_query = f"{query} -logo -brand -watermark"
            results = googlesearch.search(search_query, num_results=8)
            
            for url in results:
                try:
                    response = self.session.get(url, timeout=5)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for img in soup.find_all('img'):
                        src = img.get('src') or img.get('data-src')
                        if src and any(ext in src.lower() for ext in ['.jpg', '.png', '.webp']):
                            full = urljoin(url, src)
                            if not any(x in full.lower() for x in ['logo', 'icon']):
                                images.append(full)
                except requests.RequestException:
                    continue
                if len(images) >= 5:
                    break
            return images[:5]
        except (ImportError, requests.RequestException):
            return []
    
    def download_images(self, product_id, image_urls):
        """دانلود و ذخیره تصاویر در پوشه موقت"""
        temp_folder = os.path.join('temp', product_id)
        os.makedirs(temp_folder, exist_ok=True)
        
        saved = []
        for i, url in enumerate(image_urls[:CONFIG['MAX_IMAGES']], 1):
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    # تشخیص پسوند
                    content_type = response.headers.get('content-type', '')
                    ext = 'jpg'
                    if 'png' in content_type:
                        ext = 'png'
                    elif 'webp' in content_type:
                        ext = 'webp'
                    
                    filename = f"{i}.{ext}"
                    path = os.path.join(temp_folder, filename)
                    with open(path, 'wb') as f:
                        f.write(response.content)
                    saved.append(path)
                    print(f"   ✅ دانلود: {filename}")
            except Exception as e:
                print(f"   ❌ خطا: {e}")
        
        return saved
    
    def process_new_products(self):
        """پیدا و پردازش محصولات جدید"""
        new_products = []
        for p in self.products:
            pid = p.get('id', '')
            # بررسی وجود تصویر در مپینگ
            if pid not in self.mapping:
                # بررسی در پوشه
                img_folder = os.path.join(CONFIG['OUTPUT_DIR'], pid)
                if not os.path.exists(img_folder) or len(os.listdir(img_folder)) < CONFIG['MIN_IMAGES']:
                    new_products.append(p)
        
        if not new_products:
            print("✅ همه محصولات تصویر دارند!")
            return
        
        print(f"\n🔄 پردازش {len(new_products)} محصول جدید...")
        
        for product in new_products:
            pid = product.get('id', '')
            print(f"\n📦 {product.get('name', '')}")
            
            images = self.find_images(product)
            if len(images) >= CONFIG['MIN_IMAGES']:
                # دانلود موقت
                saved = self.download_images(pid, images)
                if len(saved) >= CONFIG['MIN_IMAGES']:
                    # افزودن به لیست تایید
                    self.pending.append({
                        'product_id': pid,
                        'name': product.get('name', ''),
                        'brand': product.get('brand', ''),
                        'images': saved,
                        'image_urls': images[:CONFIG['MAX_IMAGES']],
                        'timestamp': datetime.now().isoformat()
                    })
                    self.save_state()
                    print(f"   📋 برای تایید به پنل رفت")
            else:
                print(f"   ⚠️ تعداد تصاویر کافی نیست ({len(images)})")
    
    def approve_product(self, product_id):
        """تایید تصاویر یک محصول"""
        for item in self.pending:
            if item['product_id'] == product_id:
                # انتقال به تایید شده
                self.approved.append(item)
                self.pending.remove(item)
                
                # انتقال به پوشه نهایی
                src_folder = os.path.join('temp', product_id)
                dst_folder = os.path.join(CONFIG['OUTPUT_DIR'], product_id)
                os.makedirs(dst_folder, exist_ok=True)
                
                for f in os.listdir(src_folder):
                    src = os.path.join(src_folder, f)
                    dst = os.path.join(dst_folder, f)
                    os.rename(src, dst)
                
                # حذف پوشه موقت
                try:
                    os.rmdir(src_folder)
                except OSError:
                    pass

                # به‌روزرسانی مپینگ
                self.mapping[product_id] = {
                    'name': item.get('name', ''),
                    'brand': item.get('brand', ''),
                    'images': [os.path.join(CONFIG['OUTPUT_DIR'], product_id, f) 
                              for f in os.listdir(dst_folder)]
                }
                self.save_mapping()
                self.save_state()
                return True
        return False
    
    def reject_product(self, product_id):
        """رد تصاویر یک محصول"""
        for item in self.pending:
            if item['product_id'] == product_id:
                self.rejected.append(item)
                self.pending.remove(item)
                
                # حذف پوشه موقت
                import shutil
                try:
                    shutil.rmtree(os.path.join('temp', product_id))
                except OSError:
                    pass
                return True
        return False
    
    def save_mapping(self):
        with open(CONFIG['MAPPING_FILE'], 'w', encoding='utf-8') as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)
    
    def upload_all(self):
        """آپلود همه تصاویر تایید شده به سرور"""
        if not self.approved:
            print("❌ هیچ تصویر تایید شده‌ای وجود ندارد")
            return False
        
        print(f"📤 آپلود {len(self.approved)} محصول...")
        try:
            # آپلود با SFTP
            import paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=CONFIG['SERVER_HOST'],
                username=CONFIG['SERVER_USER'],
                password=CONFIG['SERVER_PASS']
            )
            sftp = ssh.open_sftp()
            
            for root, dirs, files in os.walk(CONFIG['OUTPUT_DIR']):
                for file in files:
                    local = os.path.join(root, file)
                    remote = os.path.join(CONFIG['SERVER_PATH'], file)
                    sftp.put(local, remote)
                    print(f"   ✅ {file}")
            
            sftp.close()
            ssh.close()
            print("All images uploaded")
            return True
        except Exception:
            print("Upload error (check server settings)")
            return False


# ============================================================
#  پنل مدیریت وب (Flask)
# ============================================================
app = Flask(__name__)
bot = SmartImageBot()

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE, 
                                 pending=bot.pending,
                                 approved=bot.approved,
                                 rejected=bot.rejected)

@app.route('/approve/<product_id>', methods=['POST'])
def approve(product_id):
    if bot.approve_product(product_id):
        return jsonify({'status': 'success', 'message': 'تایید شد'})
    return jsonify({'status': 'error', 'message': 'خطا'})

@app.route('/reject/<product_id>', methods=['POST'])
def reject(product_id):
    if bot.reject_product(product_id):
        return jsonify({'status': 'success', 'message': 'رد شد'})
    return jsonify({'status': 'error', 'message': 'خطا'})

@app.route('/upload', methods=['POST'])
def upload():
    if bot.upload_all():
        return jsonify({'status': 'success', 'message': 'آپلود شد'})
    return jsonify({'status': 'error', 'message': 'خطا در آپلود'})

# ============================================================
#  قالب HTML پنل مدیریت (داخل خود فایل Python)
# ============================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>پنل مدیریت تصاویر</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:Tahoma,sans-serif; background:#0a0a0a; color:#fff; padding:20px; }
        .container { max-width:1400px; margin:0 auto; }
        h1 { color:#c8a96a; margin-bottom:30px; }
        .stats { display:flex; gap:20px; margin-bottom:30px; flex-wrap:wrap; }
        .stat-box { background:#1a1a1a; padding:20px 30px; border-radius:12px; border:1px solid #333; flex:1; min-width:150px; text-align:center; }
        .stat-box .number { font-size:2rem; font-weight:bold; color:#c8a96a; }
        .stat-box .label { color:#888; margin-top:5px; }
        .product-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:20px; }
        .product-card { background:#1a1a1a; border-radius:12px; padding:20px; border:1px solid #333; }
        .product-card:hover { border-color:#c8a96a; transform:translateY(-5px); }
        .product-card h3 { color:#c8a96a; font-size:1.1rem; margin-bottom:10px; }
        .product-card .images { display:flex; gap:10px; flex-wrap:wrap; margin:10px 0; }
        .product-card .images img { width:80px; height:80px; object-fit:cover; border-radius:8px; border:1px solid #333; }
        .btn { padding:8px 20px; border:none; border-radius:8px; cursor:pointer; font-weight:bold; }
        .btn-approve { background:#22c55e; color:#000; }
        .btn-approve:hover { background:#16a34a; }
        .btn-reject { background:#ef4444; color:#fff; }
        .btn-reject:hover { background:#dc2626; }
        .btn-upload { background:#c8a96a; color:#000; padding:10px 30px; font-size:1.1rem; margin-top:20px; }
        .tab { display:flex; gap:10px; margin-bottom:20px; border-bottom:1px solid #333; padding-bottom:10px; }
        .tab button { background:transparent; color:#888; border:none; padding:10px 20px; cursor:pointer; border-radius:8px; }
        .tab button:hover { background:#2a2a2a; }
        .tab button.active { background:#c8a96a; color:#000; }
        .tab-content { display:none; }
        .tab-content.active { display:block; }
        .empty { color:#666; text-align:center; padding:40px; }
        .status-pending { color:#facc15; }
        .status-approved { color:#22c55e; }
        .status-rejected { color:#ef4444; }
    </style>
</head>
<body>
<div class="container">
    <h1>🖼️ پنل مدیریت تصاویر</h1>
    <div class="stats">
        <div class="stat-box"><div class="number">{{ pending|length }}</div><div class="label">در انتظار تایید</div></div>
        <div class="stat-box"><div class="number">{{ approved|length }}</div><div class="label">تایید شده</div></div>
        <div class="stat-box"><div class="number">{{ rejected|length }}</div><div class="label">رد شده</div></div>
    </div>

    <div class="tab">
        <button class="active" onclick="showTab('pending')">در انتظار تایید ({{ pending|length }})</button>
        <button onclick="showTab('approved')">تایید شده ({{ approved|length }})</button>
        <button onclick="showTab('rejected')">رد شده ({{ rejected|length }})</button>
    </div>

    <div id="tab-pending" class="tab-content active">
        {% if pending %}
            <div class="product-grid">
            {% for item in pending %}
                <div class="product-card">
                    <h3>#{{ item.product_id }} - {{ item.name }}</h3>
                    <div class="images">
                        {% for img in item.images[:3] %}
                            <img src="{{ img }}" alt="تصویر" onerror="this.style.display='none'">
                        {% endfor %}
                    </div>
                    <div class="actions" style="margin-top:10px;">
                        <button class="btn btn-approve" onclick="approve('{{ item.product_id }}')">✅ تایید</button>
                        <button class="btn btn-reject" onclick="reject('{{ item.product_id }}')">❌ رد</button>
                    </div>
                </div>
            {% endfor %}
            </div>
        {% else %}
            <div class="empty">هیچ محصولی در انتظار تایید نیست</div>
        {% endif %}
    </div>

    <div id="tab-approved" class="tab-content">
        {% if approved %}
            <div class="product-grid">
            {% for item in approved %}
                <div class="product-card" style="border-color:#22c55e;">
                    <h3>#{{ item.product_id }} - {{ item.name }}</h3>
                    <div style="color:#22c55e;">✅ تایید شده</div>
                </div>
            {% endfor %}
            </div>
            <button class="btn btn-upload" onclick="uploadAll()">📤 آپلود همه تصاویر تاییدشده</button>
        {% else %}
            <div class="empty">هیچ محصولی تایید نشده است</div>
        {% endif %}
    </div>

    <div id="tab-rejected" class="tab-content">
        {% if rejected %}
            <div class="product-grid">
            {% for item in rejected %}
                <div class="product-card" style="border-color:#ef4444;">
                    <h3>#{{ item.product_id }}</h3>
                    <div style="color:#ef4444;">❌ رد شده</div>
                </div>
            {% endfor %}
            </div>
        {% else %}
            <div class="empty">هیچ محصولی رد نشده است</div>
        {% endif %}
    </div>
</div>

<script>
function showTab(tab) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-'+tab).classList.add('active');
    document.querySelectorAll('.tab button').forEach(el => el.classList.remove('active'));
    document.querySelector(`.tab button[onclick*="${tab}"]`).classList.add('active');
}

function approve(id) {
    fetch('/approve/'+id, {method:'POST'}).then(r=>r.json()).then(data=>{
        if(data.status==='success') location.reload();
        else alert('خطا');
    });
}

function reject(id) {
    if(!confirm('رد شود؟')) return;
    fetch('/reject/'+id, {method:'POST'}).then(r=>r.json()).then(data=>{
        if(data.status==='success') location.reload();
        else alert('خطا');
    });
}

function uploadAll() {
    if(!confirm('آپلود شود؟')) return;
    fetch('/upload', {method:'POST'}).then(r=>r.json()).then(data=>{
        alert(data.status==='success' ? '✅ آپلود شد!' : '❌ خطا');
    });
}
</script>
</body>
</html>
"""

# ============================================================
#  اجرای اصلی
# ============================================================
def main():
    print("="*60)
    print("🤖 ربات هوشمند دریافت تصاویر محصولات")
    print("="*60)
    
    # ایجاد پوشه‌های مورد نیاز
    os.makedirs(CONFIG['OUTPUT_DIR'], exist_ok=True)
    os.makedirs('temp', exist_ok=True)
    
    # اجرای اولیه
    bot.process_new_products()
    
    # اجرای پنل مدیریت در یک ترد جداگانه
    def run_flask():
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("\n🌐 پنل مدیریت: http://localhost:5000")
    print("⏱️ اسکن خودکار هر 1 ساعت")
    print("\n✅ ربات در حال اجرا است... (Ctrl+C برای خروج)")
    
    # زمان‌بندی
    import schedule
    schedule.every(CONFIG['AUTO_CHECK_INTERVAL']).seconds.do(bot.process_new_products)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n👋 ربات متوقف شد")

if __name__ == "__main__":
    main()
