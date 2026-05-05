#lb/load_balancer.py
import random
import config


class LoadBalancer:
    def __init__(self, workers):
        self.workers = workers
        self.last_assigned_worker = None
        self._rr_index = 0
        # ensure consistent health state
        self.worker_health = {i: True for i in range(len(workers))}

        print("[LB] Workers registered:")
        for i, w in enumerate(self.workers):
            print(i, w)

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
        return self._safe(worker, "queue_size", 0)

    # ---------------------------
    # GET BEST WORKER (FIXED)
    # ---------------------------
    def get_least_loaded_worker(self):
        healthy = [
            (i, w) for i, w in enumerate(self.workers)
            if self._safe(w, "is_healthy", True)
        ]

        if not healthy:
            print("[LB] WARNING: No healthy workers → using ANY worker")
            healthy = list(enumerate(self.workers))

        # sort by queue size, break ties by round-robin order
        healthy.sort(key=lambda x: (
            self._safe(x[1], "queue_size", 0),
            (x[0] - self._rr_index) % len(self.workers)
        ))

        worker_id, worker = healthy[0]
        self._rr_index = (worker_id + 1) % len(self.workers)
        return worker, worker_id
    # ---------------------------
    # DISPATCH WITH RETRY (FIXED)
    # ---------------------------
    def dispatch(self, request):
        worker, worker_id = self.get_least_loaded_worker()

        print(f"[LB] Request {request.id} → Worker {worker_id}")

        worker.process(request)
        
        self.last_assigned_worker = worker_id

        return True

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