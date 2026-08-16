"""Minimal HTTP health-check server for Render free web-service hosting.

Render's free tier only offers Web Services (not Background Workers), and a
Web Service must answer HTTP on $PORT or it is marked unhealthy and sleeps.
This module starts a tiny stdlib HTTP server in a daemon thread that returns
200 on every path (Render pings /healthz). It runs alongside the bot's
long-polling loop without needing FastAPI/Flask.
"""
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b"ok\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence request logs
        pass


def start() -> None:
    port = int(os.getenv("PORT", "10000") or "10000")
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="health-server")
    thread.start()
