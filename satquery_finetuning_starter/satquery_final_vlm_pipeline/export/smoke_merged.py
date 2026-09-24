import argparse, torch
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor

p=argparse.ArgumentParser()
p.add_argument("--model", required=True)
p.add_argument("--image", required=True)
p.add_argument("--prompt", default="Describe the major land-cover features visible in this satellite image.")
a=p.parse_args()

proc=AutoProcessor.from_pretrained(a.model)
model=Qwen3VLForConditionalGeneration.from_pretrained(
    a.model,dtype=torch.bfloat16,attn_implementation="sdpa").to("cuda").eval()

messages=[{"role":"user","content":[
    {"type":"image","image":a.image},
    {"type":"text","text":a.prompt},
]}]
inp=proc.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                             return_dict=True, return_tensors="pt").to("cuda")
with torch.inference_mode():
    out=model.generate(**inp,max_new_tokens=160,do_sample=False)
gen=out[:,inp["input_ids"].shape[1]:]
print(proc.batch_decode(gen,skip_special_tokens=True)[0])
