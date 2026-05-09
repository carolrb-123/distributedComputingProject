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

echo "[Thunder worker] Checking GPU"
nvidia-smi || true

if [ ! -d "$LLAMA_CPP_DIR/.git" ]; then
  echo "[Thunder worker] Cloning llama.cpp into $LLAMA_CPP_DIR"
  git clone https://github.com/ggerganov/llama.cpp "$LLAMA_CPP_DIR"
fi

cd "$LLAMA_CPP_DIR"
echo "[Thunder worker] Building llama.cpp with CUDA"
cmake -B build -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release
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
