"""
Fault Tolerance Test Module
Demonstrates: Node failure detection, task reassignment, and recovery
"""

import time
import config
from common.models import Request


class FaultToleranceTest:
    def __init__(self, scheduler, lb, num_tests=50):
        self.scheduler = scheduler
        self.lb = lb
        self.num_tests = num_tests or config.FAULT_TOLERANCE_TEST_REQUESTS
        self.results = {
            "phase1_failure": [],
            "phase2_recovery": [],
            "phase3_rebalance": []
        }

    def _send_requests(self, request_id_base, label):
        request_count = 0
        success_count = 0
        failed_count = 0
        worker_assignments = {i: 0 for i in range(len(self.lb.workers))}
        start_time = time.time()

        for i in range(self.num_tests):
            try:
                request = Request(
                    id=request_id_base + i,
                    query=f"{label} request {i}"
                )

                response = self.scheduler.handle_request(request)
                request_count += 1

                assigned_worker = request.assigned_worker_id
                if assigned_worker is not None:
                    worker_assignments[assigned_worker] += 1

                if response.status == "OK" and "ERROR" not in str(response.result):
                    success_count += 1
                    status = "SUCCESS"
                else:
                    failed_count += 1
                    status = "FAILED"

                print(
                    f"  Request {i}: {status} | Worker {assigned_worker} | "
                    f"Latency: {response.latency:.2f}s"
                )

            except Exception as e:
                failed_count += 1
                print(f"  Request {i}: FAILED | Exception: {str(e)[:80]}")

        elapsed = time.time() - start_time
        success_rate = (success_count / request_count * 100) if request_count > 0 else 0

        return {
            "total_requests": request_count,
            "successful": success_count,
            "failed": failed_count,
            "success_rate": success_rate,
            "elapsed_time": elapsed,
            "worker_assignments": worker_assignments
        }

    def _print_worker_states(self):
        for i, worker in enumerate(self.lb.workers):
            state = getattr(worker, "state", "HEALTHY" if worker.is_healthy else "UNHEALTHY")
            print(f"  Worker {i}: {state}")
    
    def test_phase_1_node_failure(self):
        """
        PHASE 1: Kill one worker and send requests
        Expected: System detects unhealthy worker, routes to others
        """
        if len(self.lb.workers) < 2:
            raise RuntimeError("Fault tolerance test requires at least 2 workers")

        print("\n" + "="*70)
        print("FAULT TOLERANCE TEST - PHASE 1: NODE FAILURE DETECTION")
        print("="*70)
        
        failed_worker_id = 1
        failed_worker = self.lb.workers[failed_worker_id]

        print("\n[FT] SIMULATING NODE FAILURE: Opening Worker 1 circuit")
        if hasattr(failed_worker, "force_unhealthy"):
            failed_worker.force_unhealthy("fault tolerance test")
        else:
            failed_worker.is_healthy = False
        time.sleep(1)
        
        print(f"[FT] Worker status before test:")
        self._print_worker_states()
        
        print(f"\n[FT] Sending {self.num_tests} requests while Worker 1 is dead...")
        self.results["phase1_failure"] = self._send_requests(5000, "Circuit breaker")
        
        print(f"\n[FT] PHASE 1 RESULTS:")
        print(f"  Total Requests: {self.results['phase1_failure']['total_requests']}")
        print(f"  Successful: {self.results['phase1_failure']['successful']}")
        print(f"  Failed: {self.results['phase1_failure']['failed']}")
        print(f"  Success Rate: {self.results['phase1_failure']['success_rate']:.2f}%")
        print(f"  Elapsed Time: {self.results['phase1_failure']['elapsed_time']:.2f}s")
        print(f"  Request Distribution:")
        worker_assignments = self.results["phase1_failure"]["worker_assignments"]
        for worker_id, count in worker_assignments.items():
            status = "UNHEALTHY (bypassed)" if worker_id == failed_worker_id else "AVAILABLE"
            print(f"    Worker {worker_id}: {count} requests [{status}]")
        
        if worker_assignments[failed_worker_id] == 0:
            print(f"\n  ASSERTION PASSED: Unhealthy Worker 1 received 0 requests")
        else:
            print(f"\n  ASSERTION FAILED: Worker 1 received {worker_assignments[failed_worker_id]} requests")
        
        others_total = sum(
            count for worker_id, count in worker_assignments.items()
            if worker_id != failed_worker_id
        )
        if others_total == self.results["phase1_failure"]["total_requests"]:
            print(f"  ASSERTION PASSED: All requests routed to available workers")
        else:
            print(f"  ASSERTION FAILED: Only {others_total} requests routed to available workers")
        
        return self.results["phase1_failure"]
    
    def test_phase_2_node_recovery(self):
        """
        PHASE 2: Bring Worker 1 back online
        Expected: Worker 1 becomes healthy again
        """
        print("\n" + "="*70)
        print("FAULT TOLERANCE TEST - PHASE 2: NODE RECOVERY")
        print("="*70)
        
        recovered_worker = self.lb.workers[1]
        print("\n[FT] BRINGING WORKER 1 BACK ONLINE: cooldown elapsed + health check")
        if hasattr(recovered_worker, "circuit_opened_at"):
            recovered_worker.circuit_opened_at = time.time() - recovered_worker.failure_cooldown - 1
        for _ in range(max(config.WORKER_RECOVERY_SUCCESSES, 1)):
            recovered_worker.health_check()
            time.sleep(0.2)
        
        print(f"[FT] Worker status after recovery:")
        self._print_worker_states()
        
        print(f"\n[FT] Sending {self.num_tests} requests with all workers healthy...")
        self.results["phase2_recovery"] = self._send_requests(6000, "Recovery")
        
        print(f"\n[FT] PHASE 2 RESULTS:")
        print(f"  Total Requests: {self.results['phase2_recovery']['total_requests']}")
        print(f"  Successful: {self.results['phase2_recovery']['successful']}")
        print(f"  Failed: {self.results['phase2_recovery']['failed']}")
        print(f"  Success Rate: {self.results['phase2_recovery']['success_rate']:.2f}%")
        print(f"  Elapsed Time: {self.results['phase2_recovery']['elapsed_time']:.2f}s")
        print(f"  Request Distribution:")
        worker_assignments = self.results["phase2_recovery"]["worker_assignments"]
        for worker_id, count in worker_assignments.items():
            print(f"    Worker {worker_id}: {count} requests")
        
        # ASSERTION: Worker 1 should now receive requests again
        if worker_assignments[1] > 0:
            print(f"\n  ASSERTION PASSED: Worker 1 received {worker_assignments[1]} requests after recovery")
        else:
            print(f"\n  ASSERTION FAILED: Worker 1 received 0 requests after recovery")
        
        # ASSERTION: Load should be roughly balanced (within 20% variance)
        request_count = self.results["phase2_recovery"]["total_requests"]
        avg_load = request_count / max(len(worker_assignments), 1)
        max_load = max(worker_assignments.values())
        min_load = min(worker_assignments.values())
        balance = (max_load - min_load) / avg_load * 100 if avg_load > 0 else 0
        
        if balance < 30:  # Allow 30% variance
            print(f"  ASSERTION PASSED: Load balanced across workers (variance: {balance:.1f}%)")
        else:
            print(f"  ASSERTION FAILED: Load imbalanced (variance: {balance:.1f}%, should be < 30%)")
        
        return self.results["phase2_recovery"]
    
    def print_summary(self):
        """
        Print comprehensive fault tolerance test summary
        """
        print("\n" + "="*70)
        print("FAULT TOLERANCE TEST - SUMMARY")
        print("="*70)
        
        p1 = self.results["phase1_failure"]
        p2 = self.results["phase2_recovery"]
        
        print(f"\nPHASE 1: NODE FAILURE DETECTION")
        print(f"  ├─ Requests Processed: {p1['total_requests']}")
        print(f"  ├─ Success Rate: {p1['success_rate']:.2f}%")
        print(f"  ├─ Throughput: {p1['total_requests'] / p1['elapsed_time']:.2f} req/sec")
        print(f"  └─ Duration: {p1['elapsed_time']:.2f}s")
        
        print(f"\nPHASE 2: NODE RECOVERY & REBALANCING")
        print(f"  ├─ Requests Processed: {p2['total_requests']}")
        print(f"  ├─ Success Rate: {p2['success_rate']:.2f}%")
        print(f"  ├─ Throughput: {p2['total_requests'] / p2['elapsed_time']:.2f} req/sec")
        print(f"  └─ Duration: {p2['elapsed_time']:.2f}s")
        
        print(f"\nKEY OBSERVATIONS:")
        print(f"  - Phase 1 (failure): Worker 1 bypassed while circuit was open")
        print(f"  - Phase 2 (recovery): Worker 1 reintegrated after health checks")
        print(f"  - All requests succeeded: {p1['failed'] == 0 and p2['failed'] == 0}")
        
        overall_success = (p1['successful'] + p2['successful']) / (p1['total_requests'] + p2['total_requests']) * 100
        print(f"\nOVERALL SUCCESS RATE: {overall_success:.2f}%")
        
        print("\n" + "="*70)
        print("FAULT TOLERANCE TEST COMPLETE")
        print("="*70 + "\n")


def run_fault_tolerance_tests(scheduler, lb):
    """
    Main entry point for fault tolerance testing
    
    Usage:
        from fault_tolerance_test import run_fault_tolerance_tests
        run_fault_tolerance_tests(scheduler, lb)
    """
    ft = FaultToleranceTest(scheduler, lb, num_tests=config.FAULT_TOLERANCE_TEST_REQUESTS)
    
    # Phase 1: Kill Worker 1, send requests
    ft.test_phase_1_node_failure()
    
    # Phase 2: Recover Worker 1, send requests
    ft.test_phase_2_node_recovery()
    
    # Summary
    ft.print_summary()
    
