SatQuery BigEarthNet Base-vs-LoRA Evaluation

Recommended evaluation:
  500 binary + 500 MCQ + 200 caption = 1200 unique validation patches.

Faster smoke evaluation:
  --binary 100 --mcq 100 --caption 50

Workflow:
1. make_ben_eval_subset.py
2. existing make_ben_rgb_manifest.py
3. selective B02/B03/B04 extraction from BigEarthNet-S2.tar.gz
4. existing render_ben_rgb.py
5. eval_base_vs_lora_ben.py
