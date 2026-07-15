#!/usr/bin/env python3
"""UNIDENT Cloud Server - static file server + GitHub data sync API"""

import http.server
import json
import os
import base64
import urllib.request
import urllib.error
import sys

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = "UNIDENTWEB/UNIDENT"
GITHUB_API = "https://api.github.com"
DATA_DIR = "data"

DATA_TYPES = [
    "products", "reviews", "orders", "users", "coupons",
    "warranties", "inquiries", "surveys", "subscribers",
    "settings", "customers",
]


class CloudHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_POST(self):
        if self.path == "/api/sync":
            self.handle_sync_single()
        elif self.path == "/api/sync-batch":
            self.handle_sync_batch()
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path.startswith("/api/status"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"status": "ok", "version": "1.0.0"}).encode()
            )
        elif self.path.startswith("/api/data/"):
            data_type = self.path.split("/api/data/", 1)[1].replace(".json", "")
            if data_type in DATA_TYPES:
                self.proxy_github_read(data_type)
            else:
                self.send_error(404)
        else:
            super().do_GET()

    def handle_sync_single(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body)
            data_type = payload.get("type", "")
            data = payload.get("data")

            if data_type not in DATA_TYPES:
                self.send_json({"error": f"Unknown data type: {data_type}"}, 400)
                return

            result = self.sync_to_github(data_type, data)
            if result.get("status") == "ok":
                self.send_json(result, 200)
            else:
                self.send_json(result, 500)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def handle_sync_batch(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            items = json.loads(body)

            results = {}
            for item in items:
                data_type = item.get("type", "")
                data = item.get("data")
                if data_type in DATA_TYPES:
                    results[data_type] = self.sync_to_github(data_type, data)
                else:
                    results[data_type] = {
                        "error": f"Unknown data type: {data_type}"
                    }

            self.send_json(results, 200)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def proxy_github_read(self, data_type):
        file_path = f"{DATA_DIR}/{data_type}.json"
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{file_path}"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.send_json({"error": "not found", "exists": False}, 404)
            else:
                self.send_json({"error": str(e), "status": e.code}, 500)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)

    def sync_to_github(self, data_type, data):
        file_path = f"{DATA_DIR}/{data_type}.json"
        url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{file_path}"

        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "UNIDENT-Cloud-Server/1.0",
        }

        sha = None
        get_req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(get_req) as resp:
                existing = json.loads(resp.read())
                sha = existing.get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                return {"error": f"GitHub read error: {e.code}", "status": e.code}

        content = json.dumps(data, ensure_ascii=False, indent=2)
        payload = {
            "message": f"sync: update {data_type}.json",
            "content": base64.b64encode(content.encode()).decode(),
        }
        if sha:
            payload["sha"] = sha

        put_req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={**headers, "Content-Type": "application/json"},
            method="PUT",
        )

        try:
            with urllib.request.urlopen(put_req) as resp:
                result = json.loads(resp.read())
                return {
                    "status": "ok",
                    "sha": result["content"]["sha"],
                    "path": file_path,
                }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            try:
                err = json.loads(error_body)
                return {
                    "error": err.get("message", str(e)),
                    "status": e.code,
                }
            except json.JSONDecodeError:
                return {"error": error_body[:200], "status": e.code}

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers", "Content-Type, Authorization"
        )
        self.end_headers()


if __name__ == "__main__":
    from functools import partial

    server = http.server.HTTPServer(("0.0.0.0", 8000), CloudHandler)
    print("UNIDENT Cloud Server running on http://0.0.0.0:8000")
    print(f"Static files: {os.getcwd()}")
    print(f"GitHub repo: {GITHUB_REPO}")
    print(f"Data types: {', '.join(DATA_TYPES)}")
    sys.stdout.flush()
    server.serve_forever()
