#config.py
"""
Configuration for Phase 3 distributed system
"""

# Ollama Configuration
OLLAMA_HOST = "http://Carol.local:9999"
OLLAMA_MODEL = "mistral"
OLLAMA_TIMEOUT = 120  # seconds
USE_OLLAMA_FALLBACK = True  # Use mock responses if Ollama unavailable

# FAISS Configuration
FAISS_VECTOR_DIM = 384  # For all-MiniLM-L6-v2
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Scheduler Configuration
WORKER_HEALTH_CHECK_INTERVAL = 2  # seconds
WORKER_TIMEOUT = 5  # seconds before marking worker as failed
TASK_REASSIGNMENT_ENABLED = True

# Load Testing
NUM_USERS =  2
REQUESTS_PER_USER = 1

# System Configuration
NUM_WORKERS = 4