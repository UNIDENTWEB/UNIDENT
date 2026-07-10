#!/bin/bash
# اسکریپت اجرای ربات اسکرپر

echo "🦷 شروع ربات اسکرپر یونیدنت..."

# فعال کردن محیط مجازی (در صورت استفاده)
# source venv/bin/activate

# نصب وابستگی‌ها
pip install -r requirements.txt

# اجرای ربات
python scraper_bot.py

# آپلود به گیت‌هاب
python upload_to_github.py

echo "✅ عملیات کامل شد."
