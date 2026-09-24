import argparse, json
from pathlib import Path
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--subset", required=True)
p.add_argument("--rgb_dir", required=True)
p.add_argument("--output", required=True)
p.add_argument("--drop_missing", action="store_true")
a = p.parse_args()

df = pd.read_parquet(a.subset)
rgb = Path(a.rgb_dir)
out = Path(a.output)
out.parent.mkdir(parents=True, exist_ok=True)

stats = {"written":0, "missing":0}
with out.open("w", encoding="utf-8") as f:
    for row in df.itertuples(index=False):
        image = (rgb / f"{row.patch_id}.png").resolve()
        if not image.exists():
            stats["missing"] += 1
            if a.drop_missing:
                continue
            raise FileNotFoundError(image)

        prompt = str(row.input).strip()
        answer = str(row.output).strip()
        rec = {
            "image": str(image),
            "conversations": [
                {"from":"human", "value":f"<image>\n{prompt}"},
                {"from":"gpt", "value":answer},
            ],
            "meta": {
                "source":"BigEarthNet.txt",
                "patch_id":str(row.patch_id),
                "type":str(row.type),
                "category":str(row.category),
            },
        }
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        stats["written"] += 1

print(stats)
