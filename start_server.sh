#!/bin/bash
./build/bin/llama-server -m Meta-Llama-3-8B-Instruct-Q4_K_M.gguf --host $(hostname) --port 9999 -ngl 0