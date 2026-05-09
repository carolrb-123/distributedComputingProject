# Formal Evaluation Plan

Use this plan to generate evidence for the project report and demo.

## Test Matrix

Run the system with increasing concurrent users:

```text
50 users / 10 threads
100 users / 20 threads
250 users / 40 threads
500 users / 80 threads
1000 users / 120 threads
```

For each run, collect:

- total requests
- failed requests
- success rate
- throughput
- average latency
- p50 latency
- p99 latency
- per-worker assignment counts
- per-worker state, EWMA latency, failure rate
- admission/backpressure waits and timeouts
- GPU utilization, GPU memory usage, temperature, and power draw

## Fault Tolerance Evidence

Run one normal baseline, then stop one worker during a test:

```bash
pkill ollama
```

Expected evidence:

- one worker moves to `DEGRADED` or `UNHEALTHY`
- load balancer routes around that worker
- remaining worker continues serving requests
- after restarting with `start-ollama`, the failed worker moves through
  `RECOVERING` to `HEALTHY`

## Evidence Files

Each run creates:

```text
evaluation_results/<run_id>/latencies.csv
evaluation_results/<run_id>/metrics_summary.json
evaluation_results/<run_id>/run_evidence.json
evaluation_results/<run_id>/gpu_metrics_history.csv
evaluation_results/<run_id>/gpu_metrics_history.json
evaluation_results/<run_id>/console.log
```

Use these files to build the final report tables and charts.

## Backpressure Evidence

High-concurrency runs should not fail just because every GPU worker is busy.
The controller now waits for capacity before rejecting a request.

Recommended settings for the formal 2-worker Thunder run:

```bash
export SCHEDULER_ADMISSION_TIMEOUT=300
export SCHEDULER_ADMISSION_POLL_INTERVAL=0.05
```

Expected evidence in `run_evidence.json`:

- `load_balancer.admission.wait_count` increases under high load
- `load_balancer.admission.timeout_count` remains `0` for successful runs
- workers remain `HEALTHY` while saturated
- success rate improves because busy workers are treated as capacity pressure,
  not node failures
