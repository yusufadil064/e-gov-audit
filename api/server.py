"""
GovBudgetAPI Server
Simple HTTP API server using Python stdlib (http.server).
Serves both the frontend HTML and the /api/analyze endpoint.

Endpoints:
  GET  /            → serves index.html
  GET  /static/*    → serves static assets
  POST /api/analyze → { "url": "..." } → JSON analysis result
"""

import json
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from flask import Flask, jsonify, request


# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.analyzers.orchestrator import WebsiteAnalysisOrchestrator

ORCHESTRATOR = WebsiteAnalysisOrchestrator()
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")


class GovBudgetHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the GovBudget API."""

    def log_message(self, format, *args):
        # Suppress default access log noise
        print(f"  [{self.address_string()}] {format % args}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_file(os.path.join(FRONTEND_DIR, "index.html"), "text/html")
        elif path.startswith("/static/"):
            file_path = os.path.join(FRONTEND_DIR, path.lstrip("/"))
            if os.path.exists(file_path):
                ctype = self._mime_type(file_path)
                self._serve_file(file_path, ctype)
            else:
                self._send_404()
        else:
            self._send_404()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/analyze":
            self._handle_analyze()
        else:
            self._send_404()

    def do_OPTIONS(self):
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()

    def _handle_analyze(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            url = data.get("url", "").strip()
            if not url:
                self._send_json({"success": False, "error": "URL is required"}, 400)
                return

            print(f"\n🔍 Analyzing: {url}")
            result = ORCHESTRATOR.analyze(url)
            print(f"✅ Done: {result.get('agency_name', url)}")
            self._send_json(result)

        except json.JSONDecodeError:
            self._send_json({"success": False, "error": "Invalid JSON body"}, 400)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send_json({"success": False, "error": str(e)}, 500)

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, file_path: str, content_type: str):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self._add_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._send_404()

    def _send_404(self):
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"404 Not Found")

    def _add_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    @staticmethod
    def _mime_type(path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        return {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
        }.get(ext, "application/octet-stream")


def run(host: str = "0.0.0.0", port: int = 8080):
    server = HTTPServer((host, port), GovBudgetHandler)
    print(f"\n{'='*60}")
    print(f"  🇮🇩  GovBudget Analyzer — Indonesian Government Website Audit")
    print(f"{'='*60}")
    print(f"  Server running at: http://localhost:{port}")
    print(f"  Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
        server.server_close()


app = FastAPI()
 
@app.get("/")
def read_root():
    return {"Python": "on Vercel"}


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run(port=port)
