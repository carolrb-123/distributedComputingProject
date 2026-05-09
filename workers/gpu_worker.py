#workers/gpu_worker.py
from queue import Full, Queue
import threading
import time
import requests

import config
from common.models import Response
from llm.inference import run_llm
from rag.retriever import retrieve_context


class WorkerState:
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    RECOVERING = "RECOVERING"


class GPUWorker:
    def __init__(self, worker_id: int, server_url: str = None):
        self.id = worker_id
        self.server_url = server_url or self._server_url_for_worker(worker_id)

        self.queue = Queue(maxsize=config.WORKER_QUEUE_SIZE)
        self.lock = threading.Lock()
        self._thread_local = threading.local()

        self.is_healthy = True
        self.state = WorkerState.HEALTHY
        self.fail_count = 0
        self.consecutive_successes = 0
        self.max_failures = config.WORKER_MAX_FAILURES
        self.failure_cooldown = config.WORKER_FAILURE_COOLDOWN
        self.recovery_successes = config.WORKER_RECOVERY_SUCCESSES
        self.circuit_opened_at = None
        self.last_error = None

        self.processed_count = 0
        self.failed_count = 0
        self.in_flight = 0

        self.total_latency = 0.0
        self.avg_latency = 0.0
        self.last_activity = time.time()
        self.last_health_check = None

        self.num_threads = config.WORKER_THREADS

        for _ in range(self.num_threads):
            threading.Thread(target=self._run, daemon=True).start()

    @staticmethod
    def _server_url_for_worker(worker_id: int) -> str:
        if not config.LLM_SERVER_URLS:
            raise ValueError("No LLM endpoints configured. Set LLM_SERVER_URLS.")
        return config.LLM_SERVER_URLS[worker_id % len(config.LLM_SERVER_URLS)]

    @property
    def queue_size(self):
        return self.queue.qsize()

    @property
    def queue_capacity(self):
        return self.queue.maxsize

    def can_accept(self):
        with self.lock:
            if self.state == WorkerState.UNHEALTHY:
                return False
            return self.queue.qsize() < self.queue.maxsize

    def _session(self):
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = requests.Session()
            self._thread_local.session = session
        return session

    def _set_state(self, state):
        self.state = state
        self.is_healthy = state in {WorkerState.HEALTHY, WorkerState.DEGRADED, WorkerState.RECOVERING}

    def _record_success(self):
        with self.lock:
            self.fail_count = 0
            self.consecutive_successes += 1
            self.last_error = None

            if self.state in {WorkerState.DEGRADED, WorkerState.RECOVERING}:
                if self.consecutive_successes >= self.recovery_successes:
                    self._set_state(WorkerState.HEALTHY)

    def _record_failure(self, error):
        with self.lock:
            self.failed_count += 1
            self.fail_count += 1
            self.consecutive_successes = 0
            self.last_error = str(error)

            if self.fail_count >= self.max_failures:
                self._set_state(WorkerState.UNHEALTHY)
                self.circuit_opened_at = time.time()
            else:
                self._set_state(WorkerState.DEGRADED)

    def mark_timeout(self, request_id):
        self._record_failure(f"Request {request_id} timed out")

    def mark_dispatch_failure(self, error):
        self._record_failure(error)

    def force_unhealthy(self, reason="manual fault injection"):
        with self.lock:
            self.fail_count = self.max_failures
            self.consecutive_successes = 0
            self.last_error = reason
            self._set_state(WorkerState.UNHEALTHY)
            self.circuit_opened_at = time.time()

    # -----------------------
    # PUBLIC API (NON-BLOCKING)
    # -----------------------
    def process(self, request):
        if not self.can_accept():
            raise RuntimeError(f"Worker {self.id} cannot accept work ({self.state})")

        try:
            self.queue.put_nowait(request)
            with self.lock:
                self.in_flight += 1
            return True
        except Full as exc:
            raise RuntimeError(f"Worker {self.id} queue is full") from exc

    # -----------------------
    # WORKER LOOP
    # -----------------------
    def _run(self):
        while True:
            request = self.queue.get()
            start = time.time()

            try:
                self.last_activity = time.time()

                context = retrieve_context(request.query, k=3)

                result = run_llm(
                    request.query,
                    context,
                    self.server_url,
                    session=self._session()
                )

                latency = time.time() - start

                with self.lock:
                    self.processed_count += 1
                    self.total_latency += latency
                    self.avg_latency = self.total_latency / self.processed_count
                self._record_success()

                request.callback(
                    Response(
                        id=request.id,
                        result=result,
                        latency=latency,
                        worker_id=self.id,
                        status="OK",
                    )
                )

            except Exception as e:
                self._record_failure(e)

                request.callback(
                    Response(
                        id=request.id,
                        result=f"ERROR: {str(e)}",
                        latency=0,
                        worker_id=self.id,
                        status="ERROR",
                        error=str(e),
                    )
                )

            finally:
                with self.lock:
                    self.in_flight = max(0, self.in_flight - 1)
                self.queue.task_done()

    # -----------------------
    # HEALTH CHECK
    # -----------------------
    def health_check(self):
        self.last_health_check = time.time()
        health_path = config.LLM_HEALTH_PATH
        if not health_path.startswith("/"):
            health_path = f"/{health_path}"

        with self.lock:
            if self.state == WorkerState.UNHEALTHY and self.circuit_opened_at:
                cooldown_left = (self.circuit_opened_at + self.failure_cooldown) - time.time()
                if cooldown_left > 0:
                    return False

        try:
            response = requests.get(
                f"{self.server_url}{health_path}",
                timeout=config.LLM_HEALTH_TIMEOUT,
            )
            response.raise_for_status()

            with self.lock:
                self.fail_count = 0
                self.consecutive_successes += 1
                self.last_error = None
                if self.state == WorkerState.UNHEALTHY:
                    self._set_state(WorkerState.RECOVERING)
                elif self.consecutive_successes >= self.recovery_successes:
                    self._set_state(WorkerState.HEALTHY)
            return True

        except Exception as exc:
            self._record_failure(exc)
            return False

    # -----------------------
    # STATUS
    # -----------------------
    def get_status(self):
        return {
            "id": self.id,
            "server_url": self.server_url,
            "is_healthy": self.is_healthy,
            "state": self.state,
            "queue_size": self.queue.qsize(),
            "queue_capacity": self.queue_capacity,
            "in_flight": self.in_flight,
            "processed_count": self.processed_count,
            "failed_count": self.failed_count,
            "avg_latency": self.avg_latency,
            "fail_count": self.fail_count,
            "consecutive_successes": self.consecutive_successes,
            "last_error": self.last_error,
            "circuit_opened_at": self.circuit_opened_at,
            "last_activity": self.last_activity,
            "last_health_check": self.last_health_check,
        }
