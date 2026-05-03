#master/scheduler.py
import threading
import time
from typing import Dict

from common.models import Request, Response
from lb.load_balancer import LoadBalancer
from common.metrics import MetricsCollector


class Scheduler:
    def __init__(self, load_balancer: LoadBalancer, metrics: MetricsCollector):
        print("LOADING SCHEDULER FROM:", __file__)

        self.lb = load_balancer
        self.metrics = metrics

        self.active_tasks: Dict[int, dict] = {}

        self.lock = threading.Lock()

        # FIX: proper monitoring setup
        self.monitoring = True
        self.worker_health: Dict[int, str] = {
            i: "HEALTHY" for i in range(len(load_balancer.workers))
        }

        self.worker_last_ping: Dict[int, float] = {
            i: time.time() for i in range(len(load_balancer.workers))
        }

        self.monitor_thread = threading.Thread(
            target=self._monitor,
            daemon=True
        )
        self.monitor_thread.start()

    # -------------------------
    # MAIN REQUEST HANDLER
    # -------------------------
    def handle_request(self, request: Request) -> Response:
        start = time.time()

        try:
            with self.lock:
                self.active_tasks[request.id] = {
                    "request": request,
                    "start_time": start,
                    "worker_id": None
                }

            # FIX: safe dispatch with retry
            response = None
            last_error = None

            for _ in range(2):  # retry once
                try:
                    response = self.lb.dispatch(request)
                    break
                except Exception as e:
                    last_error = e
                    time.sleep(0.2)

            if response is None:
                raise RuntimeError(f"Dispatch failed: {last_error}")

            worker_id = self.lb.last_assigned_worker

            with self.lock:
                self.active_tasks[request.id]["worker_id"] = worker_id

            latency = time.time() - start
            response.latency = latency

            self.metrics.record_latency(request.id, latency)

            print(f"[Scheduler] Done {request.id} | {latency:.3f}s")

            return response

        except Exception as e:
            print(f"[Scheduler] ERROR {request.id}: {e}")
            self.metrics.record_failure()

            return Response(
                id=request.id,
                result=f"ERROR: {str(e)}",
                latency=time.time() - start
            )

        finally:
            with self.lock:
                self.active_tasks.pop(request.id, None)

    # -------------------------
    # FIXED MONITOR THREAD
    # -------------------------
    def _monitor(self):
        while self.monitoring:
            time.sleep(3)

            for worker_id, worker in enumerate(self.lb.workers):
                try:
                    # FIX: safe health detection
                    is_healthy = getattr(worker, "is_healthy", True)

                    # optional heartbeat tracking
                    if hasattr(worker, "last_ping"):
                        self.worker_last_ping[worker_id] = worker.last_ping

                    self.worker_health[worker_id] = (
                        "HEALTHY" if is_healthy else "FAILED"
                    )

                except Exception as e:
                    print(f"[Monitor] Worker {worker_id} check failed: {e}")
                    self.worker_health[worker_id] = "FAILED"

    # -------------------------
    # STATUS API
    # -------------------------
    def get_worker_status(self):
        return {
            "worker_health": dict(self.worker_health),
            "active_tasks": len(self.active_tasks),
            "total_requests": self.metrics.total_requests
        }

    # -------------------------
    # CLEAN SHUTDOWN
    # -------------------------
    def shutdown(self):
        self.monitoring = False
        if hasattr(self, "monitor_thread"):
            self.monitor_thread.join(timeout=2)