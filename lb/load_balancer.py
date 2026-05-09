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
        if hasattr(worker, "can_accept") and not worker.can_accept():
            return float("inf")
        if not self._safe(worker, "is_healthy", True):
            return float("inf")

        queue_size = self._safe(worker, "queue_size", 0)
        queue_capacity = max(self._safe(worker, "queue_capacity", 1), 1)
        in_flight = self._safe(worker, "in_flight", 0)
        avg_latency = self._safe(worker, "avg_latency", 0.0)
        state = self._safe(worker, "state", "HEALTHY")
        state_penalty = {
            "HEALTHY": 0.0,
            "RECOVERING": 0.5,
            "DEGRADED": 1.0,
            "UNHEALTHY": float("inf"),
        }.get(state, 0.0)

        return (queue_size / queue_capacity) + (in_flight * 0.25) + (avg_latency * 0.05) + state_penalty

    # ---------------------------
    # GET BEST WORKER (FIXED)
    # ---------------------------
    def get_worker_candidates(self, excluded_worker_ids=None):
        excluded_worker_ids = set(excluded_worker_ids or [])
        healthy = [
            (i, w) for i, w in enumerate(self.workers)
            if i not in excluded_worker_ids and self.get_worker_score(w) != float("inf")
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
        excluded = getattr(request, "excluded_worker_ids", set())

        with self.lock:
            candidates = self.get_worker_candidates(excluded)

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
                    if hasattr(worker, "mark_dispatch_failure"):
                        worker.mark_dispatch_failure(exc)
                    continue

        raise RuntimeError(f"Dispatch failed on all workers: {last_error}")

    def mark_worker_timeout(self, worker_id, request_id):
        if worker_id is None:
            return

        worker = self.workers[worker_id]
        print(f"[LB] Worker {worker_id} timed out on request {request_id}")
        self._mark_worker_bad(worker_id)
        if hasattr(worker, "mark_timeout"):
            worker.mark_timeout(request_id)

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
