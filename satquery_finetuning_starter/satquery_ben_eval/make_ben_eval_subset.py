import argparse
from pathlib import Path
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--parquet", required=True)
p.add_argument("--train_subset", required=True)
p.add_argument("--output", required=True)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--binary", type=int, default=500)
p.add_argument("--mcq", type=int, default=500)
p.add_argument("--caption", type=int, default=200)
args = p.parse_args()

cols = ["patch_id","input","output","type","category","split"]
df = pd.read_parquet(args.parquet, columns=cols)
train = pd.read_parquet(args.train_subset, columns=["patch_id"])
train_ids = set(train["patch_id"].astype(str).unique())

val = df[df["split"].astype(str).str.lower().eq("validation")].copy()
val["patch_id"] = val["patch_id"].astype(str)
val = val[~val["patch_id"].isin(train_ids)]
val = val[val["input"].notna() & val["output"].notna()]

allowed_categories = {"presence","adjacency","count","relative pos"}
used = set()
parts = []

def take(pool, n, seed):
    pool = pool.sample(frac=1.0, random_state=seed)
    picked = []
    for idx, row in pool.iterrows():
        pid = row["patch_id"]
        if pid in used:
            continue
        used.add(pid)
        picked.append(idx)
        if len(picked) >= n:
            break
    return pool.loc[picked]

binary_pool = val[
    val["type"].astype(str).str.lower().eq("binary")
    & val["category"].astype(str).str.lower().isin(allowed_categories)
]
parts.append(take(binary_pool, args.binary, args.seed))

mcq_pool = val[
    val["type"].astype(str).str.lower().eq("mcq")
    & val["category"].astype(str).str.lower().isin(allowed_categories)
]
parts.append(take(mcq_pool, args.mcq, args.seed + 1))

caption_pool = val[val["type"].astype(str).str.lower().eq("captioning")]
parts.append(take(caption_pool, args.caption, args.seed + 2))

out = pd.concat(parts, ignore_index=True)
out = out.sample(frac=1.0, random_state=args.seed).reset_index(drop=True)

Path(args.output).parent.mkdir(parents=True, exist_ok=True)
out.to_parquet(args.output, index=False)

print({
    "rows": len(out),
    "unique_patches": out["patch_id"].nunique(),
    "types": out["type"].value_counts().to_dict(),
    "categories": out["category"].fillna("captioning").value_counts().to_dict(),
    "train_overlap": len(set(out["patch_id"]) & train_ids),
    "output": args.output
})
