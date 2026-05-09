#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8888}"
HOST="${HOST:-0.0.0.0}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$HOME/llama.cpp}"
MODEL_DIR="${MODEL_DIR:-$HOME/models}"
MODEL_FILE="${MODEL_FILE:-tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf}"
MODEL_URL="${MODEL_URL:-https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf}"
N_GPU_LAYERS="${N_GPU_LAYERS:-99}"
CTX_SIZE="${CTX_SIZE:-2048}"
BATCH_SIZE="${BATCH_SIZE:-512}"
UBATCH_SIZE="${UBATCH_SIZE:-128}"
PARALLEL="${PARALLEL:-4}"
N_PREDICT="${N_PREDICT:-128}"
BUILD_CUDA="${BUILD_CUDA:-auto}"

echo "[Thunder worker] Checking GPU"
nvidia-smi || true

if [ "$BUILD_CUDA" = "auto" ]; then
  if command -v nvcc >/dev/null 2>&1; then
    BUILD_CUDA="on"
  elif [ -x /usr/local/cuda/bin/nvcc ]; then
    export PATH="/usr/local/cuda/bin:$PATH"
    export CUDACXX="/usr/local/cuda/bin/nvcc"
    BUILD_CUDA="on"
  else
    cat <<'EOF'
[Thunder worker] CUDA compiler nvcc was not found.

llama.cpp's CUDA backend must be compiled with nvcc. On Thunder, use a
Production-mode Base instance for full CUDA build compatibility, or install a
CUDA toolkit that provides nvcc on this VM.

Quick checks:
  which nvcc
  ls -l /usr/local/cuda/bin/nvcc
  nvidia-smi

Temporary CPU-only fallback:
  BUILD_CUDA=off ./scripts/run_thunder_llama_server.sh
EOF
    exit 1
  fi
elif [ "$BUILD_CUDA" = "on" ] && [ -x /usr/local/cuda/bin/nvcc ]; then
  export PATH="/usr/local/cuda/bin:$PATH"
  export CUDACXX="${CUDACXX:-/usr/local/cuda/bin/nvcc}"
fi

if [ ! -d "$LLAMA_CPP_DIR/.git" ]; then
  echo "[Thunder worker] Cloning llama.cpp into $LLAMA_CPP_DIR"
  git clone https://github.com/ggerganov/llama.cpp "$LLAMA_CPP_DIR"
fi

cd "$LLAMA_CPP_DIR"
if [ "$BUILD_CUDA" = "off" ]; then
  echo "[Thunder worker] Building llama.cpp CPU-only"
  cmake -B build -DGGML_CUDA=OFF -DCMAKE_BUILD_TYPE=Release
  N_GPU_LAYERS=0
else
  echo "[Thunder worker] Building llama.cpp with CUDA"
  cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
fi
cmake --build build --config Release -j "$(nproc)"

mkdir -p "$MODEL_DIR"
MODEL_PATH="$MODEL_DIR/$MODEL_FILE"
if [ ! -f "$MODEL_PATH" ]; then
  echo "[Thunder worker] Downloading model to $MODEL_PATH"
  curl -L "$MODEL_URL" -o "$MODEL_PATH"
fi

echo "[Thunder worker] Starting llama-server on $HOST:$PORT"
exec "$LLAMA_CPP_DIR/build/bin/llama-server" \
  -m "$MODEL_PATH" \
  --host "$HOST" \
  --port "$PORT" \
  -ngl "$N_GPU_LAYERS" \
  --ctx-size "$CTX_SIZE" \
  --batch-size "$BATCH_SIZE" \
  --ubatch-size "$UBATCH_SIZE" \
  --parallel "$PARALLEL" \
  -n "$N_PREDICT"
