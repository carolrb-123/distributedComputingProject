#master/scheduler.py
"""
Enhanced Scheduler with Health Checks & Task Reassignment
"""
import threading
import time
from collections import defaultdict
from typing import Dict, Optional

from urllib3 import request
from common.models import Request, Response
from lb.load_balancer import LoadBalancer
from common.metrics import MetricsCollector

class Scheduler:
    def __init__(self, load_balancer: LoadBalancer, metrics: MetricsCollector):
        self.lb = load_balancer
        self.metrics = metrics
        
        # Task tracking
        self.active_tasks: Dict[int, dict] = {}  # request_id -> {worker_id, request, start_time}
        self.response_queue: Dict[int, Optional[Response]] = {}  # request_id -> response
        
        # Worker health tracking
        self.worker_health: Dict[int, str] = {i: "HEALTHY" for i in range(len(load_balancer.workers))}
        self.worker_last_ping: Dict[int, float] = {i: time.time() for i in range(len(load_balancer.workers))}
        
        # Health check thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()
    
    def handle_request(self, request: Request) -> Response:
        """
        Main entry point: dispatch request and wait for response
        """
        start = time.time()
        
        try:
            # Dispatch to load balancer
            print(f"[Scheduler] Dispatching request {request.id}")
            self.active_tasks[request.id] = {
                "request": request,
                "start_time": start,
                "worker_id": None
            }
            
            # Get response from load balancer (via worker)
            response = self.lb.dispatch(request)

            worker_id = self.lb.last_assigned_worker
            self.active_tasks[request.id]["worker_id"] = worker_id
            
            # Record latency
            latency = time.time() - start
            response.latency = latency
            self.metrics.record_latency(request.id, latency)
            
            print(f"[Scheduler] Response {request.id} | Latency: {latency:.4f}s")
            
            return response
            
        except Exception as e:
            print(f"[Scheduler] ERROR processing request {request.id}: {e}")
            self.metrics.record_failure()
            return Response(
                id=request.id,
                result=f"ERROR: {str(e)}",
                latency=time.time() - start
            )
        finally:
            if request.id in self.active_tasks:
                del self.active_tasks[request.id]
    
    def _monitor(self):
        """
        Background thread: monitor worker health and reassign tasks
        """
        while self.monitoring:
            time.sleep(2)  # Check every 2 seconds
            
            # Ping all workers
            for worker_id, worker in enumerate(self.lb.workers):
                try:
                    # Simple health check: try to access worker
                    if hasattr(worker, 'is_alive'):
                        is_healthy = worker.is_alive()
                    else:
                        is_healthy = True
                    
                    if is_healthy:
                        self.worker_health[worker_id] = "HEALTHY"
                        self.worker_last_ping[worker_id] = time.time()
                    else:
                        self.worker_health[worker_id] = "FAILED"
                        self._handle_worker_failure(worker_id)
                        
                except Exception as e:
                    self.worker_health[worker_id] = "FAILED"
                    print(f"[Monitor] Worker {worker_id} health check failed: {e}")
                    self._handle_worker_failure(worker_id)
    
    def _handle_worker_failure(self, failed_worker_id: int):
        """
        Reassign tasks from failed worker to healthy ones
        """
        print(f"[Scheduler] Worker {failed_worker_id} FAILED - reassigning tasks")
        
        # Find tasks assigned to failed worker
        tasks_to_reassign = [
            (req_id, task) for req_id, task in self.active_tasks.items()
            if task.get("worker_id") == failed_worker_id
        ]
        
        # Reassign to healthy workers
        for req_id, task in tasks_to_reassign:
            print(f"[Scheduler] Re-dispatching request {req_id}")

            try:
                response = self.lb.dispatch(task["request"])

                latency = time.time() - task["start_time"]
                response.latency = latency

                self.metrics.record_latency(req_id, latency)

                print(f"[Scheduler] ✅ Recovered request {req_id} | Latency: {latency:.4f}s")

            except Exception as e:
                print(f"[Scheduler] ❌ Retry failed for request {req_id}: {e}")
                self.metrics.record_failure()
    
    def get_worker_status(self) -> Dict:
        """Get status of all workers"""
        return {
            "worker_health": dict(self.worker_health),
            "active_tasks": len(self.active_tasks),
            "total_requests": self.metrics.total_requests
        }
    
    def shutdown(self):
        """Stop monitoring"""
        self.monitoring = False