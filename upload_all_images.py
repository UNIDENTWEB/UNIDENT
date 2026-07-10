#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
آپلود مستقیم تصاویر محصولات به گیت‌هاب (در صورت نیاز)
"""

import os
import json
import base64
import requests
from pathlib import Path
from typing import Dict

class ImageUploader:
    """آپلود تصاویر به گیت‌هاب"""
    
    def __init__(self, token: str, repo: str, branch: str = 'main'):
        self.token = token
        self.repo = repo
        self.branch = branch
        self.api_base = 'https://api.github.com/repos'
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def upload_image(self, image_url: str, remote_path: str) -> bool:
        """آپلود یک تصویر به گیت‌هاب (از URL)"""
        try:
            # دانلود تصویر
            response = requests.get(image_url, timeout=30)
            if response.status_code != 200:
                print(f"❌ خطا در دانلود تصویر: {image_url}")
                return False
            
            # تبدیل به base64
            encoded = base64.b64encode(response.content).decode('utf-8')
            
            # آپلود به گیت‌هاب
            url = f"{self.api_base}/{self.repo}/contents/{remote_path}"
            
            # دریافت SHA (برای به‌روزرسانی)
            sha = None
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                sha = resp.json().get('sha')
            
            data = {
                'message': f'🖼️ آپلود تصویر: {remote_path}',
                'content': encoded,
                'branch': self.branch
            }
            if sha:
                data['sha'] = sha
            
            resp = requests.put(url, headers=self.headers, json=data)
            
            if resp.status_code in [200, 201]:
                print(f"✅ آپلود تصویر: {remote_path}")
                return True
            else:
                print(f"❌ خطا در آپلود {remote_path}: {resp.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ خطا: {e}")
            return False

def main():
    TOKEN = os.environ.get('GITHUB_TOKEN', '')
    REPO = os.environ.get('GITHUB_REPO', 'UNIDENTWEB/UNIDENT')
    
    if not TOKEN or not REPO:
        print("⚠️ لطفاً متغیرهای محیطی GITHUB_TOKEN و GITHUB_REPO را تنظیم کنید.")
        return
    
    uploader = ImageUploader(TOKEN, REPO)
    
    # بارگذاری mapping تصاویر
    try:
        with open('image_mapping.json', 'r', encoding='utf-8') as f:
            mapping = json.load(f)
    except FileNotFoundError:
        print("⚠️ فایل image_mapping.json یافت نشد.")
        return
    
    for product_id, info in mapping.items():
        images = info.get('images', [])
        for idx, img_url in enumerate(images):
            ext = img_url.split('.')[-1].split('?')[0] or 'jpg'
            remote_path = f'images/{product_id}_{idx}.{ext}'
            uploader.upload_image(img_url, remote_path)

if __name__ == '__main__':
    main()
