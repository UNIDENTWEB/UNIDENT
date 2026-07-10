#!/bin/bash
# اسکریپت اجرای ربات اسکرپر

echo "starting unident scraper bot..."

# نصب وابستگی‌ها
pip install -r requirements.txt

# اجرای ربات
python scraper_bot.py

echo "operation completed."
