# Distributed AI Inference System

Real distributed AI inference system with cloud GPU workers, adaptive load
balancing, fault tolerance, admission backpressure, GPU monitoring, RAG, and
formal scalability evaluation.

This project was developed for **CSE354 Distributed Computing** at Ain Shams
University. It began as an advanced distributed simulation and was upgraded
into a working distributed inference deployment using real Thunder Compute GPU
virtual machines.

## Project Summary

The system runs a local controller that distributes AI inference requests across
multiple remote GPU worker nodes. Each worker is a Thunder Compute VM running an
Ollama inference server. The controller performs scheduling, RAG context
retrieval, adaptive load balancing, worker health monitoring, retry logic,
circuit-breaker fault tolerance, admission backpressure, metrics collection, and
formal evidence generation.

Final evaluated deployment:

| Component | Final Configuration |
|---|---|
| Cloud provider | Thunder Compute |
| Worker count | 6 GPU workers |
| GPU per worker | 1 x NVIDIA RTX A6000 |
| Worker runtime | Ollama |
| Model | TinyLlama |
| Controller | Local Python process |
| Monitoring | Per-worker GPU metrics agent |
| Highest evaluated load | 1000 requests / 120 load threads |
| Final success rate | 100% |

## Key Features

- Real remote cloud GPU workers, not simulated workers.
- Configurable worker endpoints through `LLM_SERVER_URLS`.
- Ollama/OpenAI-compatible inference using `/v1/chat/completions`.
- Retrieval-Augmented Generation using a FAISS-backed document index.
- Adaptive load balancing based on:
  - worker health state
  - in-flight request count
  - queue pressure
  - EWMA latency
  - failure rate
  - recovery/degraded penalties
- Fault tolerance with:
  - worker health checks
  - circuit breaker states
  - cooldown and recovery
  - retry-on-different-worker behavior
- Admission backpressure when all workers are saturated.
- GPU monitoring with `nvidia-smi` telemetry:
  - utilization
  - memory usage
  - temperature
  - power draw
- Formal load evaluation with saved CSV/JSON evidence.
- Report package with IEEE-style report draft and generated graphs.

## Architecture

```text
Load Test Clients
        |
        v
Scheduler / Controller
        |
        v
Adaptive Load Balancer
        |
        v
GPU Worker Adapters
        |
        v
Thunder Compute Ollama GPU VMs
        |
        v
TinyLlama Inference

Side channels:
RAG / FAISS context retrieval
GPU metrics polling
Evidence generation
Monitoring dashboard
```

Generated architecture figure:

```text
report/figures/architecture.svg
```

## Repository Structure

```text
.
├── main.py                         # Main controller entry point
├── config.py                       # Environment-driven runtime config
├── client/
│   └── load_generator.py           # Concurrent load generator
├── common/
│   ├── errors.py                   # Capacity/admission error types
│   ├── gpu_metrics.py              # Controller-side GPU metric polling
│   ├── metrics.py                  # Latency and success-rate metrics
│   └── models.py                   # Request/Response models
├── lb/
│   └── load_balancer.py            # Adaptive load balancing + backpressure
├── master/
│   └── scheduler.py                # Scheduling, retries, active tasks
├── workers/
│   └── gpu_worker.py               # Logical worker adapter and circuit breaker
├── llm/
│   └── inference.py                # Ollama/OpenAI-compatible LLM calls
├── rag/
│   ├── document_ingester.py        # FAISS document ingestion
│   ├── embedding_pipeline.py       # Embedding generation
│   └── retriever.py                # Top-k context retrieval
├── monitoring/
│   └── dashboard.py                # Simple monitoring dashboard/API
├── scripts/
│   ├── gpu_metrics_agent.py        # Runs on each GPU VM
│   ├── run_formal_evaluation.py    # Formal load-test matrix runner
│   ├── run_thunder_6node_eval.sh   # Final six-worker evaluation script
│   ├── run_thunder_llama_server.sh # llama.cpp worker helper
│   └── generate_report_graphs.py   # Builds report SVG graphs
├── docs/
│   ├── evaluation_plan.md          # Evaluation methodology
│   └── thunder_phase1.md           # Thunder deployment notes
├── report/
│   ├── ieee_report.md              # Full IEEE-style report draft
│   ├── ieee_report.tex             # IEEEtran starter version
│   ├── screenshots_needed.md       # Required screenshot checklist
│   ├── evaluation_summary_table.csv
│   └── figures/                    # Generated SVG graphs
└── evaluation_results/             # Formal run evidence, ignored by git
```

## Final Evaluation Results

The final six-worker evaluation used the following matrix:

| Users | Load Threads | Success Rate | Failed Requests | Throughput | Avg Latency | P50 | P99 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 50 | 10 | 100.0% | 0 | 2.133 req/s | 2.097s | 1.466s | 5.490s |
| 100 | 20 | 100.0% | 0 | 3.778 req/s | 2.895s | 2.551s | 9.844s |
| 250 | 40 | 100.0% | 0 | 4.773 req/s | 5.092s | 3.317s | 15.795s |
| 500 | 80 | 100.0% | 0 | 5.686 req/s | 9.791s | 3.750s | 58.728s |
| 1000 | 120 | 100.0% | 0 | 6.905 req/s | 13.931s | 3.372s | 115.463s |

The 1000-request run also recorded:

| Metric | Value |
|---|---:|
| Total requests | 1000 |
| Failed requests | 0 |
| Admission waits | 126 |
| Admission timeouts | 0 |
| Worker states | All `HEALTHY` |
| GPU metric samples | 90 |
| Max GPU utilization | 28% |
| Max GPU memory used | 1081 MB |
| Max GPU temperature | 52 C |
| Max GPU power draw | 128.65 W |

Main evidence files:

```text
evaluation_results/final_eval_6workers_summary.csv
evaluation_results/final_eval_6workers_users1000_threads120/console.log
evaluation_results/final_eval_6workers_users1000_threads120/metrics_summary.json
evaluation_results/final_eval_6workers_users1000_threads120/run_evidence.json
evaluation_results/final_eval_6workers_users1000_threads120/latencies.csv
evaluation_results/final_eval_6workers_users1000_threads120/gpu_metrics_history.csv
```

## Two-Worker Baseline vs Six-Worker Final System

The original two-worker evaluation exposed the scalability bottleneck. At high
concurrency, workers reached their in-flight capacity and excess requests were
rejected. The final system fixed this by scaling to six workers and adding
admission backpressure.

| Users | Two-Worker Success Rate | Six-Worker Success Rate |
|---:|---:|---:|
| 50 | 100.0% | 100.0% |
| 100 | 100.0% | 100.0% |
| 250 | 37.2% | 100.0% |
| 500 | 9.8% | 100.0% |
| 1000 | 5.0% | 100.0% |

Generated comparison graph:

```text
report/figures/success_rate_scaling.svg
```

## Requirements

### Local Controller

- Python 3.10+; Python 3.12 was used during final evaluation.
- macOS, Linux, or Windows.
- Network access to worker endpoints.

Python dependencies:

```bash
pip install -r requirements.txt
```

### Thunder Worker Nodes

For the final cloud deployment:

- Thunder Compute account and CLI.
- Ollama template instances.
- One A6000 GPU per node.
- Forwarded ports:
  - `11434` for Ollama API
  - `9100` for GPU metrics agent

## Quick Start: Local Controller with Existing Thunder Workers

Clone the repository:

```bash
git clone https://github.com/carolrb-123/distributedComputingProject.git
cd distributedComputingProject
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set the six-worker Thunder configuration:

```bash
export LLM_SERVER_URLS="https://ye96jt3q-11434.thundercompute.net,https://a5oxns3p-11434.thundercompute.net,https://uw01uuc2-11434.thundercompute.net,https://xkj8xszu-11434.thundercompute.net,https://hz8878v2-11434.thundercompute.net,https://ow2vbplc-11434.thundercompute.net"
export GPU_METRICS_URLS="https://ye96jt3q-9100.thundercompute.net,https://a5oxns3p-9100.thundercompute.net,https://uw01uuc2-9100.thundercompute.net,https://xkj8xszu-9100.thundercompute.net,https://hz8878v2-9100.thundercompute.net,https://ow2vbplc-9100.thundercompute.net"
export LLM_MODEL=tinyllama
export LLM_HEALTH_PATH=/api/version
export NUM_WORKERS=6
export LLM_MAX_TOKENS=16
export SCHEDULER_REQUEST_TIMEOUT=240
export SCHEDULER_ADMISSION_TIMEOUT=300
export SCHEDULER_ADMISSION_POLL_INTERVAL=0.05
export WORKER_THREADS=2
export WORKER_QUEUE_SIZE=8
export WORKER_MAX_IN_FLIGHT=10
export LOAD_BALANCER_POLICY=adaptive
```

Run a small smoke test:

```bash
export NUM_USERS=12
export LOAD_TEST_THREADS=6
python main.py
```

Run the full formal six-worker evaluation:

```bash
scripts/run_thunder_6node_eval.sh
```

## Thunder Deployment Guide

The detailed Thunder guide is in:

```text
docs/thunder_phase1.md
```

### 1. Create Ollama Worker VMs

Create one Thunder VM per worker using the Ollama template. The final demo used
six A6000 VMs.

Example:

```bash
tnr create --mode prototyping --template ollama --gpu a6000 --num-gpus 1 --vcpus 4 --disk-size-gb 100 --yes
```

### 2. Forward Worker Ports

For each instance:

```bash
tnr ports forward <instance_id> --add 11434
tnr ports forward <instance_id> --add 9100
tnr ports list
```

### 3. Start Ollama and Pull Model on Each VM

Connect to each VM:

```bash
tnr connect <instance_id>
```

Inside the VM:

```bash
export OLLAMA_HOST=0.0.0.0:11434
nohup ollama serve > ~/ollama.log 2>&1 &
ollama pull tinyllama
```

### 4. Start GPU Metrics Agent on Each VM

Inside each VM:

```bash
git clone -b phase1-thunder-gpu-workers https://github.com/carolrb-123/distributedComputingProject.git ~/distributedProject
cd ~/distributedProject
nohup python3 scripts/gpu_metrics_agent.py > ~/gpu_metrics_agent.log 2>&1 &
```

Verify locally on the VM:

```bash
curl http://127.0.0.1:11434/api/version
curl http://127.0.0.1:9100/metrics
```

Verify from the controller machine:

```bash
curl https://<uuid>-11434.thundercompute.net/api/version
curl https://<uuid>-9100.thundercompute.net/metrics
```

## Running the System

Main command:

```bash
python main.py
```

Useful environment variables:

| Variable | Purpose | Typical Final Value |
|---|---|---|
| `LLM_SERVER_URLS` | Comma-separated inference endpoints | six Thunder `11434` URLs |
| `GPU_METRICS_URLS` | Comma-separated metrics endpoints | six Thunder `9100` URLs |
| `LLM_MODEL` | Ollama model name | `tinyllama` |
| `LLM_HEALTH_PATH` | Health endpoint | `/api/version` |
| `NUM_WORKERS` | Logical worker count | `6` |
| `NUM_USERS` | Requests in one run | `50` to `1000` |
| `LOAD_TEST_THREADS` | Client load threads | `10` to `120` |
| `WORKER_THREADS` | Per-worker local adapter threads | `2` |
| `WORKER_QUEUE_SIZE` | Per-worker queue size | `8` |
| `WORKER_MAX_IN_FLIGHT` | Per-worker capacity limit | `10` |
| `LOAD_BALANCER_POLICY` | Routing policy | `adaptive` |
| `SCHEDULER_REQUEST_TIMEOUT` | Worker response timeout | `240` |
| `SCHEDULER_ADMISSION_TIMEOUT` | Backpressure wait limit | `300` |
| `GPU_METRICS_INTERVAL` | GPU polling interval | `2` |

## Formal Evaluation

Run the default formal matrix:

```bash
scripts/run_thunder_6node_eval.sh
```

Override the matrix:

```bash
EVAL_ID=smoke_eval_6workers EVAL_MATRIX="24:12" scripts/run_thunder_6node_eval.sh
```

The formal runner creates:

```text
evaluation_results/<run_id>/console.log
evaluation_results/<run_id>/latencies.csv
evaluation_results/<run_id>/metrics_summary.json
evaluation_results/<run_id>/run_evidence.json
evaluation_results/<run_id>/gpu_metrics_history.csv
evaluation_results/<run_id>/gpu_metrics_history.json
```

## Monitoring

Start the controller with dashboard enabled:

```bash
export ENABLE_MONITORING_DASHBOARD=true
export MONITORING_HOST=127.0.0.1
export MONITORING_PORT=8080
python main.py
```

Open:

```text
http://127.0.0.1:8080
```

JSON status endpoint:

```text
http://127.0.0.1:8080/api/status
```

Worker-level GPU endpoint:

```bash
curl https://<uuid>-9100.thundercompute.net/metrics
```

## Fault Tolerance Testing

Run simulated circuit-breaker tests:

```bash
export RUN_FAULT_TOLERANCE_TESTS=true
export FAULT_TOLERANCE_TEST_REQUESTS=4
export NUM_USERS=4
export LOAD_TEST_THREADS=2
python main.py
```

Manual Thunder node failure test:

1. Start the controller with at least two worker URLs.
2. Connect to one Thunder worker.
3. Stop Ollama:

```bash
pkill ollama
```

4. Run a small load test.
5. Confirm the worker becomes `DEGRADED` or `UNHEALTHY`.
6. Restart Ollama:

```bash
export OLLAMA_HOST=0.0.0.0:11434
nohup ollama serve > ~/ollama.log 2>&1 &
```

7. Confirm health checks move the worker through `RECOVERING` back to
   `HEALTHY`.

## Report Package

The report package is in:

```text
report/
```

Important files:

| File | Purpose |
|---|---|
| `report/ieee_report.md` | Full IEEE-style report draft |
| `report/ieee_report.tex` | IEEEtran LaTeX starter |
| `report/screenshots_needed.md` | Screenshot checklist |
| `report/evaluation_summary_table.csv` | Final evaluation table |
| `report/figures/*.svg` | Generated graphs |

Regenerate graphs:

```bash
python3 scripts/generate_report_graphs.py
```

## Generated Figures

The following figures are generated from the saved evaluation evidence:

```text
report/figures/architecture.svg
report/figures/success_rate_scaling.svg
report/figures/throughput_scaling.svg
report/figures/latency_summary_6workers.svg
report/figures/latency_cdf_1000.svg
report/figures/worker_assignments_1000.svg
report/figures/admission_backpressure.svg
report/figures/gpu_summary_6workers.svg
```

## Demo Checklist

Use this sequence during the live demo:

1. Show Thunder fleet:

```bash
tnr status
tnr ports list
```

2. Verify worker APIs:

```bash
for id in ye96jt3q a5oxns3p uw01uuc2 xkj8xszu hz8878v2 ow2vbplc; do
  echo "$id:"
  curl -s "https://${id}-11434.thundercompute.net/api/version"
  echo
done
```

3. Verify GPU metrics:

```bash
curl -s https://uw01uuc2-9100.thundercompute.net/metrics
```

4. Show final evaluation summary:

```text
evaluation_results/final_eval_6workers_summary.csv
```

5. Show 1000-request evidence:

```text
evaluation_results/final_eval_6workers_users1000_threads120/metrics_summary.json
evaluation_results/final_eval_6workers_users1000_threads120/run_evidence.json
evaluation_results/final_eval_6workers_users1000_threads120/gpu_metrics_history.csv
```

6. Show report graphs:

```text
report/figures/success_rate_scaling.svg
report/figures/admission_backpressure.svg
report/figures/worker_assignments_1000.svg
```

## Local llama.cpp Option

The final evaluated system uses Thunder Ollama workers. A local llama.cpp path
is still available for development, but it is not the final evaluated
deployment.

To use local llama.cpp servers:

1. Build llama.cpp.
2. Start multiple `llama-server` instances on different ports.
3. Set:

```bash
export LLM_SERVER_URLS="http://localhost:8888,http://localhost:8889,http://localhost:8890,http://localhost:8891"
export LLM_HEALTH_PATH=/health
export NUM_WORKERS=4
```

4. Run:

```bash
python main.py
```

## Troubleshooting

### `No workers currently available`

This usually means every worker is at capacity. Increase admission wait time or
scale out workers:

```bash
export SCHEDULER_ADMISSION_TIMEOUT=300
export SCHEDULER_ADMISSION_POLL_INTERVAL=0.05
```

### Public Thunder URL does not respond

Check the instance and port forwarding:

```bash
tnr status
tnr ports list
tnr ports forward <instance_id> --add 11434
tnr ports forward <instance_id> --add 9100
```

### Ollama API is not listening

On the worker VM:

```bash
export OLLAMA_HOST=0.0.0.0:11434
nohup ollama serve > ~/ollama.log 2>&1 &
curl http://127.0.0.1:11434/api/version
```

### Model is missing

On the worker VM:

```bash
ollama pull tinyllama
```

### GPU metrics endpoint is empty or unavailable

On the worker VM:

```bash
nvidia-smi
cd ~/distributedProject
nohup python3 scripts/gpu_metrics_agent.py > ~/gpu_metrics_agent.log 2>&1 &
curl http://127.0.0.1:9100/metrics
```

### High p99 latency

High p99 latency under 500 to 1000 requests is expected when backpressure is
enabled. The system prioritizes completing requests successfully rather than
drops. To reduce p99 latency:

- add more GPU workers
- reduce `LLM_MAX_TOKENS`
- use a faster model
- tune `WORKER_THREADS`, `WORKER_QUEUE_SIZE`, and `WORKER_MAX_IN_FLIGHT`
- increase the number of production-grade GPU nodes

## Cost Note

The final demonstration used six Thunder A6000 nodes. During setup, Thunder
estimated each node at approximately `$0.35/hr`, for a six-node pool around
`$2.10/hr`. Delete unused demo nodes after testing:

```bash
tnr delete <instance_id>
```

## References

- Thunder Compute templates documentation:  
  https://www.thundercompute.com/docs/guides/using-instance-templates
- Ollama OpenAI compatibility:  
  https://docs.ollama.com/api/openai-compatibility
- FAISS documentation:  
  https://faiss.ai/index.html
- FAISS GitHub repository:  
  https://github.com/facebookresearch/faiss
- FAISS paper DOI:  
  https://doi.org/10.1109/TBDATA.2019.2921572

## License

This repository was created for academic coursework. Add a formal license file
if the project will be reused or published beyond the course submission.
