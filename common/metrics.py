#common/metrics.py
import json
from datetime import datetime
import threading
from typing import Dict, List

class MetricsCollector:
    def __init__(self):
        self.latencies: Dict[int, float] = {}  # request_id -> latency (seconds)
        self.request_times: List[float] = []
        self.start_time = datetime.now()
        self.total_requests = 0
        self.failed_requests = 0
        self.lock = threading.Lock()
        
    def record_latency(self, request_id: int, latency: float):
        """Record latency for a request"""
        with self.lock:
            self.latencies[request_id] = latency
            self.request_times.append(latency)
            self.total_requests += 1

    def record_success(self, request_id: int, latency: float):
        self.record_latency(request_id, latency)
        
    def record_failure(self, request_id: int = None, latency: float = None):
        """Record a failed request"""
        with self.lock:
            self.failed_requests += 1
            self.total_requests += 1
            if request_id is not None and latency is not None:
                self.latencies[request_id] = latency
                self.request_times.append(latency)
        
    def get_throughput(self) -> float:
        """Calculate requests per second"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed == 0:
            return 0
        return self.total_requests / elapsed
    
    def get_p99_latency(self) -> float:
        """Get 99th percentile latency"""
        if not self.request_times:
            return 0
        sorted_times = sorted(self.request_times)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[idx] if idx < len(sorted_times) else sorted_times[-1]
    
    def get_p50_latency(self) -> float:
        """Get median latency"""
        if not self.request_times:
            return 0
        sorted_times = sorted(self.request_times)
        idx = len(sorted_times) // 2
        return sorted_times[idx]
    
    def get_avg_latency(self) -> float:
        """Get average latency"""
        if not self.request_times:
            return 0
        return sum(self.request_times) / len(self.request_times)
    
    def print_summary(self):
        """Print metrics to console"""
        print("\n" + "="*70)
        print("PERFORMANCE METRICS SUMMARY")
        print("="*70)
        print(f"Total Requests: {self.total_requests}")
        print(f"Failed Requests: {self.failed_requests}")
        print(f"Success Rate: {((self.total_requests - self.failed_requests) / max(self.total_requests, 1)) * 100:.2f}%")
        print(f"Throughput: {self.get_throughput():.2f} req/sec")
        print(f"Avg Latency: {self.get_avg_latency():.4f}s")
        print(f"P50 Latency: {self.get_p50_latency():.4f}s")
        print(f"P99 Latency: {self.get_p99_latency():.4f}s")
        print("="*70 + "\n")
    
    def save_to_csv(self, filepath: str = "metrics.csv"):
        """Save latency data to CSV for plotting"""
        import csv
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['request_id', 'latency_seconds'])
            for req_id in sorted(self.latencies.keys()):
                writer.writerow([req_id, self.latencies[req_id]])
        print(f"✓ Metrics saved to {filepath}")
    
    def save_summary_json(self, filepath: str = "metrics_summary.json"):
        """Save summary statistics to JSON"""
        summary = {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": ((self.total_requests - self.failed_requests) / max(self.total_requests, 1)),
            "throughput_req_per_sec": self.get_throughput(),
            "avg_latency_sec": self.get_avg_latency(),
            "p50_latency_sec": self.get_p50_latency(),
            "p99_latency_sec": self.get_p99_latency(),
            "timestamp": self.start_time.isoformat()
        }
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"✓ Summary saved to {filepath}")
