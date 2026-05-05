#workers/gpu_worker.py
from queue import Queue
import threading
import time
import random
import requests

from common.models import Response
from llm.inference import run_llm
from rag.retriever import retrieve_context


class GPUWorker:
    def __init__(self, worker_id: int):
        self.id = worker_id

        self.queue = Queue(maxsize=10)
        self.lock = threading.Lock()

        self.is_healthy = True
        self.fail_count = 0
        self.max_failures = 5

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

        #self.server_url = random.choice(self.server_urls)

        # start worker thread
        self.num_threads = 8  

        for _ in range(self.num_threads):
            threading.Thread(target=self._run, daemon=True).start()

    # -----------------------
    # PUBLIC API (NON-BLOCKING)
    # -----------------------
    def process(self, request):
        self.queue.put(request)

    # -----------------------
    # WORKER LOOP
    # -----------------------
    def _run(self):
        
        while True:
            request = self.queue.get()
            self.queue_size = self.queue.qsize()
            start = time.time()

            try:
                self.last_activity = time.time()

                context = retrieve_context(request.query, k=3)

                server_url = random.choice(self.server_urls)

                result = run_llm(
                    request.query,
                    context,
                    server_url
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
    # STATUS
    # -----------------------
    def get_status(self):
        return {
            "id": self.id,
            "is_healthy": self.is_healthy,
            "queue_size": self.queue.qsize(),
            "processed_count": self.processed_count,
            "avg_latency": self.avg_latency,
            "last_activity": self.last_activity
        }