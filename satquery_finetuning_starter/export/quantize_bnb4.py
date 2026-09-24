#!/usr/bin/env python3
"""Create a saved 4-bit BitsAndBytes checkpoint from the merged model.
Use recent Transformers + bitsandbytes. Always compare quality against BF16 before deployment.
"""
import argparse, torch
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--model', required=True); ap.add_argument('--output', required=True); args=ap.parse_args()
    q=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4', bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
    model=Qwen3VLForConditionalGeneration.from_pretrained(args.model, quantization_config=q, device_map='auto', dtype=torch.bfloat16)
    print('memory footprint GiB:', model.get_memory_footprint()/1024**3)
    model.save_pretrained(args.output, safe_serialization=True)
    AutoProcessor.from_pretrained(args.model).save_pretrained(args.output)
    print('4-bit model saved to', args.output)
if __name__=='__main__': main()
