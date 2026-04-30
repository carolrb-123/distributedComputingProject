#config.py
"""
Configuration for Phase 3 distributed system
"""
import socket
import platform

# Get the Mac/Windows hostname
HOSTNAME = socket.gethostname()

# Ollama Configuration
OLLAMA_HOST = f"http://{HOSTNAME}:9999"
OLLAMA_MODEL = "mistral"
OLLAMA_TIMEOUT = 120
USE_OLLAMA_FALLBACK = True

# FAISS Configuration
FAISS_VECTOR_DIM = 384
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Scheduler Configuration
WORKER_HEALTH_CHECK_INTERVAL = 2
WORKER_TIMEOUT = 5
TASK_REASSIGNMENT_ENABLED = True

# Load Testing
NUM_USERS = 1000
REQUESTS_PER_USER = 1

# System Configuration
NUM_WORKERS = 4