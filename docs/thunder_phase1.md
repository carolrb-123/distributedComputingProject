# Phase 1: Thunder GPU Worker Deployment

This project now treats each configured LLM endpoint as a logical GPU worker.
The scheduler and load balancer can run locally while inference runs on one or
more Thunder Compute GPU VMs.

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
