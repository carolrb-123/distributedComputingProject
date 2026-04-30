class LoadBalancer:
    def __init__(self, workers):
        self.workers = workers
        self.index = 0
        self.last_assigned_worker = None  # NEW

    def get_least_loaded_worker(self):
        healthy_workers = [
            (i, w) for i, w in enumerate(self.workers)
            if getattr(w, "is_healthy", True)
        ]

        if not healthy_workers:
            raise Exception("No healthy workers")

        worker_id, worker = min(
            healthy_workers,
            key=lambda x: x[1].processed_count
        )

        return worker, worker_id
    def dispatch(self, request):
        worker, worker_id = self.get_least_loaded_worker()
        self.last_assigned_worker = worker_id

        print(f"[LB] Assigning request {request.id} → Worker {worker_id}")

        return worker.process(request)