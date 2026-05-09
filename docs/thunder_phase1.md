# Phase 1: Thunder GPU Worker Deployment

This project now treats each configured LLM endpoint as a logical GPU worker.
The scheduler and load balancer can run locally while inference runs on one or
more Thunder Compute GPU VMs.

## Fast path: Thunder Ollama API workers

This avoids compiling llama.cpp on every VM. Create each Thunder instance with
the `ollama` template, then connect to it and run:

```bash
start-ollama
ollama pull tinyllama
```

Forward Ollama's API port:

```bash
tnr ports forward <instance_id> --add 11434
tnr ports list
```

Run the controller with the forwarded Ollama URLs:

```bash
export LLM_SERVER_URLS="https://vm-a-11434.thundercompute.net,https://vm-b-11434.thundercompute.net"
export LLM_MODEL=tinyllama
export LLM_HEALTH_PATH=/api/version
export NUM_WORKERS=2
export NUM_USERS=50
export LOAD_TEST_THREADS=20
export RUN_FAULT_TOLERANCE_TESTS=false
python main.py
```

Ollama exposes an OpenAI-compatible `/v1/chat/completions` endpoint, so the
project can use it as a real remote inference worker while skipping local CUDA
compilation.

## Custom path: Build llama.cpp workers

## 1. Start one llama.cpp server per Thunder VM

On each Thunder VM:

```bash
git clone <your-repo-url> distributedProject
cd distributedProject
./scripts/run_thunder_llama_server.sh
```

Useful overrides:

```bash
PORT=8888 MODEL_DIR=/ephemeral/models ./scripts/run_thunder_llama_server.sh
```

Use `/ephemeral` for model weights when the VM has ephemeral storage and you do
not need the downloaded model to survive instance deletion or modification.

## 2. Forward the inference port

From your local machine:

```bash
tnr ports forward <instance_id> --add 8888
tnr ports list
```

Copy each forwarded HTTPS URL. It should look like:

```text
https://<instance-uuid>-8888.thundercompute.net
```

## 3. Run the scheduler/load test against Thunder workers

On your local machine or on a separate controller VM:

```bash
export LLM_SERVER_URLS="https://vm-a-8888.thundercompute.net,https://vm-b-8888.thundercompute.net"
export NUM_WORKERS=2
export NUM_USERS=100
export LOAD_TEST_THREADS=50
export RUN_FAULT_TOLERANCE_TESTS=false
python main.py
```

Health checks use `/health`; inference uses `/v1/chat/completions`.

## 4. Scale up

Add more Thunder VMs, start the same server script on each, forward port `8888`,
then append each URL to `LLM_SERVER_URLS`. `NUM_WORKERS` should usually match
the number of URLs.

## Notes

- Bind worker servers to `0.0.0.0`, not localhost, so Thunder port forwarding
  can reach them.
- Do not reinstall CUDA on Thunder images. Use a Python venv or rebuild app
  dependencies if compatibility issues appear.
- Docker support on Thunder is experimental. For Phase 1, run llama.cpp
  directly on the VM.

## CUDA compiler troubleshooting

If llama.cpp fails with `CMAKE_CUDA_COMPILER-NOTFOUND`, CMake cannot find
`nvcc`, the CUDA compiler.

Check:

```bash
which nvcc
ls -l /usr/local/cuda/bin/nvcc
nvidia-smi
```

If `nvcc` exists under `/usr/local/cuda/bin`, expose it before running the
worker script:

```bash
export PATH=/usr/local/cuda/bin:$PATH
export CUDACXX=/usr/local/cuda/bin/nvcc
PORT=8888 MODEL_DIR=/ephemeral/models ./scripts/run_thunder_llama_server.sh
```

If `nvcc` is missing, use a Thunder Production-mode Base instance. llama.cpp's
CUDA backend is compiled from CUDA source and needs full CUDA toolkit/compiler
compatibility. A CPU-only fallback is available for debugging, but it is not the
target Phase 1 GPU setup:

```bash
BUILD_CUDA=off PORT=8888 MODEL_DIR=/ephemeral/models ./scripts/run_thunder_llama_server.sh
```

## Phase 2 fault-tolerance validation

The controller now has per-worker circuit breakers, cooldowns, recovery states,
and retry-on-different-worker behavior for explicit worker failures.

Run a simulated circuit-breaker test:

```bash
export LLM_SERVER_URLS="https://vm-a-11434.thundercompute.net,https://vm-b-11434.thundercompute.net"
export LLM_MODEL=tinyllama
export LLM_HEALTH_PATH=/api/version
export NUM_WORKERS=2
export NUM_USERS=4
export LOAD_TEST_THREADS=2
export LLM_MAX_TOKENS=16
export SCHEDULER_REQUEST_TIMEOUT=120
export FAULT_TOLERANCE_TEST_REQUESTS=4
export RUN_FAULT_TOLERANCE_TESTS=true
python main.py
```

For a real Thunder node failure test:

1. Keep the controller running with both worker URLs configured.
2. Connect to one Thunder VM.
3. Stop Ollama on that VM:

```bash
pkill ollama
```

4. Send a small load test from the controller.
5. Confirm the unhealthy worker enters `UNHEALTHY` and traffic routes to the
   other worker.
6. Restart Ollama on the VM:

```bash
start-ollama
```

7. After `WORKER_FAILURE_COOLDOWN`, health checks should move it through
   `RECOVERING` back to `HEALTHY`.

## Phase 3 adaptive load balancing

The controller now supports policy-based routing with adaptive scoring. The
default policy is `adaptive`, which considers:

- worker health state
- in-flight requests
- oldest in-flight request age
- queue pressure
- EWMA latency
- observed failure rate
- recovery/degraded penalties

Run the recommended Thunder test:

```bash
export LLM_SERVER_URLS="https://vm-a-11434.thundercompute.net,https://vm-b-11434.thundercompute.net"
export LLM_MODEL=tinyllama
export LLM_HEALTH_PATH=/api/version
export NUM_WORKERS=2
export NUM_USERS=20
export LOAD_TEST_THREADS=6
export LLM_MAX_TOKENS=16
export SCHEDULER_REQUEST_TIMEOUT=120
export SCHEDULER_ADMISSION_TIMEOUT=300
export SCHEDULER_ADMISSION_POLL_INTERVAL=0.05
export WORKER_THREADS=2
export WORKER_QUEUE_SIZE=8
export WORKER_MAX_IN_FLIGHT=10
export LOAD_BALANCER_POLICY=adaptive
python main.py
```

Compare policies:

```bash
export LOAD_BALANCER_POLICY=round_robin
python main.py

export LOAD_BALANCER_POLICY=least_connections
python main.py

export LOAD_BALANCER_POLICY=adaptive
python main.py
```

Useful tuning knobs:

```bash
export LB_UTILIZATION_WEIGHT=3.0
export LB_QUEUE_WEIGHT=1.5
export LB_LATENCY_WEIGHT=2.5
export LB_IN_FLIGHT_AGE_WEIGHT=0.5
export LB_FAILURE_WEIGHT=4.0
export LB_STATE_DEGRADED_PENALTY=5.0
export LB_STATE_RECOVERING_PENALTY=2.0
export LB_EWMA_ALPHA=0.35
```

If one Thunder worker is much slower than another, `adaptive` should gradually
favor the faster worker while still using both when capacity allows.

## Monitoring, GPU utilization, and formal evidence

Start one GPU metrics agent on each Thunder VM:

```bash
cd distributedProject
git pull origin phase1-thunder-gpu-workers
python3 scripts/gpu_metrics_agent.py
```

The agent listens on port `9100` and exposes:

```text
/health
/metrics
```

Forward the metrics port for each Thunder VM from your local machine:

```bash
tnr ports forward <instance_id> --add 9100
tnr ports list
```

Test the metrics URLs:

```bash
curl https://vm-a-9100.thundercompute.net/metrics
curl https://vm-b-9100.thundercompute.net/metrics
```

Run one monitored load test:

```bash
export LLM_SERVER_URLS="https://vm-a-11434.thundercompute.net,https://vm-b-11434.thundercompute.net"
export GPU_METRICS_URLS="https://vm-a-9100.thundercompute.net,https://vm-b-9100.thundercompute.net"
export LLM_MODEL=tinyllama
export LLM_HEALTH_PATH=/api/version
export NUM_WORKERS=2
export NUM_USERS=100
export LOAD_TEST_THREADS=20
export LLM_MAX_TOKENS=16
export SCHEDULER_REQUEST_TIMEOUT=180
export SCHEDULER_ADMISSION_TIMEOUT=300
export SCHEDULER_ADMISSION_POLL_INTERVAL=0.05
export WORKER_THREADS=2
export WORKER_QUEUE_SIZE=8
export WORKER_MAX_IN_FLIGHT=10
export LOAD_BALANCER_POLICY=adaptive
export ENABLE_MONITORING_DASHBOARD=true
python main.py
```

Open the dashboard while the test runs:

```text
http://127.0.0.1:8080
```

Each run writes evidence to:

```text
evaluation_results/<run_id>/
```

The evidence folder contains:

```text
latencies.csv
metrics_summary.json
run_evidence.json
gpu_metrics_history.csv
gpu_metrics_history.json
```

Run a formal evaluation matrix:

```bash
export LLM_SERVER_URLS="https://vm-a-11434.thundercompute.net,https://vm-b-11434.thundercompute.net"
export GPU_METRICS_URLS="https://vm-a-9100.thundercompute.net,https://vm-b-9100.thundercompute.net"
export LLM_MODEL=tinyllama
export LLM_HEALTH_PATH=/api/version
export LLM_MAX_TOKENS=16
export SCHEDULER_REQUEST_TIMEOUT=180
export SCHEDULER_ADMISSION_TIMEOUT=300
export SCHEDULER_ADMISSION_POLL_INTERVAL=0.05
export WORKER_THREADS=2
export WORKER_QUEUE_SIZE=8
export WORKER_MAX_IN_FLIGHT=10
export LOAD_BALANCER_POLICY=adaptive
export EVAL_MATRIX="50:10,100:20,250:40,500:80,1000:120"
.venv/bin/python3.12 scripts/run_formal_evaluation.py
```

For 250+ concurrent-user cases, the load balancer will apply admission
backpressure when both GPU workers are saturated. In the evidence JSON, check
`load_balancer.admission.wait_count`, `avg_wait_time_sec`, and
`timeout_count`.

## Current 6-node Thunder pool

The current scaled Thunder pool is:

```text
0 ye96jt3q  https://ye96jt3q-11434.thundercompute.net  https://ye96jt3q-9100.thundercompute.net
1 a5oxns3p  https://a5oxns3p-11434.thundercompute.net  https://a5oxns3p-9100.thundercompute.net
2 uw01uuc2  https://uw01uuc2-11434.thundercompute.net  https://uw01uuc2-9100.thundercompute.net
3 xkj8xszu  https://xkj8xszu-11434.thundercompute.net  https://xkj8xszu-9100.thundercompute.net
4 hz8878v2  https://hz8878v2-11434.thundercompute.net  https://hz8878v2-9100.thundercompute.net
5 ow2vbplc  https://ow2vbplc-11434.thundercompute.net  https://ow2vbplc-9100.thundercompute.net
```

Run the six-worker formal evaluation:

```bash
scripts/run_thunder_6node_eval.sh
```

Or override just the matrix for a quick smoke test:

```bash
EVAL_ID=smoke_eval_6workers EVAL_MATRIX="24:12" scripts/run_thunder_6node_eval.sh
```

For the final report, include the generated CSV/JSON summaries plus screenshots
of the live dashboard and Thunder `nvidia-smi`/metrics output.
