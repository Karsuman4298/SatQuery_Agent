import argparse, json, re, string
from pathlib import Path

def norm(s):
    s=s.lower().strip()
    s=s.translate(str.maketrans("","",string.punctuation))
    s=re.sub(r"\s+"," ",s)
    return s

p=argparse.ArgumentParser()
p.add_argument("--predictions", required=True,
               help="JSONL with fields prediction and reference")
a=p.parse_args()

n=em=0
for line in open(a.predictions, encoding="utf-8"):
    if not line.strip(): continue
    x=json.loads(line)
    n+=1
    em += int(norm(x["prediction"]) == norm(x["reference"]))
print({"n":n, "normalized_exact_match": em/max(n,1)})
