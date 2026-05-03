#workers/gpu_worker.py
"""
Enhanced GPU Worker with Health Tracking
"""
import random
import time
import threading
import requests
from common.models import Request, Response
from llm.inference import run_llm
from rag.retriever import retrieve_context

from concurrent.futures import ThreadPoolExecutor

class GPUWorker:
    def __init__(self, worker_id: int):
        self.id = worker_id  # ✅ REQUIRED

        # Concurrency
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.semaphore = threading.Semaphore(1)

        # HTTP session
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,
            pool_maxsize=50
        )
        self.session.mount("http://", adapter)

        # Health + failure tracking
        self.fail_count = 0
        self.max_failures = 5
        self.recovery_time = 5
        self.is_healthy = True 

        # Work tracking
        self.queue_size = 0      
        self.is_busy = False     
        self.processed_count = 0 

        # Latency tracking
        self.total_latency = 0.0 
        self.avg_latency = 0.0   
        self.last_activity = time.time() 


        LLM_URLS = [
    "http://localhost:8888",
    "http://localhost:8889",
    "http://localhost:8890",
    "http://localhost:8891"
]
                
        self.server_url = random.choice(LLM_URLS)
    def process(self, request: Request) -> Response:
        self.queue_size += 1
        self.is_busy = True

        try:
            future = self.executor.submit(self._handle_request, request)
            return future.result()
        finally:
            self.queue_size -= 1
            if self.queue_size == 0:
                self.is_busy = False
    def _handle_request(self, request: Request) -> Response:
        with self.semaphore:
            start = time.time()
            self.last_activity = time.time()

            print(f"[Worker {self.id}] START request {request.id}")

            try:
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

                print(f"[Worker {self.id}] DONE request {request.id} in {latency:.2f}s")

                return Response(
                    id=request.id,
                    result=result,
                    latency=latency
                )

            except Exception as e:
                print(f"[Worker {self.id}] ERROR: {e}")

                self.fail_count += 1

                if self.fail_count >= self.max_failures:
                    self.is_healthy = False
                    self.recovery_time = time.time() + 5
                    print(f"[Worker {self.id}] ❌ Marked unhealthy")

                return Response(
                    id=request.id,
                    result="ERROR: LLM backend failure",
                    latency=0
                )

        
        
    def is_alive(self) -> bool:
        if not self.is_healthy:
            if time.time() > self.recovery_time:
                print(f"[Worker {self.id}] ♻️ Recovered")
                self.is_healthy = True
                self.fail_count = 0

        return self.is_healthy

    def get_status(self) -> dict:
        return {
            "id": self.id,
            "is_healthy": self.is_healthy,
            "is_busy": self.is_busy,
            "processed_count": self.processed_count,
            "last_activity": self.last_activity
        }