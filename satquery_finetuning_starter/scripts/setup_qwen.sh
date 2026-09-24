#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/vendor"
if [ ! -d "$ROOT/vendor/Qwen3-VL/.git" ]; then
  git clone https://github.com/QwenLM/Qwen3-VL.git "$ROOT/vendor/Qwen3-VL"
fi
cd "$ROOT/vendor/Qwen3-VL"
echo "Qwen commit: $(git rev-parse HEAD)"
echo "Official trainer: $ROOT/vendor/Qwen3-VL/qwen-vl-finetune"
