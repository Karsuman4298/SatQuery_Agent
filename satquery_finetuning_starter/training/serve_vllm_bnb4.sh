#!/usr/bin/env bash
set -euo pipefail
MODEL=${1:?Usage: $0 /path/to/merged-or-bnb-model}
# Requires vLLM plus the vllm-bnb-plugin. For a BF16 merged model, --quantization bitsandbytes performs in-flight 4-bit quantization.
vllm serve "$MODEL" \
  --host 0.0.0.0 \
  --port 8000 \
  --served-model-name satquery-vl-2b \
  --dtype bfloat16 \
  --quantization bitsandbytes \
  --max-model-len 4096 \
  --limit-mm-per-prompt.image 2 \
  --limit-mm-per-prompt.video 0 \
  --generation-config vllm
