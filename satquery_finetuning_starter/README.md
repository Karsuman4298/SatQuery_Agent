# SatQuery VL fine-tuning starter

This starter intentionally uses the official Qwen3-VL fine-tuning framework for the first production-quality run.

High-level flow:
1. Create isolated Python environment and install a CUDA-matched PyTorch build.
2. Run `scripts/setup_qwen.sh` and install the official Qwen trainer dependencies.
3. Download VRSBench / BigEarthNet.txt / ChangeChat annotations.
4. Prepare one combined Qwen JSONL file. Every `<image>` token must have one image path.
5. Validate it.
6. Register it with the Qwen trainer.
7. Run LoRA training.
8. Evaluate adapter vs base.
9. Merge the best LoRA into BF16 master checkpoint.
10. Quantize/serve 4-bit only after the BF16 checkpoint passes evaluation.

Suggested first experiment:
- VRSBench caption/VQA + 20k-50k BigEarthNet.txt RGB samples + 10k ChangeChat samples.
- One epoch, LoRA rank 16, batch 1, gradient accumulation 16, ~448px max image area.

Never train on BigEarthNet `validation`, `test`, or `bench` splits. Keep them for evaluation.
