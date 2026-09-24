import argparse, json, random
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--image_jsonl", required=True,
               help="Any Qwen JSONL; its image paths are reused for uncertainty/tool examples.")
p.add_argument("--output", required=True)
p.add_argument("--n", type=int, default=3000)
p.add_argument("--seed", type=int, default=42)
a = p.parse_args()

random.seed(a.seed)
rows = [json.loads(x) for x in open(a.image_jsonl, encoding="utf-8") if x.strip()]
random.shuffle(rows)

uncertainty = [
("What is the exact latitude and longitude of this scene?",
 "Exact coordinates cannot be determined reliably from visual content alone. Georeferencing metadata is required."),
("What exact date was this satellite image acquired?",
 "The acquisition date cannot be determined reliably from the pixels alone. Image metadata is required."),
("Calculate the exact area of the largest water body in square kilometres.",
 "Exact area requires geospatial scale information such as pixel resolution, CRS and geotransform metadata; it should be computed by a GIS tool rather than inferred from appearance alone."),
("What is the exact ground distance between the two farthest buildings?",
 "Exact ground distance cannot be obtained reliably from the image alone. A GIS calculation using georeferencing and spatial resolution is required."),
]

out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", encoding="utf-8") as f:
    for i in range(a.n):
        src = rows[i % len(rows)]
        image = src["image"]
        q, ans = random.choice(uncertainty)
        rec = {
            "image": image,
            "conversations":[
                {"from":"human","value":f"<image>\n{q}"},
                {"from":"gpt","value":ans}
            ],
            "meta":{"source":"satquery_uncertainty"}
        }
        f.write(json.dumps(rec, ensure_ascii=False)+"\n")
print({"written":a.n, "output":str(out)})
