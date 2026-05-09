#lb/load_balancer.py
import threading
import time

import config
from common.errors import AdmissionTimeoutError, WorkerCapacityError


class LoadBalancer:
    def __init__(self, workers):
        self.workers = workers
        self.last_assigned_worker = None
        self.lock = threading.Lock()
        self._rr_index = 0
        self.worker_health = {i: True for i in range(len(workers))}
        self.assignment_counts = {i: 0 for i in range(len(workers))}
        self.last_scores = {}
        self.admission_wait_count = 0
        self.admission_timeout_count = 0
        self.total_admission_wait_time = 0.0
        self.max_admission_wait_time = 0.0

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
    # WORKER SNAPSHOT
    # ---------------------------
    def _worker_snapshot(self, worker_id, worker):
        queue_size = self._safe(worker, "queue_size", 0)
        queue_capacity = max(self._safe(worker, "queue_capacity", 1), 1)
        in_flight = self._safe(worker, "in_flight", 0)
        oldest_in_flight_age = self._safe(worker, "oldest_in_flight_age", 0.0)
        max_in_flight = max(self._safe(worker, "max_in_flight", queue_capacity), 1)
        avg_latency = self._safe(worker, "avg_latency", 0.0)
        ewma_latency = self._safe(worker, "ewma_latency", avg_latency)
        latency = ewma_latency if ewma_latency > 0 else avg_latency
        failed_count = self._safe(worker, "failed_count", 0)
        success_count = self._safe(worker, "success_count", self._safe(worker, "processed_count", 0))
        total_results = success_count + failed_count
        failure_rate = failed_count / total_results if total_results else 0.0
        state = self._safe(worker, "state", "HEALTHY")

        return {
            "worker_id": worker_id,
            "worker": worker,
            "state": state,
            "is_healthy": self._safe(worker, "is_healthy", True),
            "can_accept": worker.can_accept() if hasattr(worker, "can_accept") else True,
            "queue_size": queue_size,
            "queue_capacity": queue_capacity,
            "queue_pressure": min(queue_size / queue_capacity, 1.0),
            "in_flight": in_flight,
            "oldest_in_flight_age": oldest_in_flight_age,
            "max_in_flight": max_in_flight,
            "utilization": min(in_flight / max_in_flight, 1.0),
            "latency": latency,
            "failure_rate": failure_rate,
            "assignments": self.assignment_counts.get(worker_id, 0),
        }

    # ---------------------------
    # SCORE FUNCTION
    # ---------------------------
    def get_worker_score(self, worker, worker_id=None, min_latency=None):
        worker_id = worker_id if worker_id is not None else -1
        snapshot = self._worker_snapshot(worker_id, worker)
        return self._score_snapshot(snapshot, min_latency)

    def _score_snapshot(self, snapshot, min_latency=None):
        if not snapshot["can_accept"] or not snapshot["is_healthy"]:
            return float("inf")

        if snapshot["state"] == "UNHEALTHY":
            return float("inf")

        if config.LOAD_BALANCER_POLICY == "round_robin":
            return 0.0

        if config.LOAD_BALANCER_POLICY == "least_connections":
            return snapshot["in_flight"]

        latency = snapshot["latency"]
        if latency <= 0:
            latency_ratio = 0.0
        elif min_latency and min_latency > 0:
            latency_ratio = latency / min_latency
        else:
            latency_ratio = latency

        state_penalty = {
            "HEALTHY": 0.0,
            "RECOVERING": config.LB_STATE_RECOVERING_PENALTY,
            "DEGRADED": config.LB_STATE_DEGRADED_PENALTY,
            "UNHEALTHY": float("inf"),
        }.get(snapshot["state"], 0.0)

        return (
            snapshot["utilization"] * config.LB_UTILIZATION_WEIGHT
            + snapshot["queue_pressure"] * config.LB_QUEUE_WEIGHT
            + latency_ratio * config.LB_LATENCY_WEIGHT
            + snapshot["oldest_in_flight_age"] * config.LB_IN_FLIGHT_AGE_WEIGHT
            + snapshot["failure_rate"] * config.LB_FAILURE_WEIGHT
            + state_penalty
        )

    def _candidate_sort_key(self, snapshot):
        if config.LOAD_BALANCER_POLICY == "round_robin":
            return (snapshot["rr_distance"], snapshot["assignments"])
        return (snapshot["score"], snapshot["rr_distance"], snapshot["assignments"])

    def _is_available(self, snapshot):
        return snapshot["score"] != float("inf")

    def _min_observed_latency(self, snapshots):
        latencies = [
            item["latency"]
            for item in snapshots
            if item["latency"] and item["latency"] > 0
        ]
        return min(latencies) if latencies else None

    # ---------------------------
    # GET BEST WORKER
    # ---------------------------
    def get_worker_candidates(self, excluded_worker_ids=None):
        excluded_worker_ids = set(excluded_worker_ids or [])
        snapshots = [
            self._worker_snapshot(i, w)
            for i, w in enumerate(self.workers)
            if i not in excluded_worker_ids
        ]
        min_latency = self._min_observed_latency(snapshots)

        for snapshot in snapshots:
            snapshot["score"] = self._score_snapshot(snapshot, min_latency)
            snapshot["rr_distance"] = (snapshot["worker_id"] - self._rr_index) % len(self.workers)

        self.last_scores = {
            item["worker_id"]: {
                "score": item["score"],
                "state": item["state"],
                "in_flight": item["in_flight"],
                "oldest_in_flight_age": item["oldest_in_flight_age"],
                "max_in_flight": item["max_in_flight"],
                "latency": item["latency"],
                "failure_rate": item["failure_rate"],
                "can_accept": item["can_accept"],
                "queue_size": item["queue_size"],
                "queue_capacity": item["queue_capacity"],
            }
            for item in snapshots
        }

        healthy = [item for item in snapshots if self._is_available(item)]

        if not healthy:
            raise RuntimeError("No workers currently available")

        healthy.sort(key=self._candidate_sort_key)
        return [(item["worker_id"], item["worker"]) for item in healthy]

    # ---------------------------
    # DISPATCH WITH ADMISSION BACKPRESSURE
    # ---------------------------
    def dispatch(self, request):
        last_error = None
        excluded = getattr(request, "excluded_worker_ids", set())
        admission_started_at = None
        timeout = max(0.0, config.SCHEDULER_ADMISSION_TIMEOUT)
        deadline = time.time() + timeout

        while True:
            candidates = []

            with self.lock:
                try:
                    candidates = self.get_worker_candidates(excluded)
                except RuntimeError as exc:
                    last_error = exc

                for worker_id, worker in candidates:
                    try:
                        score = self.last_scores.get(worker_id, {}).get("score", 0.0)
                        in_flight = self._safe(worker, "in_flight", 0)
                        max_in_flight = self._safe(worker, "max_in_flight", 1)
                        worker.process(request)
                        self.last_assigned_worker = worker_id
                        request.assigned_worker_id = worker_id
                        self.assignment_counts[worker_id] = self.assignment_counts.get(worker_id, 0) + 1
                        self._rr_index = (worker_id + 1) % len(self.workers)
                        wait_time = time.time() - admission_started_at if admission_started_at else 0.0
                        if wait_time > 0:
                            self._record_admission_wait(wait_time)
                        print(
                            f"[LB] Request {request.id} -> Worker {worker_id} "
                            f"| score={score:.3f} | load={in_flight}/{max_in_flight} "
                            f"| admission_wait={wait_time:.3f}s"
                        )
                        return True
                    except WorkerCapacityError as exc:
                        last_error = exc
                        continue
                    except Exception as exc:
                        last_error = exc
                        self._mark_worker_bad(worker_id)
                        if hasattr(worker, "mark_dispatch_failure"):
                            worker.mark_dispatch_failure(exc)
                        continue

            remaining = deadline - time.time()
            if remaining <= 0 or timeout <= 0:
                self._record_admission_timeout()
                reason = last_error or "no worker capacity became available"
                raise AdmissionTimeoutError(
                    f"Admission timeout after {timeout:.1f}s: {reason}"
                )

            if admission_started_at is None:
                admission_started_at = time.time()
                print(
                    f"[LB] Request {request.id} waiting for worker capacity "
                    f"(timeout={timeout:.1f}s)"
                )

            time.sleep(min(config.SCHEDULER_ADMISSION_POLL_INTERVAL, remaining))

    def _record_admission_wait(self, wait_time):
        self.admission_wait_count += 1
        self.total_admission_wait_time += wait_time
        self.max_admission_wait_time = max(self.max_admission_wait_time, wait_time)

    def _record_admission_timeout(self):
        self.admission_timeout_count += 1

    def mark_worker_timeout(self, worker_id, request_id):
        if worker_id is None:
            return

        worker = self.workers[worker_id]
        print(f"[LB] Worker {worker_id} timed out on request {request_id}")
        self._mark_worker_bad(worker_id)
        if hasattr(worker, "mark_timeout"):
            worker.mark_timeout(request_id)

    def get_status(self):
        with self.lock:
            return {
                "policy": config.LOAD_BALANCER_POLICY,
                "assignment_counts": dict(self.assignment_counts),
                "last_scores": dict(self.last_scores),
                "admission": {
                    "wait_count": self.admission_wait_count,
                    "timeout_count": self.admission_timeout_count,
                    "total_wait_time_sec": self.total_admission_wait_time,
                    "max_wait_time_sec": self.max_admission_wait_time,
                    "avg_wait_time_sec": (
                        self.total_admission_wait_time / self.admission_wait_count
                        if self.admission_wait_count else 0.0
                    ),
                    "timeout_sec": config.SCHEDULER_ADMISSION_TIMEOUT,
                    "poll_interval_sec": config.SCHEDULER_ADMISSION_POLL_INTERVAL,
                },
            }

    # ---------------------------
    # MARK WORKER AS BAD
    # ---------------------------
    def _mark_worker_bad(self, worker_id):
        if worker_id is not None:
            self.worker_health[worker_id] = False
