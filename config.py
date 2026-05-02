#config.py
"""
Configuration for Phase 3 distributed system
"""
import socket
import platform

# Get the Mac/Windows hostname
HOSTNAME = socket.gethostname()

# Ollama Configuration
# config.py

LLM_SERVER_URL = "http://localhost:9999"
#OLLAMA_HOST = LLM_SERVER_URL

LLM_TIMEOUT = 30
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

MAX_QUEUE_SIZE = 5