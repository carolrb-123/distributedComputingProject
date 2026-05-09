#workers/gpu_worker.py
from queue import Full, Queue
import threading
import time
import requests

import config
from common.models import Response
from llm.inference import run_llm
from rag.retriever import retrieve_context


class GPUWorker:
    def __init__(self, worker_id: int, server_url: str = None):
        self.id = worker_id
        self.server_url = server_url or self._server_url_for_worker(worker_id)

        self.queue = Queue(maxsize=config.WORKER_QUEUE_SIZE)
        self.lock = threading.Lock()
        self._thread_local = threading.local()

        self.is_healthy = True
        self.fail_count = 0
        self.max_failures = config.WORKER_MAX_FAILURES

        self.processed_count = 0

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

    def _session(self):
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = requests.Session()
            self._thread_local.session = session
        return session

    # -----------------------
    # PUBLIC API (NON-BLOCKING)
    # -----------------------
    def process(self, request):
        if not self.is_healthy:
            raise RuntimeError(f"Worker {self.id} is unhealthy")

        try:
            self.queue.put_nowait(request)
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
                    self.fail_count = 0

                request.callback(
                    Response(
                        id=request.id,
                        result=result,
                        latency=latency
                    )
                )

            except Exception as e:
                with self.lock:
                    self.fail_count += 1

                    if self.fail_count >= self.max_failures:
                        self.is_healthy = False

                request.callback(
                    Response(
                        id=request.id,
                        result=f"ERROR: {str(e)}",
                        latency=0
                    )
                )

            finally:
                self.queue.task_done()

    # -----------------------
    # HEALTH CHECK
    # -----------------------
    def health_check(self):
        self.last_health_check = time.time()

        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=config.LLM_HEALTH_TIMEOUT,
            )
            response.raise_for_status()

            with self.lock:
                self.fail_count = 0
                self.is_healthy = True
            return True

        except Exception:
            with self.lock:
                self.fail_count += 1
                if self.fail_count >= self.max_failures:
                    self.is_healthy = False
            return False

    # -----------------------
    # STATUS
    # -----------------------
    def get_status(self):
        return {
            "id": self.id,
            "server_url": self.server_url,
            "is_healthy": self.is_healthy,
            "queue_size": self.queue.qsize(),
            "queue_capacity": self.queue_capacity,
            "processed_count": self.processed_count,
            "avg_latency": self.avg_latency,
            "fail_count": self.fail_count,
            "last_activity": self.last_activity,
            "last_health_check": self.last_health_check,
        }
