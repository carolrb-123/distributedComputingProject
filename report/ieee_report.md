# Real Distributed AI Inference System with Cloud GPU Workers, Fault Tolerance, Monitoring, and Scalable Evaluation

**Authors:** Boulos Aziz, [Team Member Names]  
**Course:** CSE354 Distributed Computing, Ain Shams University, Faculty of Engineering  
**Semester:** Spring 2025/2026  
**Repository:** `https://github.com/carolrb-123/distributedComputingProject`  

## Abstract

This project implements and evaluates a real distributed AI inference system that runs large-language-model requests across multiple cloud GPU worker nodes. The system replaces a simulated distributed-computing prototype with a working deployment on six Thunder Compute NVIDIA RTX A6000 virtual machines running Ollama inference servers. A local controller performs scheduling, adaptive load balancing, request admission backpressure, health checking, retry logic, circuit-breaker-based fault tolerance, Retrieval-Augmented Generation (RAG), GPU telemetry collection, and formal evidence generation. The final evaluation tested 50, 100, 250, 500, and 1000 request workloads with increasing client concurrency. The six-worker system achieved 100% success rate in all workloads, including the 1000-request/120-thread case, with zero failed requests, zero admission timeouts, all workers healthy, and GPU telemetry collected from all six nodes. The results demonstrate that the system satisfies the course objectives of designing, implementing, configuring, and evaluating a distributed computing model for a complex real-world problem.

**Keywords:** distributed computing, cloud GPU, AI inference, load balancing, fault tolerance, monitoring, RAG, Ollama, Thunder Compute, scalability.

## I. Introduction

The CSE354 project specification requires a group project with a written report and developed code that demonstrates detailed analysis, design, testing, problem description, solution, limitations, sample output, references, and additional project information. The assessed learning outcomes include designing a distributed computing model, implementing it, configuring a working distributed environment, and communicating the work effectively.

The selected problem is distributed AI inference. Modern AI applications may receive many concurrent user requests while relying on expensive and heterogeneous GPU resources. A single inference server can become a bottleneck, fail under load, or lose availability during node failure. Therefore, a scalable inference service must distribute requests across multiple workers, detect failures, route around unhealthy nodes, measure performance, and produce evidence that the deployment is real rather than simulated.

The final system uses six real cloud GPU nodes on Thunder Compute. Each worker runs Ollama with the TinyLlama model and exposes an OpenAI-compatible chat-completions API. The controller performs RAG, schedules requests, applies adaptive load balancing, and records metrics. The project evolved through several phases: converting workers into real Thunder GPU nodes, implementing fault tolerance, adding professional load balancing, collecting monitoring evidence, improving concurrency behavior through admission backpressure, and performing formal load evaluation.

## II. Problem Statement and Objectives

The original project was an advanced distributed simulation. The required upgrade was to transform it into a real distributed AI inference system. The main objectives were:

1. Replace local/simulated workers with real cloud GPU worker nodes.
2. Support multiple concurrent users with scalable scheduling.
3. Detect and tolerate worker failures.
4. Balance load based on live worker state instead of static round-robin routing only.
5. Monitor GPU utilization, memory, temperature, and power draw.
6. Produce formal evaluation evidence for scalability, reliability, and performance.
7. Demonstrate a credible 1000-user evaluation.

The main technical challenge was not only to make inference calls succeed, but also to handle saturation correctly. In an early two-worker evaluation, requests failed when both workers reached their in-flight capacity. This was a capacity-management issue, not a worker-health failure. The final design therefore separates true worker failure from temporary saturation and uses admission backpressure to wait for capacity before rejecting a request.

## III. Requirement Traceability

| Project / Course Requirement | Implementation Evidence |
|---|---|
| Design a distributed computing model | Scheduler, adaptive load balancer, six cloud GPU workers, RAG pipeline, metrics collector |
| Implement a distributed computing model | Python modules in `master/`, `lb/`, `workers/`, `llm/`, `rag/`, `monitoring/`, and `common/` |
| Configure a working distributed environment | Six Thunder Compute A6000 VMs using Ollama APIs and forwarded monitoring ports |
| Demonstrate scalability | Formal matrix from 50 to 1000 requests; 100% success in six-worker evaluation |
| Demonstrate fault tolerance | Circuit breaker states, health checks, retry-on-different-worker behavior |
| Demonstrate monitoring | GPU metrics agent on port 9100, dashboard API, evidence CSV/JSON files |
| Provide testing and sample output | `evaluation_results/final_eval_6workers_*` folders and console logs |
| Discuss limitations and future work | Section IX |

## IV. System Architecture

The system follows a controller-worker architecture. Clients submit concurrent requests to the controller. The controller builds retrieval context using the local FAISS-based RAG pipeline, then dispatches each request to a remote Thunder GPU worker through the adaptive load balancer. Each GPU worker adapter communicates with an Ollama server over HTTPS using the `/v1/chat/completions` API. A separate GPU metrics agent runs on each VM and exposes `/metrics` for telemetry.

**Figure 1:** `report/figures/architecture.svg`

### A. Main Components

**Client Load Generator:**  
The load generator uses a thread pool to submit a configurable number of user requests. The formal evaluation script runs a matrix of user counts and thread counts.

**Scheduler:**  
The scheduler tracks active tasks, assigns callbacks, handles request timeouts, records metrics, and supports retry-on-different-worker behavior when task reassignment is enabled.

**Adaptive Load Balancer:**  
The load balancer scores workers using worker state, in-flight load, queue pressure, observed latency, failure rate, and recovery/degraded penalties. It supports adaptive, least-connections, and round-robin policies.

**GPU Worker Adapter:**  
Each logical worker represents one remote inference endpoint. It maintains an internal queue, in-flight count, health state, failure counters, EWMA latency, and active request timestamps.

**Ollama Inference Servers:**  
Each Thunder VM runs Ollama and the TinyLlama model. Ollama provides OpenAI-compatible `/v1/chat/completions` support, allowing the project to use a standard chat completion payload.

**RAG Pipeline:**  
The system builds a small FAISS index from course-relevant question-answer documents. Each request retrieves top-k context and sends it to the model with the user query.

**Monitoring and Evidence:**  
Each GPU node runs `scripts/gpu_metrics_agent.py`, which queries `nvidia-smi` and exposes JSON metrics. The controller polls these endpoints and saves latency, summary, GPU, and evidence JSON/CSV files for each run.

## V. Implementation Details

### A. Real GPU Worker Deployment

Workers are configured through environment variables rather than hard-coded local ports. The main variables are:

```text
LLM_SERVER_URLS
GPU_METRICS_URLS
NUM_WORKERS
LLM_MODEL
LLM_HEALTH_PATH
WORKER_THREADS
WORKER_QUEUE_SIZE
WORKER_MAX_IN_FLIGHT
```

For the final evaluation, six Thunder Compute workers were used:

```text
ye96jt3q, a5oxns3p, uw01uuc2, xkj8xszu, hz8878v2, ow2vbplc
```

Each worker exposed:

```text
https://<uuid>-11434.thundercompute.net
https://<uuid>-9100.thundercompute.net
```

### B. Fault Tolerance

The worker state machine supports four states:

```text
HEALTHY, DEGRADED, UNHEALTHY, RECOVERING
```

Failures increment a worker failure counter. When the counter reaches the configured threshold, the worker enters `UNHEALTHY`, opening its circuit breaker. After a cooldown interval and successful health checks, the worker moves through `RECOVERING` and back to `HEALTHY`. The scheduler can retry a failed request on another worker, preventing a single failed node from stopping the full system.

### C. Professional Load Balancing

The adaptive score combines:

- worker utilization
- queue pressure
- EWMA latency
- oldest in-flight request age
- worker failure rate
- state penalties for degraded or recovering nodes

Workers with full capacity or unhealthy states receive an infinite score and are not selected for immediate dispatch. The adaptive policy therefore reacts to performance differences between workers. In the final 1000-request run, the load balancer sent more requests to the faster workers while still using all six nodes.

### D. Admission Backpressure

The most important scalability improvement was controller-level admission backpressure. In the two-worker evaluation, high-concurrency tests produced many `No healthy workers available` errors because all workers reached `WORKER_MAX_IN_FLIGHT`. This was not a true health failure. The final system treats temporary saturation as capacity pressure and waits for a worker to become available.

The admission controls are:

```text
SCHEDULER_ADMISSION_TIMEOUT=300
SCHEDULER_ADMISSION_POLL_INTERVAL=0.05
```

This change transformed high-load behavior. In the 1000-request six-worker run, 126 requests waited for capacity, but zero timed out and zero failed.

### E. Monitoring

The GPU metrics agent collects:

- GPU name and UUID
- GPU utilization
- memory utilization
- memory used and total memory
- temperature
- power draw

For the final run, GPU telemetry was saved in:

```text
evaluation_results/final_eval_6workers_users1000_threads120/gpu_metrics_history.csv
evaluation_results/final_eval_6workers_users1000_threads120/gpu_metrics_history.json
```

## VI. Experimental Setup

### A. Hardware and Cloud Setup

| Resource | Configuration |
|---|---|
| Cloud provider | Thunder Compute |
| Number of workers | 6 |
| GPU per worker | 1 x NVIDIA RTX A6000 |
| vCPUs per worker | 4 |
| RAM per worker | 32 GB |
| Worker template | Ollama |
| Model | TinyLlama |
| Controller | Local machine |

### B. Evaluation Matrix

| Run | Users | Load Threads |
|---|---:|---:|
| 1 | 50 | 10 |
| 2 | 100 | 20 |
| 3 | 250 | 40 |
| 4 | 500 | 80 |
| 5 | 1000 | 120 |

The formal evaluation script saved each run into `evaluation_results/<run_id>/`, including:

```text
console.log
latencies.csv
metrics_summary.json
run_evidence.json
gpu_metrics_history.csv
gpu_metrics_history.json
```

## VII. Results

### A. Final Six-Worker Results

| Users / Threads | Success Rate | Failed Requests | Throughput (req/s) | Avg Latency (s) | P50 (s) | P99 (s) |
|---:|---:|---:|---:|---:|---:|---:|
| 50 / 10 | 100.0% | 0 | 2.133 | 2.097 | 1.466 | 5.490 |
| 100 / 20 | 100.0% | 0 | 3.778 | 2.895 | 2.551 | 9.844 |
| 250 / 40 | 100.0% | 0 | 4.773 | 5.092 | 3.317 | 15.795 |
| 500 / 80 | 100.0% | 0 | 5.686 | 9.791 | 3.750 | 58.728 |
| 1000 / 120 | 100.0% | 0 | 6.905 | 13.931 | 3.372 | 115.463 |

The final 1000-request run is the strongest evidence for scalability. It completed with 1000 total requests, 0 failed requests, 100% success rate, 6.905 req/s throughput, and all workers in the `HEALTHY` state.

**Figure 2:** `report/figures/success_rate_scaling.svg`  
**Figure 3:** `report/figures/throughput_scaling.svg`  
**Figure 4:** `report/figures/latency_summary_6workers.svg`  
**Figure 5:** `report/figures/latency_cdf_1000.svg`

### B. Two-Worker Baseline vs Six-Worker Final System

The two-worker baseline demonstrated the scalability bottleneck clearly:

| Users / Threads | Two-Worker Success Rate | Six-Worker Success Rate |
|---:|---:|---:|
| 50 / 10 | 100.0% | 100.0% |
| 100 / 20 | 100.0% | 100.0% |
| 250 / 40 | 37.2% | 100.0% |
| 500 / 80 | 9.8% | 100.0% |
| 1000 / 120 | 5.0% | 100.0% |

The two-worker runs failed at high concurrency because requests were rejected during capacity saturation. After scaling to six workers and adding admission backpressure, the same evaluation matrix completed successfully.

### C. Load-Balancing Behavior

In the 1000-request run, assignments were:

| Worker | Assigned Requests |
|---:|---:|
| 0 | 61 |
| 1 | 364 |
| 2 | 76 |
| 3 | 357 |
| 4 | 71 |
| 5 | 71 |

The assignment distribution was intentionally adaptive rather than perfectly equal. Workers 1 and 3 showed lower EWMA latency during the run and were favored by the load balancer. This is appropriate behavior for a performance-aware load balancer because it maximizes throughput while keeping all workers available.

**Figure 6:** `report/figures/worker_assignments_1000.svg`

### D. Admission Backpressure Results

| Users | Admission Waits | Admission Timeouts |
|---:|---:|---:|
| 50 | 0 | 0 |
| 100 | 0 | 0 |
| 250 | 0 | 0 |
| 500 | 44 | 0 |
| 1000 | 126 | 0 |

Backpressure activated only under heavier load. In the 1000-request run, 126 requests waited for worker capacity, but none timed out. This is strong evidence that the controller handles overload gracefully instead of converting temporary saturation into failed requests.

**Figure 7:** `report/figures/admission_backpressure.svg`

### E. GPU Monitoring Results

| Users | GPU Samples | Max GPU Util. | Max Memory Used | Max Temp. | Max Power |
|---:|---:|---:|---:|---:|---:|
| 50 | 15 | 0% | 1077 MB | 41 C | 122.25 W |
| 100 | 18 | 22% | 1079 MB | 44 C | 117.68 W |
| 250 | 36 | 27% | 1079 MB | 48 C | 123.64 W |
| 500 | 60 | 27% | 1081 MB | 50 C | 125.51 W |
| 1000 | 90 | 28% | 1081 MB | 52 C | 128.65 W |

The GPU data confirms that the workers were real GPU-backed nodes. The utilization percentages are moderate because TinyLlama is a small model and some time is spent in queueing, HTTP overhead, and response generation rather than continuous GPU saturation.

**Figure 8:** `report/figures/gpu_summary_6workers.svg`

## VIII. Discussion

The results show three important distributed-systems behaviors.

First, the system horizontally scales. The two-worker system was stable at 50 and 100 requests, but failed at higher concurrency. The six-worker system completed all workloads at 100% success. This demonstrates that the architecture can add more GPU workers by adding endpoints to `LLM_SERVER_URLS` and `GPU_METRICS_URLS`.

Second, the system distinguishes failure from overload. Earlier high-load failures were caused by capacity exhaustion, not node crashes. Admission backpressure fixed this by waiting for capacity. This is closer to real production behavior because overloaded systems should degrade by increasing latency before they drop requests.

Third, the system is observable. The final evidence contains console logs, latency CSVs, metrics summaries, load-balancer assignment counts, admission statistics, worker states, and GPU telemetry. This makes the result reproducible and suitable for report evidence rather than relying on screenshots alone.

## IX. Limitations and Future Work

The system is demo-ready and satisfies the distributed AI inference objective, but it still has limitations:

1. **Model size:** TinyLlama was used to keep the evaluation affordable and repeatable. Larger models would require stronger throughput tuning and possibly more GPUs.
2. **Latency tail:** The 1000-request run has a high p99 latency because backpressure queues requests instead of failing them. This is acceptable for reliability evidence, but future work should reduce tail latency.
3. **Containerization:** Dockerization was planned as a later phase but was not the main focus of this final evaluation.
4. **Security:** Public forwarded endpoints should be protected for production use. The current setup is suitable for coursework and demonstration.
5. **Autoscaling:** The system currently scales manually by adding Thunder nodes. Future work could implement automatic worker discovery and autoscaling.
6. **Persistent dashboard:** The monitoring dashboard is functional, but a production version would use a time-series database and richer visualization.

## X. Conclusion

This project successfully transformed an advanced distributed simulation into a real distributed AI inference system using cloud GPU workers. The final design includes real Thunder Compute GPU nodes, adaptive load balancing, fault tolerance, admission backpressure, RAG, GPU monitoring, and formal evaluation evidence. The six-worker deployment achieved 100% success across the full evaluation matrix, including the 1000-request/120-thread case. The implementation meets the course learning outcomes by designing, implementing, configuring, and evaluating a working distributed computing model for a complex AI inference problem.

## Appendix A: Exact Evidence Paths

```text
evaluation_results/final_eval_6workers_summary.csv
evaluation_results/final_eval_6workers_users1000_threads120/console.log
evaluation_results/final_eval_6workers_users1000_threads120/metrics_summary.json
evaluation_results/final_eval_6workers_users1000_threads120/run_evidence.json
evaluation_results/final_eval_6workers_users1000_threads120/latencies.csv
evaluation_results/final_eval_6workers_users1000_threads120/gpu_metrics_history.csv
evaluation_results/final_eval_6workers_users1000_threads120/gpu_metrics_history.json
report/evaluation_summary_table.csv
report/figures/*.svg
```

## Appendix B: Important Code Files

```text
main.py
master/scheduler.py
lb/load_balancer.py
workers/gpu_worker.py
common/errors.py
common/metrics.py
common/gpu_metrics.py
scripts/gpu_metrics_agent.py
scripts/run_formal_evaluation.py
scripts/run_thunder_6node_eval.sh
monitoring/dashboard.py
rag/retriever.py
llm/inference.py
```

## References

[1] Ain Shams University, Faculty of Engineering, "CSE354: Distributed Computing Project Specification," Spring 2025/2026.  
[2] Thunder Compute, "Use Instance Templates for AI," Thunder Compute Documentation, accessed May 10, 2026. https://www.thundercompute.com/docs/guides/using-instance-templates  
[3] Ollama, "OpenAI Compatibility," Ollama Documentation, accessed May 10, 2026. https://docs.ollama.com/api/openai-compatibility  
[4] Meta AI, "Faiss Documentation," accessed May 10, 2026. https://faiss.ai/index.html  
[5] J. Johnson, M. Douze, and H. Jegou, "Billion-Scale Similarity Search with GPUs," IEEE Transactions on Big Data, vol. 7, no. 3, pp. 535-547, 2021, doi: 10.1109/TBDATA.2019.2921572.  
[6] Meta Engineering, "Faiss: A library for efficient similarity search," 2017, accessed May 10, 2026. https://engineering.fb.com/2017/03/29/data-infrastructure/faiss-a-library-for-efficient-similarity-search/
