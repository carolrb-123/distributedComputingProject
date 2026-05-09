"""
Phase 3 Entry Point - Real RAG + Real LLM + Fault Tolerance
"""
import config
from common.gpu_metrics import GPUMetricsCollector
from workers.gpu_worker import GPUWorker
from lb.load_balancer import LoadBalancer
from master.scheduler import Scheduler
from client.load_generator import run_load_test
from common.metrics import MetricsCollector
from rag.embedding_pipeline import EmbeddingPipeline
from rag.document_ingester import DocumentIngester
from rag.retriever import initialize_retriever
from fault_tolerance_test import run_fault_tolerance_tests
from monitoring.dashboard import MonitoringDashboard
import os
import json
from datetime import datetime

def setup_rag_pipeline():
    """Initialize RAG components"""
    print("\n[Main] Setting up RAG pipeline...")
    
    embedder = EmbeddingPipeline(config.EMBEDDING_MODEL)
    ingester = DocumentIngester(embedder)
    
    sample_qa = [
        {
            "question": "What is distributed computing?",
            "answer": "Distributed computing is a field of computer science that studies distributed systems, which are computing systems whose components are located on different networked computers, which communicate and coordinate their actions by passing messages to one another."
        },
        {
            "question": "What is load balancing?",
            "answer": "Load balancing is the process of distributing network traffic and computing workloads across multiple servers to optimize resource utilization, maximize throughput, minimize response time, and avoid overload on any single resource."
        },
        {
            "question": "What is a GPU?",
            "answer": "A Graphics Processing Unit (GPU) is a specialized electronic circuit designed to rapidly manipulate and alter memory to accelerate the creation of images. Modern GPUs are used for deep learning, scientific computing, and parallel processing tasks."
        },
        {
            "question": "What is RAG?",
            "answer": "Retrieval-Augmented Generation (RAG) is a technique that combines information retrieval with text generation. It retrieves relevant documents or context from a knowledge base and uses them to augment the input to a language model, improving answer quality and reducing hallucinations."
        },
        {
            "question": "What is fault tolerance?",
            "answer": "Fault tolerance is the ability of a system to continue operating correctly in the event of some component failures. A fault-tolerant system can maintain operation despite failures by detecting failed components and reassigning their work."
        }
    ]
    
    import json
    qa_file = "sample_qa.json"
    with open(qa_file, 'w') as f:
        json.dump(sample_qa, f)
    
    ingester.ingest_json_qa(qa_file)
    ingester.build_index()
    initialize_retriever(ingester)
    
    print("[Main] RAG pipeline ready\n")

def get_run_id():
    if config.RUN_ID:
        return config.RUN_ID
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def build_evidence_payload(run_id, metrics, scheduler, workers, lb, gpu_monitor):
    return {
        "run_id": run_id,
        "created_at": datetime.now().isoformat(),
        "config": {
            "llm_server_urls": config.LLM_SERVER_URLS,
            "gpu_metrics_urls": config.GPU_METRICS_URLS,
            "llm_model": config.LLM_MODEL,
            "num_workers": config.NUM_WORKERS,
            "num_users": config.NUM_USERS,
            "load_test_threads": config.LOAD_TEST_THREADS,
            "worker_threads": config.WORKER_THREADS,
            "worker_queue_size": config.WORKER_QUEUE_SIZE,
            "worker_max_in_flight": config.WORKER_MAX_IN_FLIGHT,
            "load_balancer_policy": config.LOAD_BALANCER_POLICY,
            "scheduler_request_timeout": config.SCHEDULER_REQUEST_TIMEOUT,
            "llm_max_tokens": config.LLM_MAX_TOKENS,
            "run_fault_tolerance_tests": config.RUN_FAULT_TOLERANCE_TESTS,
        },
        "metrics": metrics.get_summary(),
        "scheduler": scheduler.get_worker_status() if scheduler else {},
        "workers": [worker.get_status() for worker in workers],
        "load_balancer": lb.get_status() if hasattr(lb, "get_status") else {},
        "gpu": gpu_monitor.snapshot() if gpu_monitor else {},
    }

def save_evidence(run_id, metrics, scheduler, workers, lb, gpu_monitor):
    evidence_dir = os.path.join(config.EVIDENCE_DIR, run_id)
    os.makedirs(evidence_dir, exist_ok=True)

    metrics.save_to_csv(os.path.join(evidence_dir, "latencies.csv"))
    metrics.save_summary_json(os.path.join(evidence_dir, "metrics_summary.json"))

    payload = build_evidence_payload(run_id, metrics, scheduler, workers, lb, gpu_monitor)
    with open(os.path.join(evidence_dir, "run_evidence.json"), "w") as f:
        json.dump(payload, f, indent=2)

    if gpu_monitor:
        gpu_monitor.save_history_json(os.path.join(evidence_dir, "gpu_metrics_history.json"))
        gpu_monitor.save_history_csv(os.path.join(evidence_dir, "gpu_metrics_history.csv"))

    print(f"[Evidence] Saved run evidence to {evidence_dir}")
    return evidence_dir

def main():
    print("\n" + "="*70)
    print("PHASE 3: DISTRIBUTED LLM SYSTEM WITH RAG & FAULT TOLERANCE")
    print("="*70 + "\n")
    
    run_id = get_run_id()
    metrics = MetricsCollector()
    gpu_monitor = GPUMetricsCollector()
    dashboard = None
    
    setup_rag_pipeline()
    
    print("[Main] Creating workers...")
    workers = [
        GPUWorker(
            i,
            config.LLM_SERVER_URLS[i % len(config.LLM_SERVER_URLS)]
        )
        for i in range(config.NUM_WORKERS)
    ]
    print(f"[Main] Created {config.NUM_WORKERS} workers\n")
    for worker in workers:
        print(f"[Main] Worker {worker.id} -> {worker.server_url}")
    print()
    
    print("[Main] Creating load balancer...")
    lb = LoadBalancer(workers)
    print("[Main] Load balancer ready\n")
    
    print("[Main] Creating scheduler...")
    scheduler = Scheduler(lb, metrics)
    print("[Main] Scheduler ready\n")

    if config.GPU_METRICS_URLS:
        print(f"[Main] Starting GPU metrics polling for {len(config.GPU_METRICS_URLS)} workers...")
        gpu_monitor.start()
        gpu_monitor.poll_once()
        print("[Main] GPU metrics polling ready\n")
    else:
        print("[Main] GPU metrics polling disabled. Set GPU_METRICS_URLS to enable.\n")

    if config.ENABLE_MONITORING_DASHBOARD:
        dashboard = MonitoringDashboard(
            config.MONITORING_HOST,
            config.MONITORING_PORT,
            metrics,
            scheduler,
            workers,
            lb,
            gpu_monitor,
        )
        dashboard.start()

    # ─────────────────────────────────────────
    # FAULT TOLERANCE TESTS (run before main load test)
    # ─────────────────────────────────────────
    if config.RUN_FAULT_TOLERANCE_TESTS:
        print("[Main] Running fault tolerance tests...\n")
        run_fault_tolerance_tests(scheduler, lb)
    else:
        print("[Main] Skipping fault tolerance tests. Set RUN_FAULT_TOLERANCE_TESTS=true to enable.\n")

    # ─────────────────────────────────────────
    # MAIN LOAD TEST
    # ─────────────────────────────────────────
    print(f"[Main] Starting load test with {config.NUM_USERS} users...\n")
    run_load_test(scheduler, num_users=config.NUM_USERS)
    
    print("\n")
    metrics.print_summary()
    
    metrics.save_to_csv("metrics.csv")
    metrics.save_summary_json("metrics_summary.json")
    
    print("\nWorker Status:")
    for worker in workers:
        status = worker.get_status()
        print(
            f"  Worker {status['id']}: {status['processed_count']} requests, "
            f"State: {status.get('state', 'UNKNOWN')}, "
            f"Healthy: {status['is_healthy']}, "
            f"In-flight: {status.get('in_flight', 0)}, "
            f"Oldest Age: {status.get('oldest_in_flight_age', 0):.1f}s, "
            f"Utilization: {status.get('utilization', 0):.2f}, "
            f"EWMA Latency: {status.get('ewma_latency', 0):.3f}s, "
            f"Failure Rate: {status.get('failure_rate', 0):.2f}, "
            f"Failures: {status.get('failed_count', 0)}"
        )

    lb_status = lb.get_status() if hasattr(lb, "get_status") else {}
    if lb_status:
        print("\nLoad Balancer Status:")
        print(f"  Policy: {lb_status.get('policy')}")
        print(f"  Assignments: {lb_status.get('assignment_counts')}")
    
    print("\n" + "="*70)
    print("PHASE 3 COMPLETE")
    print("="*70 + "\n")
    
    save_evidence(run_id, metrics, scheduler, workers, lb, gpu_monitor)

    if dashboard:
        dashboard.stop()
    gpu_monitor.stop()
    scheduler.shutdown()

if __name__ == "__main__":
    main()
