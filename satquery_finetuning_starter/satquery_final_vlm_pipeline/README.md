# SatQuery-VL Final Training Pipeline

Target: Qwen3-VL-2B-Instruct -> SatQuery-VL-2B

Recommended curriculum:
1. VRSBench VQA/caption data (already prepared)
2. BigEarthNet.txt + BigEarthNet-v2 Sentinel-2 RGB
3. ChangeChat-105k + LEVIR-CC image pairs
4. Custom evidence-grounding / uncertainty examples
5. Final mixed LoRA training
6. Evaluation
7. Merge adapter into BF16 base
8. Quantized deployment

This code assumes your project root is:
  /hdd/aryan_das/USERS/Suman_Kar/SatQuery_Agent/satquery_finetuning_starter

Never point these scripts outside your own Suman_Kar directory.
