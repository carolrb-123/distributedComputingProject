import csv
import json
import threading
import time
from datetime import datetime
from typing import Dict, List

import requests

import config


class GPUMetricsCollector:
    def __init__(self, urls=None):
        self.urls = [url.rstrip("/") for url in (urls or config.GPU_METRICS_URLS)]
        self.latest: Dict[int, dict] = {}
        self.history: List[dict] = []
        self.lock = threading.Lock()
        self._running = False
        self._thread = None

    def start(self):
        if not self.urls or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def poll_once(self):
        for worker_id, base_url in enumerate(self.urls):
            sample = self._fetch(worker_id, base_url)
            with self.lock:
                self.latest[worker_id] = sample
                self.history.append(sample)

    def snapshot(self):
        with self.lock:
            return {
                "latest": dict(self.latest),
                "history_count": len(self.history),
            }

    def save_history_json(self, filepath):
        with self.lock:
            data = list(self.history)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def save_history_csv(self, filepath):
        rows = []
        with self.lock:
            history = list(self.history)

        for sample in history:
            for gpu in sample.get("gpus", []):
                rows.append({
                    "timestamp": sample.get("timestamp"),
                    "worker_id": sample.get("worker_id"),
                    "url": sample.get("url"),
                    "ok": sample.get("ok"),
                    "host": sample.get("host"),
                    "gpu_index": gpu.get("index"),
                    "gpu_name": gpu.get("name"),
                    "gpu_utilization_percent": gpu.get("utilization_gpu_percent"),
                    "memory_utilization_percent": gpu.get("utilization_memory_percent"),
                    "memory_used_mb": gpu.get("memory_used_mb"),
                    "memory_total_mb": gpu.get("memory_total_mb"),
                    "temperature_c": gpu.get("temperature_c"),
                    "power_draw_w": gpu.get("power_draw_w"),
                    "error": sample.get("error"),
                })

        fieldnames = [
            "timestamp",
            "worker_id",
            "url",
            "ok",
            "host",
            "gpu_index",
            "gpu_name",
            "gpu_utilization_percent",
            "memory_utilization_percent",
            "memory_used_mb",
            "memory_total_mb",
            "temperature_c",
            "power_draw_w",
            "error",
        ]
        with open(filepath, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _poll_loop(self):
        while self._running:
            self.poll_once()
            time.sleep(config.GPU_METRICS_INTERVAL)

    def _fetch(self, worker_id, base_url):
        metrics_path = config.GPU_METRICS_PATH
        if not metrics_path.startswith("/"):
            metrics_path = f"/{metrics_path}"
        url = f"{base_url}{metrics_path}"

        sample = {
            "timestamp": datetime.now().isoformat(),
            "worker_id": worker_id,
            "url": url,
            "ok": False,
            "host": None,
            "gpus": [],
            "error": None,
        }

        try:
            response = requests.get(url, timeout=config.GPU_METRICS_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
            sample.update({
                "ok": True,
                "host": payload.get("host"),
                "gpus": payload.get("gpus", []),
                "raw": payload,
            })
        except Exception as exc:
            sample["error"] = str(exc)

        return sample
