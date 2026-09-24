#!/usr/bin/env python3
import argparse, torch
from PIL import Image
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--model', required=True); ap.add_argument('--image', required=True); ap.add_argument('--question', default='Describe the dominant land-cover features visible in this remote-sensing image.'); args=ap.parse_args()
    model=Qwen3VLForConditionalGeneration.from_pretrained(args.model, dtype='auto', device_map='auto')
    proc=AutoProcessor.from_pretrained(args.model)
    messages=[{'role':'user','content':[{'type':'image','image':Image.open(args.image).convert('RGB')},{'type':'text','text':args.question}]}]
    inputs=proc.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors='pt').to(model.device)
    with torch.inference_mode(): out=model.generate(**inputs, max_new_tokens=160, do_sample=False)
    trimmed=[o[len(i):] for i,o in zip(inputs.input_ids,out)]
    print(proc.batch_decode(trimmed, skip_special_tokens=True)[0])
if __name__=='__main__': main()
