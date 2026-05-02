#lb/load_balancer.py
import random
import config
class LoadBalancer:
    def __init__(self, workers):
        self.workers = workers
        self.index = 0
        self.last_assigned_worker = None  # NEW
    def get_worker_score(self, worker):
        return (
            worker.processed_count * 0.2 +
            getattr(worker, "queue_size", 0) * 2 +
            getattr(worker, "avg_latency", 0) * 1.5 +
            (0 if worker.is_healthy else 1000)
        )
    def get_least_loaded_worker(self):
        healthy_workers = [
            (i, w) for i, w in enumerate(self.workers)
            if getattr(w, "is_healthy", True)
        ]

        if not healthy_workers:
            raise Exception("No healthy workers")

        worker_id, worker = min(
        healthy_workers,
        key=lambda x: self.get_worker_score(x[1])
    )
        return worker, worker_id
    def dispatch(self, request):
        worker, worker_id = self.get_least_loaded_worker()
        self.last_assigned_worker = worker_id

        print(f"[LB] Assigning request {request.id} → Worker {worker_id}")
        if worker.queue_size > config.MAX_QUEUE_SIZE:
            worker.is_healthy = False
            print(f"[LB] Worker {worker_id} overloaded → marking unhealthy")
        return worker.process(request)