import argparse, json, random
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--source", action="append", required=True,
               help="PATH:N, e.g. vrs.jsonl:40000")
p.add_argument("--output", required=True)
p.add_argument("--seed", type=int, default=42)
a = p.parse_args()
random.seed(a.seed)

mixed = []
report = {}
for spec in a.source:
    path, n = spec.rsplit(":", 1)
    n = int(n)
    rows = [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]
    random.shuffle(rows)
    take = rows[:min(n, len(rows))]
    mixed.extend(take)
    report[path] = len(take)

random.shuffle(mixed)
out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
with out.open("w", encoding="utf-8") as f:
    for x in mixed:
        f.write(json.dumps(x, ensure_ascii=False)+"\n")

print({"total":len(mixed), "sources":report, "output":str(out)})
