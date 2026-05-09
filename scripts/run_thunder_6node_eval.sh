#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python3.12}"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

export LLM_SERVER_URLS="${LLM_SERVER_URLS:-https://ye96jt3q-11434.thundercompute.net,https://a5oxns3p-11434.thundercompute.net,https://uw01uuc2-11434.thundercompute.net,https://xkj8xszu-11434.thundercompute.net,https://hz8878v2-11434.thundercompute.net,https://ow2vbplc-11434.thundercompute.net}"
export GPU_METRICS_URLS="${GPU_METRICS_URLS:-https://ye96jt3q-9100.thundercompute.net,https://a5oxns3p-9100.thundercompute.net,https://uw01uuc2-9100.thundercompute.net,https://xkj8xszu-9100.thundercompute.net,https://hz8878v2-9100.thundercompute.net,https://ow2vbplc-9100.thundercompute.net}"
export LLM_MODEL="${LLM_MODEL:-tinyllama}"
export LLM_HEALTH_PATH="${LLM_HEALTH_PATH:-/api/version}"
export LLM_MAX_TOKENS="${LLM_MAX_TOKENS:-16}"
export NUM_WORKERS="${NUM_WORKERS:-6}"
export SCHEDULER_REQUEST_TIMEOUT="${SCHEDULER_REQUEST_TIMEOUT:-240}"
export SCHEDULER_ADMISSION_TIMEOUT="${SCHEDULER_ADMISSION_TIMEOUT:-300}"
export SCHEDULER_ADMISSION_POLL_INTERVAL="${SCHEDULER_ADMISSION_POLL_INTERVAL:-0.05}"
export WORKER_THREADS="${WORKER_THREADS:-2}"
export WORKER_QUEUE_SIZE="${WORKER_QUEUE_SIZE:-8}"
export WORKER_MAX_IN_FLIGHT="${WORKER_MAX_IN_FLIGHT:-10}"
export LOAD_BALANCER_POLICY="${LOAD_BALANCER_POLICY:-adaptive}"
export EVAL_MATRIX="${EVAL_MATRIX:-50:10,100:20,250:40,500:80,1000:120}"
export EVAL_ID="${EVAL_ID:-final_eval_6workers}"

"$PYTHON_BIN" scripts/run_formal_evaluation.py
