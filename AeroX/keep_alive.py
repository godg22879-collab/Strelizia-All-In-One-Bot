import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Bot is online and running!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress HTTP request logs from cluttering bot logs

def start_keep_alive():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"[KeepAlive] Web server listening on 0.0.0.0:{port}")
    except Exception as e:
        print(f"[KeepAlive] Could not start web server on port {port}: {e}")
