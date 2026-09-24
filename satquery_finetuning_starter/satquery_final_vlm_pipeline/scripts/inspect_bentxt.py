import argparse
import pandas as pd

p = argparse.ArgumentParser()
p.add_argument("--parquet", required=True)
p.add_argument("--n", type=int, default=5)
a = p.parse_args()

df = pd.read_parquet(a.parquet)
print("rows:", len(df))
print("columns:", list(df.columns))
for col in ["split", "type", "category", "country", "season", "climate_zone"]:
    if col in df.columns:
        print(f"\n{col}:")
        print(df[col].value_counts(dropna=False).head(50).to_string())

print("\nSamples:")
cols = [c for c in ["patch_id","input","output","type","category","split"] if c in df.columns]
print(df[cols].head(a.n).to_string(index=False))
