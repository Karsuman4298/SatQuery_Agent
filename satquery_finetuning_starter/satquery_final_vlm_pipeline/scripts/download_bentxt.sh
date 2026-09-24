#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/data/raw/bigearthnet_txt"
mkdir -p "$ROOT/data/raw/bigearthnet_v2"

# BigEarthNet.txt annotations (~9.6M image-text rows)
hf download BIFOLD-BigEarthNetv2-0/BigEarthNet.txt \
  BigEarthNet.txt.parquet \
  --repo-type dataset \
  --local-dir "$ROOT/data/raw/bigearthnet_txt"

# BigEarthNet-v2 Sentinel-2 image archive mirror.
# This is large (~59 GiB compressed) and is split into two files.
hf download torchgeo/bigearthnet \
  V2/BigEarthNet-S2.tar.gzaa \
  V2/BigEarthNet-S2.tar.gzab \
  --repo-type dataset \
  --local-dir "$ROOT/data/raw/bigearthnet_v2"

echo
echo "Downloaded. Next concatenate + extract:"
echo "  cat data/raw/bigearthnet_v2/V2/BigEarthNet-S2.tar.gzaa \\"
echo "      data/raw/bigearthnet_v2/V2/BigEarthNet-S2.tar.gzab \\"
echo "      > data/raw/bigearthnet_v2/BigEarthNet-S2.tar.gz"
echo
echo "  mkdir -p data/raw/bigearthnet_v2/extracted"
echo "  tar -xzf data/raw/bigearthnet_v2/BigEarthNet-S2.tar.gz \\"
echo "      -C data/raw/bigearthnet_v2/extracted"
