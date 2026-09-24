import argparse, json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--annotations", required=True)
p.add_argument("--images_root", required=True,
               help="LEVIR-CC root containing train/A, train/B, val/A, ...")
p.add_argument("--output", required=True)
p.add_argument("--max_rows", type=int, default=20000)
p.add_argument("--seed", type=int, default=42)
a = p.parse_args()

import random
random.seed(a.seed)

data = json.load(open(a.annotations, encoding="utf-8"))
random.shuffle(data)
root = Path(a.images_root)
out = Path(a.output)
out.parent.mkdir(parents=True, exist_ok=True)

written = missing = bad = 0
with out.open("w", encoding="utf-8") as f:
    for row in data:
        if written >= a.max_rows:
            break
        imgs = row.get("image")
        conv = row.get("conversations")
        if not isinstance(imgs, list) or len(imgs) != 2 or not conv:
            bad += 1
            continue

        abs_imgs = [(root / x).resolve() for x in imgs]
        if not all(x.exists() for x in abs_imgs):
            missing += 1
            continue

        # Verify number of image markers in first human turn.
        human = " ".join(x.get("value","") for x in conv if x.get("from") == "human")
        if human.count("<image>") < 2:
            bad += 1
            continue

        rec = {
            "image": [str(x) for x in abs_imgs],
            "conversations": conv,
            "meta": {"source":"ChangeChat-105k", "changeflag":row.get("changeflag")}
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        written += 1

print({"written":written, "missing_images":missing, "bad":bad})
