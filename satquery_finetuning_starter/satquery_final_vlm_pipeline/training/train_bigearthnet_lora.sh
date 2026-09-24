#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
QWEN="$ROOT/vendor/Qwen3-VL/qwen-vl-finetune"
cd "$QWEN"

MODEL=${MODEL:-$ROOT/models/Qwen3-VL-2B-Instruct}
DATASET=${DATASET:-satquery_ben}
OUTPUT=${OUTPUT:-$ROOT/outputs/satquery-ben-lora-v1}

# Single A30: no torchrun/DDP and no gradient checkpointing.
python qwenvl/train/train_qwen.py \
  --model_name_or_path "$MODEL" \
  --dataset_use "$DATASET" \
  --data_flatten False \
  --data_packing False \
  --tune_mm_vision False \
  --tune_mm_mlp False \
  --tune_mm_llm True \
  --bf16 \
  --lora_enable True \
  --lora_r 16 \
  --lora_alpha 32 \
  --lora_dropout 0.05 \
  --output_dir "$OUTPUT" \
  --num_train_epochs 1 \
  --per_device_train_batch_size 1 \
  --gradient_accumulation_steps 16 \
  --max_pixels 200704 \
  --min_pixels 12544 \
  --eval_strategy no \
  --save_strategy steps \
  --save_steps 250 \
  --save_total_limit 2 \
  --learning_rate 1e-6 \
  --weight_decay 0.01 \
  --warmup_ratio 0.03 \
  --max_grad_norm 1.0 \
  --lr_scheduler_type cosine \
  --logging_steps 10 \
  --model_max_length 2048 \
  --gradient_checkpointing False \
  --dataloader_num_workers 4 \
  --report_to none
