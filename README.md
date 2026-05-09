# distributedComputingProject# distributedComputingProject

**Distributed LLM System (RAG + Load Balancing + Multi-Worker)**

A distributed LLM inference system featuring:
- Retrieval-Augmented Generation (RAG via FAISS)
- Load balancing across local or remote GPU worker endpoints
- Multiple concurrent workers backed by llama.cpp-compatible HTTP servers
- Fault tolerance & health monitoring
- Multi-server inference using llama.cpp with TinyLlama or another GGUF model

## System Architecture
    Client
      ↓
    Scheduler
      ↓
    Load Balancer
      ↓
    GPU Worker Adapters
      ↓
    Remote llama.cpp Servers (local or Thunder GPU VMs)
      ↓
    RAG (FAISS)
## Features

- ✅ Parallel request handling via threaded workers
- ✅ Multi-server LLM inference across configurable HTTP endpoints
- ✅ Worker health monitoring via each endpoint's `/health`
- ✅ Fault tolerance with task reassignment
- ✅ Admission backpressure when all GPU workers are saturated
- ✅ Metrics collection (latency, throughput, success rate)
- ✅ Modular architecture (Scheduler, Load Balancer, Workers, LLM, RAG)
- ✅ Load-testable with configurable concurrency
- ✅ Thunder Compute Phase 1 deployment guide in `docs/thunder_phase1.md`

---

## SETUP GUIDE

### 1. Clone the Repository

```bash
git clone https://github.com/carolrb-123/distributedComputingProject.git
cd distributedComputingProject
```

### 2. Create Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install llama.cpp

**macOS:**
```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make
```

**Windows (using CMake):**
```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
mkdir build
cd build
cmake ..
cmake --build . --config Release
```

### 5. Download TinyLlama Model

Download: **tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf**

**Direct download:**
```bash
cd llama.cpp
curl -L -O https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
```

Or download manually from [HuggingFace](https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF) and place inside `llama.cpp/`

### 6. Run llama.cpp Servers

⚠️ **IMPORTANT:** Run **4 servers** for optimal performance and fault tolerance.

Navigate to llama.cpp directory:
```bash
cd llama.cpp
```

**Open 4 separate terminals** and run these commands:

**Terminal 1 (Port 8888):**
```bash
./build/bin/llama-server \
  -m tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
  --host ::1 \
  --port 8888 \
  -ngl 99 \
  --ctx-size 256 \
  -n 32 \
  --threads 8 \
  --batch-size 512 \
  --ubatch-size 128 \
  --parallel 8
```

**Terminal 2 (Port 8889):**
```bash
./build/bin/llama-server \
  -m tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
  --host ::1 \
  --port 8889 \
  -ngl 99 \
  --ctx-size 256 \
  -n 32 \
  --threads 8 \
  --batch-size 512 \
  --ubatch-size 128 \
  --parallel 8
```

**Terminal 3 (Port 8890):**
```bash
./build/bin/llama-server \
  -m tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
  --host ::1 \
  --port 8890 \
  -ngl 99 \
  --ctx-size 256 \
  -n 32 \
  --threads 8 \
  --batch-size 512 \
  --ubatch-size 128 \
  --parallel 8
```

**Terminal 4 (Port 8891):**
```bash
./build/bin/llama-server \
  -m tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \
  --host ::1 \
  --port 8891 \
  -ngl 99 \
  --ctx-size 256 \
  -n 32 \
  --threads 8 \
  --batch-size 512 \
  --ubatch-size 128 \
  --parallel 8
```

**Server Configuration Explained:**
- `-m`: Model file (TinyLlama 1.1B for fast CPU inference)
- `--host ::1`: IPv6 localhost
- `--port`: Unique port for each server (8888-8891)
- `-ngl 0`: CPU-only (no GPU offloading)
- `--ctx-size 128`: Small context window for speed
- `-n 10`: Generate only 10 tokens per response (faster)
- `--threads 4`: Use 4 CPU threads per server

### 7. Test Each Server

In a new terminal, test that all servers are running:

```bash
curl http://localhost:8888/health
curl http://localhost:8889/health
curl http://localhost:8890/health
curl http://localhost:8891/health
```

You should see `{"status":"ok"}` from each.

**Optional: Test inference:**
```bash
curl http://localhost:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10
  }'
```

### 8. Configure Project

The project uses environment variables for worker endpoints. For local testing:

```bash
export LLM_SERVER_URLS="http://localhost:8888,http://localhost:8889,http://localhost:8890,http://localhost:8891"
export NUM_WORKERS=4
```

For Thunder Compute GPU VMs, see `docs/thunder_phase1.md`.

### 9. Run the Project

In your project directory (with virtual environment activated):

```bash
python main.py
```

**Expected Output:**
- System will dispatch requests based on `NUM_USERS`
- Load balancer distributes across configured workers
- Each logical worker maps to one configured LLM server URL
- Real-time logs show request processing, worker health, and fault tolerance
- Final metrics report saved to `metrics.csv` and `metrics_summary.json`

---

## Configuration

Edit `config.py` to adjust:

```python
NUM_WORKERS = 4              # Number of worker nodes
NUM_USERS = 1000             # Concurrent requests to simulate
LLM_SERVER_URLS = [...]       # Local or Thunder worker URLs
LLM_TIMEOUT = 60             # Request timeout (seconds)
WORKER_HEALTH_CHECK_INTERVAL = 2  # Health check frequency
```

---

## Performance Optimization Tips

**For better success rate:**
1. Reduce worker concurrency in `workers/gpu_worker.py`:
```python
   self.executor = ThreadPoolExecutor(max_workers=1)  # 1 request per worker
   self.semaphore = threading.Semaphore(1)
```

2. Increase timeout in `config.py`:
```python
   LLM_TIMEOUT = 120
```

3. Reduce test load for initial testing:
```python
   NUM_USERS = 100
```

**Why TinyLlama?**
- TinyLlama (1.1B parameters) runs efficiently on CPU
- 10-20x faster than Llama-3 8B on CPU-only systems
- Sufficient for demonstrating distributed system architecture
- Real AI inference (not simulation)

---

## Metrics Output

After running, check:
- `metrics.csv` - Per-request latency data
- `metrics_summary.json` - Overall performance stats
- Console output - Real-time system behavior

**Sample Metrics:**
- Total Requests: 1000
- Success Rate: 20-40% (CPU-limited)
- Throughput: ~1-2 req/sec
- Avg Latency: 15-30s
- Worker health recovery events

---

## Troubleshooting

**"No healthy workers" errors:**
- Ensure all 4 llama.cpp servers are running
- Check server health endpoints
- Increase `LLM_TIMEOUT` in config.py
- If errors appear only at high concurrency, increase
  `SCHEDULER_ADMISSION_TIMEOUT` so requests wait for worker capacity instead
  of timing out at admission.

**500 Server Errors:**
- Too much concurrent load on CPU
- Reduce `max_workers` in gpu_worker.py to 1
- Ensure each server is running on correct port

**Slow performance:**
- Expected on CPU-only systems
- TinyLlama + `-n 10` is already optimized
- Consider reducing `NUM_USERS` for testing

---


  
