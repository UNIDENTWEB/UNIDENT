#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
آپلود خودکار فایل‌ها به مخزن گیت‌هاب
"""

import os
import json
import base64
import requests
from pathlib import Path

class GitHubUploader:
    """آپلود فایل به گیت‌هاب"""
    
    def __init__(self, token: str, repo: str, branch: str = 'main'):
        self.token = token
        self.repo = repo
        self.branch = branch
        self.api_base = 'https://api.github.com/repos'
        
    def upload_file(self, file_path: str, remote_path: str, commit_message: str) -> bool:
        """آپلود یک فایل به گیت‌هاب"""
        url = f"{self.api_base}/{self.repo}/contents/{remote_path}"
        
        with open(file_path, 'rb') as f:
            content = f.read()
        encoded = base64.b64encode(content).decode('utf-8')
        
        # دریافت SHA فایل موجود (برای به‌روزرسانی)
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        sha = None
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            sha = response.json().get('sha')
        
        data = {
            'message': commit_message,
            'content': encoded,
            'branch': self.branch
        }
        if sha:
            data['sha'] = sha
        
        response = requests.put(url, headers=headers, json=data)
        
        if response.status_code in [200, 201]:
            print(f"✅ آپلود شد: {remote_path}")
            return True
        else:
            print(f"❌ خطا در آپلود {remote_path}: {response.status_code}")
            return False

def main():
    # تنظیمات - این مقادیر را با اطلاعات خود جایگزین کنید
    TOKEN = os.environ.get('GITHUB_TOKEN', '')
    REPO = os.environ.get('GITHUB_REPO', 'UNIDENTWEB/UNIDENT')
    
    if not TOKEN or not REPO:
        print("⚠️ لطفاً متغیرهای محیطی GITHUB_TOKEN و GITHUB_REPO را تنظیم کنید.")
        print("   export GITHUB_TOKEN=your_token")
        print("   export GITHUB_REPO=your_username/repo_name")
        return
    
    uploader = GitHubUploader(TOKEN, REPO, branch='main')
    
    # لیست فایل‌های مورد نظر برای آپلود
    files_to_upload = [
        ('image_mapping.json', 'image_mapping.json', '🔄 به‌روزرسانی تصاویر محصولات'),
        ('scrape_results.json', 'scrape_results.json', '📊 ذخیره نتایج اسکرپ'),
    ]
    
    for local_path, remote_path, message in files_to_upload:
        if os.path.exists(local_path):
            uploader.upload_file(local_path, remote_path, message)
        else:
            print(f"⚠️ فایل {local_path} یافت نشد.")

if __name__ == '__main__':
    main()
