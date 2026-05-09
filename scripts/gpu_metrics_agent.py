#!/usr/bin/env python3
import json
import os
import socket
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = os.getenv("GPU_METRICS_AGENT_HOST", "0.0.0.0")
PORT = int(os.getenv("GPU_METRICS_AGENT_PORT", "9100"))


def _to_int(value):
    try:
        return int(float(value))
    except Exception:
        return None


def _to_float(value):
    try:
        return float(value)
    except Exception:
        return None


def read_gpu_metrics():
    query = ",".join([
        "index",
        "name",
        "uuid",
        "utilization.gpu",
        "utilization.memory",
        "memory.used",
        "memory.total",
        "temperature.gpu",
        "power.draw",
    ])
    cmd = [
        "nvidia-smi",
        f"--query-gpu={query}",
        "--format=csv,noheader,nounits",
    ]

    result = subprocess.run(cmd, text=True, capture_output=True, check=True)
    gpus = []

    for line in result.stdout.strip().splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) < 9:
            continue

        gpus.append({
            "index": _to_int(fields[0]),
            "name": fields[1],
            "uuid": fields[2],
            "utilization_gpu_percent": _to_int(fields[3]),
            "utilization_memory_percent": _to_int(fields[4]),
            "memory_used_mb": _to_int(fields[5]),
            "memory_total_mb": _to_int(fields[6]),
            "temperature_c": _to_int(fields[7]),
            "power_draw_w": _to_float(fields[8]),
        })

    return gpus


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in {"/", "/health", "/metrics"}:
            self.send_response(404)
            self.end_headers()
            return

        payload = {
            "timestamp": datetime.now().isoformat(),
            "host": socket.gethostname(),
            "ok": True,
            "gpus": [],
            "error": None,
        }

        if self.path == "/health":
            self._send_json(payload)
            return

        try:
            payload["gpus"] = read_gpu_metrics()
        except Exception as exc:
            payload["ok"] = False
            payload["error"] = str(exc)

        self._send_json(payload, status=200 if payload["ok"] else 503)

    def log_message(self, format, *args):
        return

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[GPU metrics agent] Listening on {HOST}:{PORT}")
    server.serve_forever()
