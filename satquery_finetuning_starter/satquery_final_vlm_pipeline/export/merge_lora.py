import argparse, torch
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
from peft import PeftModel

p=argparse.ArgumentParser()
p.add_argument("--base", required=True)
p.add_argument("--adapter", required=True)
p.add_argument("--output", required=True)
a=p.parse_args()

base = Qwen3VLForConditionalGeneration.from_pretrained(
    a.base, dtype=torch.bfloat16, attn_implementation="sdpa",
)
model = PeftModel.from_pretrained(base, a.adapter)
model = model.merge_and_unload()
model.save_pretrained(a.output, safe_serialization=True, max_shard_size="5GB")
processor = AutoProcessor.from_pretrained(a.base)
processor.save_pretrained(a.output)
print("Saved merged BF16 model:", a.output)
