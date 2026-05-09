# config.py
"""
Runtime configuration for the distributed inference system.

Environment variables are intentionally first-class here because real GPU
workers will run on cloud instances with dynamic public/tunneled URLs.
"""
import os
import socket


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


def _get_csv(name: str, default):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return list(default)
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


HOSTNAME = socket.gethostname()

# llama.cpp-compatible OpenAI API endpoints. In Thunder, set this to the
# forwarded HTTPS URLs for each GPU VM, for example:
# LLM_SERVER_URLS=https://vm-a-8888.thundercompute.net,https://vm-b-8888.thundercompute.net
DEFAULT_LLM_SERVER_URLS = [
    "http://localhost:8888",
    "http://localhost:8889",
    "http://localhost:8890",
    "http://localhost:8891",
]
LLM_SERVER_URLS = _get_csv("LLM_SERVER_URLS", DEFAULT_LLM_SERVER_URLS)
LLM_SERVER_URL = LLM_SERVER_URLS[0]
LLM_MODEL = os.getenv("LLM_MODEL", "local-model")
LLM_TIMEOUT = _get_float("LLM_TIMEOUT", 180.0)
LLM_HEALTH_TIMEOUT = _get_float("LLM_HEALTH_TIMEOUT", 5.0)
LLM_HEALTH_PATH = os.getenv("LLM_HEALTH_PATH", "/health")
LLM_MAX_TOKENS = _get_int("LLM_MAX_TOKENS", 64)
LLM_TEMPERATURE = _get_float("LLM_TEMPERATURE", 0.7)

# FAISS Configuration
FAISS_VECTOR_DIM = 384
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)

# Scheduler Configuration
WORKER_HEALTH_CHECK_INTERVAL = _get_float("WORKER_HEALTH_CHECK_INTERVAL", 2.0)
WORKER_TIMEOUT = _get_float("WORKER_TIMEOUT", 5.0)
SCHEDULER_REQUEST_TIMEOUT = _get_float("SCHEDULER_REQUEST_TIMEOUT", 30.0)
SCHEDULER_MAX_ATTEMPTS = _get_int("SCHEDULER_MAX_ATTEMPTS", 2)
TASK_REASSIGNMENT_ENABLED = _get_bool("TASK_REASSIGNMENT_ENABLED", True)

# Load Testing
NUM_USERS = _get_int("NUM_USERS", 1000)
REQUESTS_PER_USER = _get_int("REQUESTS_PER_USER", 1)
LOAD_TEST_THREADS = _get_int("LOAD_TEST_THREADS", 200)

# System Configuration
NUM_WORKERS = _get_int("NUM_WORKERS", len(LLM_SERVER_URLS))
WORKER_THREADS = _get_int("WORKER_THREADS", 8)
WORKER_QUEUE_SIZE = _get_int("WORKER_QUEUE_SIZE", 10)
WORKER_MAX_IN_FLIGHT = _get_int("WORKER_MAX_IN_FLIGHT", WORKER_THREADS + WORKER_QUEUE_SIZE)
WORKER_MAX_FAILURES = _get_int("WORKER_MAX_FAILURES", 5)
WORKER_FAILURE_COOLDOWN = _get_float("WORKER_FAILURE_COOLDOWN", 20.0)
WORKER_RECOVERY_SUCCESSES = _get_int("WORKER_RECOVERY_SUCCESSES", 2)
FAULT_TOLERANCE_TEST_REQUESTS = _get_int("FAULT_TOLERANCE_TEST_REQUESTS", 8)
RUN_FAULT_TOLERANCE_TESTS = _get_bool("RUN_FAULT_TOLERANCE_TESTS", False)

# Load Balancer Configuration
LOAD_BALANCER_POLICY = os.getenv("LOAD_BALANCER_POLICY", "adaptive").strip().lower()
LB_EWMA_ALPHA = _get_float("LB_EWMA_ALPHA", 0.35)
LB_UTILIZATION_WEIGHT = _get_float("LB_UTILIZATION_WEIGHT", 3.0)
LB_QUEUE_WEIGHT = _get_float("LB_QUEUE_WEIGHT", 1.5)
LB_LATENCY_WEIGHT = _get_float("LB_LATENCY_WEIGHT", 2.5)
LB_IN_FLIGHT_AGE_WEIGHT = _get_float("LB_IN_FLIGHT_AGE_WEIGHT", 0.5)
LB_FAILURE_WEIGHT = _get_float("LB_FAILURE_WEIGHT", 4.0)
LB_STATE_DEGRADED_PENALTY = _get_float("LB_STATE_DEGRADED_PENALTY", 5.0)
LB_STATE_RECOVERING_PENALTY = _get_float("LB_STATE_RECOVERING_PENALTY", 2.0)

# Monitoring and Evidence
GPU_METRICS_URLS = _get_csv("GPU_METRICS_URLS", [])
GPU_METRICS_PATH = os.getenv("GPU_METRICS_PATH", "/metrics")
GPU_METRICS_INTERVAL = _get_float("GPU_METRICS_INTERVAL", 2.0)
GPU_METRICS_TIMEOUT = _get_float("GPU_METRICS_TIMEOUT", 2.0)
ENABLE_MONITORING_DASHBOARD = _get_bool("ENABLE_MONITORING_DASHBOARD", False)
MONITORING_HOST = os.getenv("MONITORING_HOST", "127.0.0.1")
MONITORING_PORT = _get_int("MONITORING_PORT", 8080)
EVIDENCE_DIR = os.getenv("EVIDENCE_DIR", "evaluation_results")
RUN_ID = os.getenv("RUN_ID", "").strip()

MAX_QUEUE_SIZE = WORKER_QUEUE_SIZE
