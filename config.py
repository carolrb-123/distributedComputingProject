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
LLM_TIMEOUT = _get_float("LLM_TIMEOUT", 180.0)
LLM_HEALTH_TIMEOUT = _get_float("LLM_HEALTH_TIMEOUT", 5.0)
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
TASK_REASSIGNMENT_ENABLED = _get_bool("TASK_REASSIGNMENT_ENABLED", True)

# Load Testing
NUM_USERS = _get_int("NUM_USERS", 1000)
REQUESTS_PER_USER = _get_int("REQUESTS_PER_USER", 1)
LOAD_TEST_THREADS = _get_int("LOAD_TEST_THREADS", 200)

# System Configuration
NUM_WORKERS = _get_int("NUM_WORKERS", len(LLM_SERVER_URLS))
WORKER_THREADS = _get_int("WORKER_THREADS", 8)
WORKER_QUEUE_SIZE = _get_int("WORKER_QUEUE_SIZE", 10)
WORKER_MAX_FAILURES = _get_int("WORKER_MAX_FAILURES", 5)
RUN_FAULT_TOLERANCE_TESTS = _get_bool("RUN_FAULT_TOLERANCE_TESTS", False)

MAX_QUEUE_SIZE = WORKER_QUEUE_SIZE
