#workers/gpu_worker.py
import random
import time
import requests
from concurrent.futures import ThreadPoolExecutor
import threading

from common.models import Request, Response
from llm.inference import run_llm
from rag.retriever import retrieve_context


class GPUWorker:
    def __init__(self, worker_id: int):
        self.id = worker_id

        self.executor = ThreadPoolExecutor(max_workers=4)  # FIXED (was 1)
        self.lock = threading.Lock()

        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,
            pool_maxsize=50
        )
        self.session.mount("http://", adapter)

        self.fail_count = 0
        self.max_failures = 5
        self.recovery_time = 5
        self.is_healthy = True

        self.queue_size = 0
        self.processed_count = 0

        self.total_latency = 0.0
        self.avg_latency = 0.0
        self.last_activity = time.time()

        self.server_urls = [
            "http://localhost:8888",
            "http://localhost:8889",
            "http://localhost:8890",
            "http://localhost:8891"
        ]

        self.server_url = random.choice(self.server_urls)

    def process(self, request: Request) -> Response:
        with self.lock:
            self.queue_size += 1

        try:
            future = self.executor.submit(self._handle_request, request)
            return future.result()
        finally:
            with self.lock:
                self.queue_size -= 1

    def _handle_request(self, request: Request) -> Response:
        start = time.time()

        try:
            self.last_activity = time.time()

            context = retrieve_context(request.query, k=3)

            result = run_llm(
                request.query,
                context,
                self.server_url,
                session=self.session
            )

            latency = time.time() - start

            self.processed_count += 1
            self.fail_count = 0

            self.total_latency += latency
            self.avg_latency = self.total_latency / self.processed_count

            return Response(
                id=request.id,
                result=result,
                latency=latency
            )

        except Exception as e:
            self.fail_count += 1

            if self.fail_count >= self.max_failures*2:
                self.is_healthy = False
                self.recovery_time = time.time() + 5

            return Response(
                id=request.id,
                result="ERROR",
                latency=0
            )

    def is_alive(self) -> bool:
        if not self.is_healthy and time.time() > self.recovery_time:
            self.is_healthy = True
            self.fail_count = 0

        return self.is_healthy
    def get_status(self):
        return {
            "id": self.id,
            "is_healthy": self.is_healthy,
            "queue_size": self.queue_size,
            "processed_count": self.processed_count,
            "avg_latency": self.avg_latency,
            "last_activity": self.last_activity
        }
    