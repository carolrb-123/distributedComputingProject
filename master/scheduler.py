#master/scheduler.py
import threading
import queue

class Scheduler:
    def __init__(self, load_balancer):
        self.lb = load_balancer
        self.active_tasks = {}
        self.response_queue = queue.Queue()
        self.scheduler_thread = threading.Thread(target=self._monitor, daemon=True)
        self.scheduler_thread.start()
    
    def _monitor(self):
        while True:
            pass
    
    def handle_request(self, request):
        print(f"[Scheduler] Dispatching request {request.id}")
        self.active_tasks[request.id] = True
        response = self.lb.dispatch(request)
        del self.active_tasks[request.id]
        self.response_queue.put(response)
        return response