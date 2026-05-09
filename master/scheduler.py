#master/scheduler.py
import threading
import time
from typing import Dict

import config
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

            response = None
            last_error = None
            attempted_workers = set()
            max_attempts = max(1, config.SCHEDULER_MAX_ATTEMPTS)

            for attempt in range(1, max_attempts + 1):
                try:
                    event = threading.Event()
                    result_container = {}
                    request.attempt = attempt

                    def callback(worker_response, expected_attempt=attempt):
                        if expected_attempt != request.attempt:
                            return
                        result_container["response"] = worker_response
                        event.set()

                    request.callback = callback
                    request.excluded_worker_ids = set(attempted_workers)

                    self.lb.dispatch(request)
                    worker_id = request.assigned_worker_id
                    attempted_workers.add(worker_id)

                    with self.lock:
                        self.active_tasks[request.id]["worker_id"] = worker_id

                    timed_out = not event.wait(timeout=config.SCHEDULER_REQUEST_TIMEOUT)
                    if timed_out:
                        self.lb.mark_worker_timeout(worker_id, request.id)
                        last_error = RuntimeError(
                            f"Request {request.id} timed out after "
                            f"{config.SCHEDULER_REQUEST_TIMEOUT}s on worker {worker_id}"
                        )
                        break

                    response = result_container["response"]

                    if response.status != "OK" and attempt < max_attempts:
                        last_error = RuntimeError(response.error or response.result)
                        attempted_workers.add(response.worker_id)
                        response = None
                        time.sleep(0.2)
                        continue

                    break

                except Exception as e:
                    last_error = e
                    if not config.TASK_REASSIGNMENT_ENABLED:
                        break
                    time.sleep(0.2)

            if response is None:
                raise RuntimeError(f"Dispatch failed: {last_error}")

            worker_id = getattr(request, "assigned_worker_id", self.lb.last_assigned_worker)

            with self.lock:
                self.active_tasks[request.id]["worker_id"] = worker_id

            latency = time.time() - start
            response.latency = latency

            if response.status == "OK" and not str(response.result).startswith("ERROR"):
                self.metrics.record_success(request.id, latency)
            else:
                self.metrics.record_failure(request.id, latency)

            print(f"[Scheduler] Done {request.id} | {latency:.3f}s")

            return response

        except Exception as e:
            print(f"[Scheduler] ERROR {request.id}: {e}")
            latency = time.time() - start
            self.metrics.record_failure(request.id, latency)

            return Response(
                id=request.id,
                result=f"ERROR: {str(e)}",
                latency=latency,
                status="ERROR",
                error=str(e),
            )

        finally:
            with self.lock:
                self.active_tasks.pop(request.id, None)

    # -------------------------
    # FIXED MONITOR THREAD
    # -------------------------
    def _monitor(self):
        while self.monitoring:
            time.sleep(config.WORKER_HEALTH_CHECK_INTERVAL)

            for worker_id, worker in enumerate(self.lb.workers):
                try:
                    if hasattr(worker, "health_check"):
                        is_healthy = worker.health_check()
                    else:
                        is_healthy = getattr(worker, "is_healthy", True)

                    # optional heartbeat tracking
                    if hasattr(worker, "last_ping"):
                        self.worker_last_ping[worker_id] = worker.last_ping

                    self.worker_health[worker_id] = getattr(
                        worker,
                        "state",
                        "HEALTHY" if is_healthy else "UNHEALTHY"
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
