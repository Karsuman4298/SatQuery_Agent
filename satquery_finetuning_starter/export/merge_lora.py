#!/usr/bin/env python3
import argparse, torch
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
from peft import PeftModel

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base', default='Qwen/Qwen3-VL-2B-Instruct'); ap.add_argument('--adapter', required=True); ap.add_argument('--output', required=True); args=ap.parse_args()
    base=Qwen3VLForConditionalGeneration.from_pretrained(args.base, dtype=torch.bfloat16, device_map='cpu')
    model=PeftModel.from_pretrained(base, args.adapter)
    model=model.merge_and_unload()
    model.save_pretrained(args.output, safe_serialization=True, max_shard_size='5GB')
    AutoProcessor.from_pretrained(args.base).save_pretrained(args.output)
    print('Merged model saved to', args.output)
if __name__=='__main__': main()
