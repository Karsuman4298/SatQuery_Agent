import argparse, re
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--parquet", required=True)
p.add_argument("--output", required=True)
p.add_argument("--split", default="train")
p.add_argument("--max_images", type=int, default=20000)
p.add_argument("--per_image", type=int, default=2)
p.add_argument("--seed", type=int, default=42)
p.add_argument("--allow_types", default="binary,mcq,captioning")
p.add_argument("--exclude_category_regex",
               default=r"(bounding|location|country|season|climate|area)")
a = p.parse_args()

df = pd.read_parquet(a.parquet)
need = {"patch_id","input","output","type","category","split"}
missing = need - set(df.columns)
if missing:
    raise SystemExit(f"Missing columns: {sorted(missing)}")

allowed = {x.strip() for x in a.allow_types.split(",") if x.strip()}
x = df[df["split"].astype(str).str.lower().eq(a.split.lower())].copy()
x = x[x["type"].astype(str).str.lower().isin({z.lower() for z in allowed})]

bad = re.compile(a.exclude_category_regex, re.I)
x = x[~x["category"].astype(str).map(lambda s: bool(bad.search(s)))]

# Remove empty targets.
x = x[x["input"].notna() & x["output"].notna()]
x = x[(x["input"].astype(str).str.len() > 2) & (x["output"].astype(str).str.len() > 0)]

# Deterministic unique-image sampling.
ids = (
    x[["patch_id"]]
    .drop_duplicates()
    .sample(frac=1.0, random_state=a.seed)
    .head(a.max_images)["patch_id"]
)
x = x[x["patch_id"].isin(set(ids))]

# At most N instructions per image.
x = (
    x.sample(frac=1.0, random_state=a.seed)
     .groupby("patch_id", group_keys=False)
     .head(a.per_image)
)

x.to_parquet(a.output, index=False)
print({
    "rows": len(x),
    "unique_images": x["patch_id"].nunique(),
    "types": x["type"].value_counts().to_dict(),
    "categories": x["category"].value_counts().to_dict(),
    "output": a.output,
})
