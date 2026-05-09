#lb/load_balancer.py
import threading


class LoadBalancer:
    def __init__(self, workers):
        self.workers = workers
        self.last_assigned_worker = None
        self.lock = threading.Lock()
        self._rr_index = 0
        self.worker_health = {i: True for i in range(len(workers))}

        print("[LB] Workers registered:")
        for i, w in enumerate(self.workers):
            server_url = getattr(w, "server_url", "unknown")
            print(f"  {i}: {server_url}")

    # ---------------------------
    # SAFE ATTRIBUTE ACCESS
    # ---------------------------
    def _safe(self, worker, attr, default=0):
        return getattr(worker, attr, default)

    # ---------------------------
    # SCORE FUNCTION (FIXED)
    # ---------------------------
    def get_worker_score(self, worker):
        if not self._safe(worker, "is_healthy", True):
            return float("inf")
        queue_size = self._safe(worker, "queue_size", 0)
        queue_capacity = max(self._safe(worker, "queue_capacity", 1), 1)
        avg_latency = self._safe(worker, "avg_latency", 0.0)
        return (queue_size / queue_capacity) + (avg_latency * 0.05)

    # ---------------------------
    # GET BEST WORKER (FIXED)
    # ---------------------------
    def get_worker_candidates(self):
        healthy = [
            (i, w) for i, w in enumerate(self.workers)
            if self._safe(w, "is_healthy", True)
        ]

        if not healthy:
            raise RuntimeError("No healthy workers available")

        healthy.sort(key=lambda x: (
            self.get_worker_score(x[1]),
            (x[0] - self._rr_index) % len(self.workers)
        ))
        return healthy

    # ---------------------------
    # DISPATCH WITH RETRY (FIXED)
    # ---------------------------
    def dispatch(self, request):
        last_error = None

        with self.lock:
            candidates = self.get_worker_candidates()

            for worker_id, worker in candidates:
                try:
                    print(f"[LB] Request {request.id} -> Worker {worker_id}")
                    worker.process(request)
                    self.last_assigned_worker = worker_id
                    request.assigned_worker_id = worker_id
                    self._rr_index = (worker_id + 1) % len(self.workers)
                    return True
                except Exception as exc:
                    last_error = exc
                    self._mark_worker_bad(worker_id)
                    continue

        raise RuntimeError(f"Dispatch failed on all workers: {last_error}")

    # ---------------------------
    # MARK WORKER AS BAD
    # ---------------------------
    def _mark_worker_bad(self, worker_id):
        if worker_id is not None:
            self.worker_health[worker_id] = False

    # ---------------------------
    # SIMPLE METRICS UPDATE
    # ---------------------------
    """def _update_worker_stats(self, worker):
        worker.processed_count = self._safe(worker, "processed_count", 0) + 1

        # optional smoothing for latency
        if hasattr(worker, "avg_latency"):
            worker.avg_latency = worker.avg_latency * 0.9"""
