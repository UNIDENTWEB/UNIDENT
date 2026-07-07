import os, json, requests, time, re, threading
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from flask import Flask, render_template, request, jsonify

CONFIG = {
    'PRODUCTS_FILE': 'products.json',
    'OUTPUT_DIR': 'images',
    'MAPPING_FILE': 'image_mapping.json',
    'MIN_IMAGES': 3,
    'MAX_IMAGES': 5,
}

class Bot:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
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
            print(f"✅ {len(self.products)} محصول")
        except:
            print("❌ products.json یافت نشد")
    
    def load_state(self):
        try:
            with open('approval_state.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.pending = data.get('pending', [])
                self.approved = data.get('approved', [])
                self.rejected = data.get('rejected', [])
        except:
            pass
    
    def save_state(self):
        with open('approval_state.json', 'w', encoding='utf-8') as f:
            json.dump({'pending':self.pending,'approved':self.approved,'rejected':self.rejected}, f, ensure_ascii=False, indent=2)
    
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
                    if not any(x in full.lower() for x in ['logo','icon','thumb']):
                        images.append(full)
            return images[:10]
        except: return []
    
    def find_images(self, product):
        brand = product.get('brand', '')
        name = product.get('name', '')
        all_images = []
        if brand == 'COXO':
            slug = re.sub(r'[^\w\-]', '', name.lower().replace(' ', '-').replace('/', '-'))
            url = f"https://coxotec.com/product/{slug}/"
            all_images = self.extract_from_page(url)
        return all_images[:CONFIG['MAX_IMAGES']]
    
    def download_images(self, pid, urls):
        folder = os.path.join('temp', pid)
        os.makedirs(folder, exist_ok=True)
        saved = []
        for i, url in enumerate(urls[:CONFIG['MAX_IMAGES']], 1):
            try:
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    ext = 'jpg'
                    if 'png' in r.headers.get('content-type',''): ext='png'
                    elif 'webp' in r.headers.get('content-type',''): ext='webp'
                    path = os.path.join(folder, f"{i}.{ext}")
                    with open(path, 'wb') as f: f.write(r.content)
                    saved.append(path)
            except: pass
        return saved
    
    def process_new_products(self):
        new = []
        for p in self.products:
            pid = p.get('id','')
            if pid not in self.mapping:
                folder = os.path.join(CONFIG['OUTPUT_DIR'], pid)
                if not os.path.exists(folder) or len(os.listdir(folder)) < CONFIG['MIN_IMAGES']:
                    new.append(p)
        if not new: return
        for p in new:
            pid = p.get('id','')
            images = self.find_images(p)
            if len(images) >= CONFIG['MIN_IMAGES']:
                saved = self.download_images(pid, images)
                if len(saved) >= CONFIG['MIN_IMAGES']:
                    self.pending.append({
                        'product_id': pid,
                        'name': p.get('name',''),
                        'brand': p.get('brand',''),
                        'images': saved,
                        'timestamp': str(time.time())
                    })
                    self.save_state()
    
    def approve_product(self, pid):
        for item in self.pending:
            if item['product_id'] == pid:
                self.approved.append(item)
                self.pending.remove(item)
                src = os.path.join('temp', pid)
                dst = os.path.join(CONFIG['OUTPUT_DIR'], pid)
                os.makedirs(dst, exist_ok=True)
                for f in os.listdir(src):
                    os.rename(os.path.join(src,f), os.path.join(dst,f))
                try: os.rmdir(src)
                except: pass
                self.mapping[pid] = {
                    'name': item.get('name',''),
                    'brand': item.get('brand',''),
                    'images': [os.path.join(CONFIG['OUTPUT_DIR'], pid, f) for f in os.listdir(dst)]
                }
                self.save_mapping()
                self.save_state()
                return True
        return False
    
    def reject_product(self, pid):
        for item in self.pending:
            if item['product_id'] == pid:
                self.rejected.append(item)
                self.pending.remove(item)
                import shutil
                try: shutil.rmtree(os.path.join('temp', pid))
                except: pass
                self.save_state()
                return True
        return False
    
    def save_mapping(self):
        with open(CONFIG['MAPPING_FILE'], 'w', encoding='utf-8') as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)

app = Flask(__name__)
bot = Bot()

@app.route('/')
def index():
    return render_template_string(HTML, pending=bot.pending, approved=bot.approved, rejected=bot.rejected)

@app.route('/approve/<pid>', methods=['POST'])
def approve(pid):
    return jsonify({'status':'success' if bot.approve_product(pid) else 'error'})

@app.route('/reject/<pid>', methods=['POST'])
def reject(pid):
    return jsonify({'status':'success' if bot.reject_product(pid) else 'error'})

HTML = """
<!DOCTYPE html>
<html dir="rtl"><head><meta charset="UTF-8"><title>پنل تصاویر</title>
<style>
body{background:#0a0a0a;color:#fff;font-family:Tahoma;padding:20px}
h1{color:#c8a96a}
.stats{display:flex;gap:20px;flex-wrap:wrap}
.stat-box{background:#1a1a1a;padding:20px;border-radius:12px;border:1px solid #333;flex:1;min-width:120px;text-align:center}
.stat-box .number{font-size:2rem;color:#c8a96a;font-weight:bold}
.product-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px}
.product-card{background:#1a1a1a;padding:20px;border-radius:12px;border:1px solid #333}
.product-card .images{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}
.product-card .images img{width:80px;height:80px;object-fit:cover;border-radius:8px}
.btn{padding:8px 20px;border:none;border-radius:8px;cursor:pointer;font-weight:bold}
.btn-approve{background:#22c55e;color:#000}
.btn-reject{background:#ef4444;color:#fff}
.tab{display:flex;gap:10px;margin-bottom:20px}
.tab button{background:transparent;color:#888;border:none;padding:10px 20px;cursor:pointer}
.tab button.active{background:#c8a96a;color:#000}
.tab-content{display:none}
.tab-content.active{display:block}
.empty{color:#666;text-align:center;padding:40px}
</style>
</head>
<body>
<div class="container">
<h1>🖼️ پنل مدیریت تصاویر</h1>
<div class="stats">
<div class="stat-box"><div class="number">{{ pending|length }}</div><div class="label">در انتظار</div></div>
<div class="stat-box"><div class="number">{{ approved|length }}</div><div class="label">تایید شده</div></div>
<div class="stat-box"><div class="number">{{ rejected|length }}</div><div class="label">رد شده</div></div>
</div>
<div class="tab">
<button class="active" onclick="showTab('pending')">در انتظار ({{ pending|length }})</button>
<button onclick="showTab('approved')">تایید ({{ approved|length }})</button>
<button onclick="showTab('rejected')">رد ({{ rejected|length }})</button>
</div>
<div id="tab-pending" class="tab-content active">
{% if pending %}
<div class="product-grid">
{% for item in pending %}
<div class="product-card">
<h3>{{ item.product_id }} - {{ item.name }}</h3>
<div class="images">{% for img in item.images[:3] %}<img src="{{ img }}" onerror="this.style.display='none'">{% endfor %}</div>
<button class="btn btn-approve" onclick="approve('{{ item.product_id }}')">✅ تایید</button>
<button class="btn btn-reject" onclick="reject('{{ item.product_id }}')">❌ رد</button>
</div>
{% endfor %}
</div>
{% else %}<div class="empty">هیچ محصولی در انتظار نیست</div>{% endif %}
</div>
<div id="tab-approved" class="tab-content">
{% if approved %}{% for item in approved %}<div class="product-card" style="border-color:#22c55e"><h3>{{ item.product_id }}</h3><div style="color:#22c55e">✅ تایید</div></div>{% endfor %}{% else %}<div class="empty">هیچ</div>{% endif %}
</div>
<div id="tab-rejected" class="tab-content">
{% if rejected %}{% for item in rejected %}<div class="product-card" style="border-color:#ef4444"><h3>{{ item.product_id }}</h3><div style="color:#ef4444">❌ رد</div></div>{% endfor %}{% else %}<div class="empty">هیچ</div>{% endif %}
</div>
</div>
<script>
function showTab(t){document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));document.getElementById('tab-'+t).classList.add('active');document.querySelectorAll('.tab button').forEach(e=>e.classList.remove('active'));document.querySelector(`.tab button[onclick*="${t}"]`).classList.add('active')}
function approve(id){fetch('/approve/'+id,{method:'POST'}).then(r=>r.json()).then(d=>{if(d.status==='success')location.reload()})}
function reject(id){if(!confirm('رد شود؟'))return;fetch('/reject/'+id,{method:'POST'}).then(r=>r.json()).then(d=>{if(d.status==='success')location.reload()})}
</script>
</body>
</html>
"""

if __name__ == "__main__":
    os.makedirs(CONFIG['OUTPUT_DIR'], exist_ok=True)
    os.makedirs('temp', exist_ok=True)
    bot.process_new_products()
    app.run(host='0.0.0.0', port=5000, debug=False)
