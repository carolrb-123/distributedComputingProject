#client/load_generator.py
from concurrent.futures import ThreadPoolExecutor
from common.models import Request
import time
from concurrent.futures import ThreadPoolExecutor

def simulate_user(scheduler, user_id):
    request = Request(id=user_id, query=f"Query{user_id}")
    response = scheduler.handle_request(request)
    print(f"[Client] Response {response.id} | Latency: {response.latency:.3f}s")




def run_load_test(scheduler, num_users=1000):
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = []

        for i in range(num_users):
            futures.append(executor.submit(simulate_user, scheduler, i))
            time.sleep(0.002)  # smoother ramp

        for f in futures:
            f.result()