# Screenshots and Evidence Checklist

Use these screenshots in the IEEE report and/or presentation. The saved terminal
outputs are already in `evaluation_results/`, so screenshots should focus on
the clearest visual proof.

## Must-Have Screenshots

1. **Project specification / marking criteria**
   - File: `/Users/boulosaziz/Documents/Ain_Shams/(10)Spring_2026/Distributed/Project/CSE 354 Project S26.pdf`
   - Capture the first page showing required report contents, learning outcomes,
     and 89%+ marking criteria.

2. **Thunder six-node fleet**
   - Command:
     ```bash
     tnr status
     ```
   - Must show six `RUNNING` A6000 Ollama instances:
     `ye96jt3q`, `a5oxns3p`, `uw01uuc2`, `xkj8xszu`, `hz8878v2`, `ow2vbplc`.

3. **Forwarded ports**
   - Command:
     ```bash
     tnr ports list
     ```
   - Must show ports `11434` and `9100` on all six nodes.

4. **Live Ollama API health**
   - Command:
     ```bash
     for id in ye96jt3q a5oxns3p uw01uuc2 xkj8xszu hz8878v2 ow2vbplc; do
       echo "$id:"
       curl -s "https://${id}-11434.thundercompute.net/api/version"
       echo
     done
     ```
   - Must show `{"version":"0.20.7"}` for each worker.

5. **Live GPU metrics**
   - Command:
     ```bash
     curl -s https://uw01uuc2-9100.thundercompute.net/metrics
     ```
   - Must show `NVIDIA RTX A6000`, memory, temperature, power, and utilization.

6. **Formal evaluation summary**
   - File:
     ```text
     evaluation_results/final_eval_6workers_summary.csv
     ```
   - Show all five rows as `PASS`.

7. **1000-user metrics summary**
   - File:
     ```text
     evaluation_results/final_eval_6workers_users1000_threads120/metrics_summary.json
     ```
   - Highlight:
     - `total_requests: 1000`
     - `failed_requests: 0`
     - `success_rate: 1.0`

8. **1000-user run evidence**
   - File:
     ```text
     evaluation_results/final_eval_6workers_users1000_threads120/run_evidence.json
     ```
   - Highlight:
     - `load_balancer.assignment_counts`
     - `load_balancer.admission.wait_count: 126`
     - `load_balancer.admission.timeout_count: 0`
     - worker states `HEALTHY`

9. **1000-user console completion**
   - File:
     ```text
     evaluation_results/final_eval_6workers_users1000_threads120/console.log
     ```
   - Capture the final metrics block and `PHASE 3 COMPLETE`.

## Code Screenshots

Use these only if the report/presentation needs implementation proof.

1. **Adaptive load balancing and backpressure**
   - File: `lb/load_balancer.py`
   - Capture `dispatch()` and the admission statistics in `get_status()`.

2. **Scheduler retry and timeout handling**
   - File: `master/scheduler.py`
   - Capture `handle_request()`, especially the event/callback handling,
     timeout logic, and admission timeout handling.

3. **Worker capacity and circuit breaker**
   - File: `workers/gpu_worker.py`
   - Capture `can_accept()`, `process()`, `_record_failure()`, and
     `health_check()`.

4. **GPU metrics agent**
   - File: `scripts/gpu_metrics_agent.py`
   - Capture the `nvidia-smi` query and `/metrics` response handler.

5. **Formal evaluation runner**
   - File: `scripts/run_formal_evaluation.py`
   - Capture the evaluation matrix and evidence folder generation.

6. **Six-node evaluation configuration**
   - File: `scripts/run_thunder_6node_eval.sh`
   - Capture the six `LLM_SERVER_URLS`, six `GPU_METRICS_URLS`, and the
     `EVAL_MATRIX`.

## Generated Graphs to Insert

The graph files are already generated in `report/figures/`.

1. `architecture.svg`
   - Use as the system architecture figure.

2. `success_rate_scaling.svg`
   - Best evidence that the six-worker system fixed the two-worker bottleneck.

3. `throughput_scaling.svg`
   - Shows throughput improvement with six workers.

4. `latency_summary_6workers.svg`
   - Shows p50, average, and p99 latency trends.

5. `latency_cdf_1000.svg`
   - Shows the latency distribution of the 1000-request run.

6. `worker_assignments_1000.svg`
   - Shows adaptive load-balancer behavior.

7. `admission_backpressure.svg`
   - Shows that backpressure activated under high load with zero timeouts.

8. `gpu_summary_6workers.svg`
   - Shows GPU telemetry maxima across evaluation runs.

## Report Assembly Recommendation

For a high-score submission:

1. Use `report/ieee_report.md` as the main content.
2. Insert the generated SVG graphs as numbered figures.
3. Add the required screenshots from this checklist.
4. Keep the raw evidence files in an appendix or submit them with the repo.
5. In the presentation/demo, focus on the 1000-user evidence and the difference
   between the two-worker baseline and six-worker final system.
