import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class MonitoringDashboard:
    def __init__(self, host, port, metrics, scheduler, workers, load_balancer, gpu_monitor=None):
        self.host = host
        self.port = port
        self.metrics = metrics
        self.scheduler = scheduler
        self.workers = workers
        self.load_balancer = load_balancer
        self.gpu_monitor = gpu_monitor
        self._server = None
        self._thread = None

    def start(self):
        dashboard = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/api/status":
                    self._send_json(dashboard.status())
                    return
                if self.path == "/":
                    self._send_html(dashboard.html())
                    return
                self.send_response(404)
                self.end_headers()

            def log_message(self, format, *args):
                return

            def _send_json(self, payload):
                body = json.dumps(payload, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_html(self, html):
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        print(f"[Monitoring] Dashboard: http://{self.host}:{self.port}")

    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2)

    def status(self):
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics.get_summary(),
            "scheduler": self.scheduler.get_worker_status() if self.scheduler else {},
            "workers": [worker.get_status() for worker in self.workers],
            "load_balancer": self.load_balancer.get_status() if hasattr(self.load_balancer, "get_status") else {},
            "gpu": self.gpu_monitor.snapshot() if self.gpu_monitor else {},
        }

    def html(self):
        status = self.status()
        body = json.dumps(status, indent=2)
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="3">
  <title>Distributed LLM Monitor</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 24px; }}
    h1 {{ font-size: 24px; }}
    pre {{ background: #111827; color: #e5e7eb; padding: 16px; border-radius: 6px; overflow-x: auto; }}
  </style>
</head>
<body>
  <h1>Distributed LLM Monitor</h1>
  <p>Auto-refreshes every 3 seconds. JSON endpoint: <code>/api/status</code></p>
  <pre>{body}</pre>
</body>
</html>"""
