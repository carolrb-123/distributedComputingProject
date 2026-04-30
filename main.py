#main.py
"""
Phase 3 Entry Point - Real RAG + Real LLM + Fault Tolerance
"""
import config
from workers.gpu_worker import GPUWorker
from lb.load_balancer import LoadBalancer
from master.scheduler import Scheduler
from client.load_generator import run_load_test
from common.metrics import MetricsCollector
from rag.embedding_pipeline import EmbeddingPipeline
from rag.document_ingester import DocumentIngester
from rag.retriever import initialize_retriever
import os

def setup_rag_pipeline():
    """Initialize RAG components"""
    print("\n[Main] Setting up RAG pipeline...")
    
    # Initialize embedding pipeline
    embedder = EmbeddingPipeline(config.EMBEDDING_MODEL)
    
    # Initialize document ingester
    ingester = DocumentIngester(embedder)
    
    # Try to load sample documents
    # For now, use synthetic Q&A pairs
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
    
    # Save sample Q&A to JSON
    import json
    qa_file = "sample_qa.json"
    with open(qa_file, 'w') as f:
        json.dump(sample_qa, f)
    
    # Ingest Q&A
    ingester.ingest_json_qa(qa_file)
    
    # Build index
    ingester.build_index()
    
    # Initialize global retriever
    initialize_retriever(ingester)
    
    print("[Main] RAG pipeline ready\n")

def main():
    print("\n" + "="*70)
    print("PHASE 3: DISTRIBUTED LLM SYSTEM WITH RAG & FAULT TOLERANCE")
    print("="*70 + "\n")
    
    # Setup metrics
    metrics = MetricsCollector()
    
    # Setup RAG
    setup_rag_pipeline()
    
    # Create GPU workers
    print("[Main] Creating workers...")
    workers = [GPUWorker(i) for i in range(config.NUM_WORKERS)]
    print(f"[Main] Created {config.NUM_WORKERS} workers\n")
    
    # Create load balancer
    print("[Main] Creating load balancer...")
    lb = LoadBalancer(workers)
    print("[Main] Load balancer ready\n")
    
    # Create scheduler
    print("[Main] Creating scheduler...")
    scheduler = Scheduler(lb, metrics)
    print("[Main] Scheduler ready\n")
    
    # Run load test
    print(f"[Main] Starting load test with {config.NUM_USERS} users...\n")
    run_load_test(scheduler, num_users=config.NUM_USERS)
    
    # Print results
    print("\n")
    metrics.print_summary()
    
    # Save metrics
    metrics.save_to_csv("metrics.csv")
    metrics.save_summary_json("metrics_summary.json")
    
    # Print worker status
    print("\nWorker Status:")
    for worker in workers:
        status = worker.get_status()
        print(f"  Worker {status['id']}: {status['processed_count']} requests, Healthy: {status['is_healthy']}")
    
    print("\n" + "="*70)
    print("PHASE 3 COMPLETE")
    print("="*70 + "\n")
    
    # Shutdown
    scheduler.shutdown()

if __name__ == "__main__":
    main()