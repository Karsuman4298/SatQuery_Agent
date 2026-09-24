import argparse, json, os
from collections import Counter

p = argparse.ArgumentParser()
p.add_argument("path")
a = p.parse_args()

good=bad=0
sources=Counter()
for i,line in enumerate(open(a.path, encoding="utf-8"),1):
    if not line.strip(): continue
    try:
        x=json.loads(line)
        images=x.get("image")
        images=[images] if isinstance(images,str) else images
        if not images or not all(os.path.exists(z) for z in images):
            raise ValueError("missing image")
        conv=x.get("conversations",[])
        human=" ".join(t.get("value","") for t in conv if t.get("from")=="human")
        if human.count("<image>") != len(images):
            raise ValueError(f"markers={human.count('<image>')} images={len(images)}")
        if not any(t.get("from")=="gpt" and t.get("value","").strip() for t in conv):
            raise ValueError("missing answer")
        sources[x.get("meta",{}).get("source","unknown")] += 1
        good+=1
    except Exception as e:
        bad+=1
        if bad<=20: print("BAD",i,repr(e))
print({"good":good,"bad":bad,"sources":dict(sources)})
