#workers/gpu_worker.py
"""
Enhanced GPU Worker with Health Tracking
"""
import time
from common.models import Request, Response
from llm.inference import run_llm
from rag.retriever import retrieve_context

class GPUWorker:
    def __init__(self, worker_id: int):
        self.id = worker_id
        self.is_healthy = True
        self.processed_count = 0
        self.last_activity = time.time()
    
    def process(self, request: Request) -> Response:
        """
        Process request: RAG + LLM
        """
        start = time.time()
        self.last_activity = time.time()
        
        try:
            print(f"[Worker {self.id}] Processing request {request.id}")
            
            # RAG Step
            context = retrieve_context(request.query, k=3)
            
            # LLM Step
            result = run_llm(request.query, context)
            
            latency = time.time() - start
            self.processed_count += 1
            
            return Response(
                id=request.id,
                result=result,
                latency=latency
            )
        
        except Exception as e:
            print(f"[Worker {self.id}] ERROR: {e}")
            self.is_healthy = False
            raise
    
    def is_alive(self) -> bool:
        """Health check endpoint"""
        return self.is_healthy
    
    def get_status(self) -> dict:
        """Get worker status"""
        return {
            "id": self.id,
            "is_healthy": self.is_healthy,
            "processed_count": self.processed_count,
            "last_activity": self.last_activity
        }