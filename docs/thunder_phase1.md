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
