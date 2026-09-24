#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/data/raw/bigearthnet_txt" "$ROOT/data/raw/vrsbench" "$ROOT/data/raw/changechat"

# BigEarthNet.txt metadata + official loader. Imagery is downloaded separately from BigEarthNet v2.0.
hf download BIFOLD-BigEarthNetv2-0/BigEarthNet.txt \
  BigEarthNet.txt.parquet ben_txt_datamodule.py \
  --repo-type dataset --local-dir "$ROOT/data/raw/bigearthnet_txt"

# VRSBench annotations + images (large: ~12.5 GB repository total).
hf download xiang709/VRSBench \
  VRSBench_train.json Images_train.zip \
  VRSBench_EVAL_vqa.json VRSBench_EVAL_Cap.json \
  --repo-type dataset --local-dir "$ROOT/data/raw/vrsbench"

# ChangeChat annotations only. LEVIR-CC imagery must be obtained from the upstream dataset.
hf download hlwu/changechat-105k \
  changechat_105k_train.json changechat_105k_test_binary.json \
  changechat_105k_test_open.json \
  --repo-type dataset --local-dir "$ROOT/data/raw/changechat"

echo "Annotations downloaded."
