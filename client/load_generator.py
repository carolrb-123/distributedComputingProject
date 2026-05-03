from concurrent.futures import ThreadPoolExecutor
from common.models import Request


def simulate_user(scheduler, user_id):
    request = Request(id=user_id, query=f"Query{user_id}")
    response = scheduler.handle_request(request)
    print(f"[Client] Response {response.id} | Latency: {response.latency:.3f}s")


def run_load_test(scheduler, num_users=1000):
    # ✅ Limit total concurrent users (VERY IMPORTANT)
    with ThreadPoolExecutor(max_workers=100) as executor:
        for i in range(num_users):
            executor.submit(simulate_user, scheduler, i)