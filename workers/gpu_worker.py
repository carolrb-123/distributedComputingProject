"""
Enhanced GPU Worker with Health Tracking
"""
import random
import time
import threading
from common.models import Request, Response
from llm.inference import run_llm
from rag.retriever import retrieve_context

from concurrent.futures import ThreadPoolExecutor

class GPUWorker:
    def __init__(self, worker_id: int):
        self.id = worker_id
        self.is_healthy = True
        self.processed_count = 0
        self.queue_size = 0
        self.total_latency = 0
        self.avg_latency = 0
        self.last_activity = time.time()
        self.is_busy = False

        
        self.executor = ThreadPoolExecutor(max_workers=1)
        PORTS = [8888, 8889, 8890, 8891]
        self.server_url = f"http://localhost:{PORTS[worker_id % len(PORTS)]}"
    def process(self, request: Request) -> Response:
        self.queue_size += 1

        try:
            future = self.executor.submit(self._handle_request, request)
            return future.result()
        finally:
            self.queue_size -= 1
    def _handle_request(self, request: Request) -> Response:
        start = time.time()
        self.last_activity = time.time()

        # 🔥 ADD THIS (start log)
        print(f"[Worker {self.id}] START request {request.id}")

        try:
            context = retrieve_context(request.query, k=3)
            result = run_llm(request.query, context, self.server_url)

            latency = time.time() - start
            self.processed_count += 1

            self.total_latency += latency
            self.avg_latency = self.total_latency / self.processed_count

            # 🔥 ADD THIS (end log)
            print(f"[Worker {self.id}] DONE request {request.id} in {latency:.2f}s")

            return Response(
                id=request.id,
                result=result,
                latency=latency
            )

        except Exception as e:
            print(f"[Worker {self.id}] ERROR: {e}")

            # do NOT instantly kill worker
            if "timed out" in str(e) or "connection" in str(e):
                self.is_healthy = False

            return Response(
                id=request.id,
                result="ERROR: LLM backend failure",
                latency=0
            )
    def is_alive(self) -> bool:
        if not self.is_healthy and random.random() < 0.1:
            print(f"[Worker {self.id}] ♻️ Recovered")
            self.is_healthy = True

        return self.is_healthy

    def get_status(self) -> dict:
        return {
            "id": self.id,
            "is_healthy": self.is_healthy,
            "is_busy": self.is_busy,
            "processed_count": self.processed_count,
            "last_activity": self.last_activity
        }