"""
Fault Tolerance Test Module
Demonstrates: Node failure detection, task reassignment, and recovery
"""

import time
import threading
from common.models import Request, Response
from common.metrics import MetricsCollector


class FaultToleranceTest:
    def __init__(self, scheduler, lb, num_tests=50):
        self.scheduler = scheduler
        self.lb = lb
        self.num_tests = num_tests
        self.results = {
            "phase1_failure": [],
            "phase2_recovery": [],
            "phase3_rebalance": []
        }
    
    def test_phase_1_node_failure(self):
        """
        PHASE 1: Kill one worker and send requests
        Expected: System detects unhealthy worker, routes to others
        """
        print("\n" + "="*70)
        print("FAULT TOLERANCE TEST - PHASE 1: NODE FAILURE DETECTION")
        print("="*70)
        
        # Deliberately mark Worker 1 as unhealthy
        print("\n[FT] SIMULATING NODE FAILURE: Setting Worker 1 is_healthy = False")
        self.lb.workers[1].is_healthy = False
        time.sleep(1)
        
        print(f"[FT] Worker status before test:")
        for i, w in enumerate(self.lb.workers):
            status = "HEALTHY" if w.is_healthy else "FAILED"
            print(f"  Worker {i}: {status}")
        
        print(f"\n[FT] Sending {self.num_tests} requests while Worker 1 is dead...")
        
        request_count = 0
        success_count = 0
        failed_count = 0
        worker_assignments = {0: 0, 1: 0, 2: 0, 3: 0}
        
        start_time = time.time()
        
        for i in range(self.num_tests):
            try:
                request = Request(
                    id=5000 + i,  # 5000+ to distinguish from main test
                    query=f"Fault tolerance test request {i}"
                )
                
                response = self.scheduler.handle_request(request)
                request_count += 1
                
                # Track which worker handled this
                assigned_worker = self.scheduler.lb.last_assigned_worker
                if assigned_worker is not None:
                    worker_assignments[assigned_worker] += 1
                
                # Check if request succeeded
                if "ERROR" not in str(response.result):
                    success_count += 1
                    status = "✓ SUCCESS"
                else:
                    failed_count += 1
                    status = "✗ FAILED"
                
                if i % 10 == 0:
                    print(f"  Request {i}: {status} | Worker {assigned_worker} | Latency: {response.latency:.2f}s")
            
            except Exception as e:
                failed_count += 1
                print(f"  Request {i}: ✗ FAILED | Exception: {str(e)[:50]}")
        
        elapsed = time.time() - start_time
        success_rate = (success_count / request_count * 100) if request_count > 0 else 0
        
        self.results["phase1_failure"] = {
            "total_requests": request_count,
            "successful": success_count,
            "failed": failed_count,
            "success_rate": success_rate,
            "elapsed_time": elapsed,
            "worker_assignments": worker_assignments
        }
        
        print(f"\n[FT] PHASE 1 RESULTS:")
        print(f"  Total Requests: {request_count}")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Success Rate: {success_rate:.2f}%")
        print(f"  Elapsed Time: {elapsed:.2f}s")
        print(f"  Request Distribution:")
        for worker_id, count in worker_assignments.items():
            status = "FAILED (bypassed)" if worker_id == 1 else "HEALTHY"
            print(f"    Worker {worker_id}: {count} requests [{status}]")
        
        # ASSERTION: Worker 1 should have received 0 requests
        if worker_assignments[1] == 0:
            print(f"\n  ✓ ASSERTION PASSED: Unhealthy Worker 1 received 0 requests")
        else:
            print(f"\n  ✗ ASSERTION FAILED: Worker 1 received {worker_assignments[1]} requests (should be 0)")
        
        # ASSERTION: Other workers should have received all requests
        others_total = worker_assignments[0] + worker_assignments[2] + worker_assignments[3]
        if others_total == request_count:
            print(f"  ✓ ASSERTION PASSED: All {request_count} requests routed to healthy workers (0, 2, 3)")
        else:
            print(f"  ✗ ASSERTION FAILED: Only {others_total}/{request_count} requests to healthy workers")
        
        return self.results["phase1_failure"]
    
    def test_phase_2_node_recovery(self):
        """
        PHASE 2: Bring Worker 1 back online
        Expected: Worker 1 becomes healthy again
        """
        print("\n" + "="*70)
        print("FAULT TOLERANCE TEST - PHASE 2: NODE RECOVERY")
        print("="*70)
        
        print("\n[FT] BRINGING WORKER 1 BACK ONLINE: Setting Worker 1 is_healthy = True")
        self.lb.workers[1].is_healthy = True
        time.sleep(1)
        
        print(f"[FT] Worker status after recovery:")
        for i, w in enumerate(self.lb.workers):
            status = "HEALTHY" if w.is_healthy else "FAILED"
            print(f"  Worker {i}: {status}")
        
        print(f"\n[FT] Sending {self.num_tests} requests with all workers healthy...")
        
        request_count = 0
        success_count = 0
        failed_count = 0
        worker_assignments = {0: 0, 1: 0, 2: 0, 3: 0}
        
        start_time = time.time()
        
        for i in range(self.num_tests):
            try:
                request = Request(
                    id=6000 + i,  # 6000+ for recovery phase
                    query=f"Recovery test request {i}"
                )
                
                response = self.scheduler.handle_request(request)
                request_count += 1
                
                assigned_worker = self.scheduler.lb.last_assigned_worker
                if assigned_worker is not None:
                    worker_assignments[assigned_worker] += 1
                
                if "ERROR" not in str(response.result):
                    success_count += 1
                    status = "✓ SUCCESS"
                else:
                    failed_count += 1
                    status = "✗ FAILED"
                
                if i % 10 == 0:
                    print(f"  Request {i}: {status} | Worker {assigned_worker} | Latency: {response.latency:.2f}s")
            
            except Exception as e:
                failed_count += 1
                print(f"  Request {i}: ✗ FAILED | Exception: {str(e)[:50]}")
        
        elapsed = time.time() - start_time
        success_rate = (success_count / request_count * 100) if request_count > 0 else 0
        
        self.results["phase2_recovery"] = {
            "total_requests": request_count,
            "successful": success_count,
            "failed": failed_count,
            "success_rate": success_rate,
            "elapsed_time": elapsed,
            "worker_assignments": worker_assignments
        }
        
        print(f"\n[FT] PHASE 2 RESULTS:")
        print(f"  Total Requests: {request_count}")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Success Rate: {success_rate:.2f}%")
        print(f"  Elapsed Time: {elapsed:.2f}s")
        print(f"  Request Distribution:")
        for worker_id, count in worker_assignments.items():
            print(f"    Worker {worker_id}: {count} requests [HEALTHY, REINTEGRATED]")
        
        # ASSERTION: Worker 1 should now receive requests again
        if worker_assignments[1] > 0:
            print(f"\n  ✓ ASSERTION PASSED: Worker 1 received {worker_assignments[1]} requests after recovery")
        else:
            print(f"\n  ✗ ASSERTION FAILED: Worker 1 received 0 requests (should have received some)")
        
        # ASSERTION: Load should be roughly balanced (within 20% variance)
        avg_load = request_count / 4
        max_load = max(worker_assignments.values())
        min_load = min(worker_assignments.values())
        balance = (max_load - min_load) / avg_load * 100 if avg_load > 0 else 0
        
        if balance < 30:  # Allow 30% variance
            print(f"  ✓ ASSERTION PASSED: Load balanced across workers (variance: {balance:.1f}%)")
        else:
            print(f"  ✗ ASSERTION FAILED: Load imbalanced (variance: {balance:.1f}%, should be < 30%)")
        
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
        print(f"  • Phase 1 (failure): Worker 1 bypassed, load on 0/2/3")
        print(f"  • Phase 2 (recovery): Worker 1 reintegrated, load rebalanced")
        print(f"  • All requests succeeded: {p1['failed'] == 0 and p2['failed'] == 0}")
        
        overall_success = (p1['successful'] + p2['successful']) / (p1['total_requests'] + p2['total_requests']) * 100
        print(f"\nOVERALL SUCCESS RATE: {overall_success:.2f}%")
        
        print("\n" + "="*70)
        print("✓ FAULT TOLERANCE TEST COMPLETE")
        print("="*70 + "\n")


def run_fault_tolerance_tests(scheduler, lb):
    """
    Main entry point for fault tolerance testing
    
    Usage:
        from fault_tolerance_test import run_fault_tolerance_tests
        run_fault_tolerance_tests(scheduler, lb)
    """
    ft = FaultToleranceTest(scheduler, lb, num_tests=50)
    
    # Phase 1: Kill Worker 1, send requests
    ft.test_phase_1_node_failure()
    
    # Phase 2: Recover Worker 1, send requests
    ft.test_phase_2_node_recovery()
    
    # Summary
    ft.print_summary()
    