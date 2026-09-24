import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import rasterio

def tile_name(patch_id: str) -> str:
    # BigEarthNet-v2 patch id ends in _<H>_<V>.
    parts = patch_id.split("_")
    if len(parts) < 3:
        raise ValueError(patch_id)
    return "_".join(parts[:-2])

def stretch(ch):
    ch = ch.astype(np.float32)
    valid = np.isfinite(ch)
    if not valid.any():
        return np.zeros_like(ch, dtype=np.uint8)
    lo, hi = np.percentile(ch[valid], [2, 98])
    if hi <= lo:
        lo, hi = float(ch[valid].min()), float(ch[valid].max())
    if hi <= lo:
        return np.zeros_like(ch, dtype=np.uint8)
    ch = np.clip((ch - lo) / (hi - lo), 0, 1)
    return (ch * 255).astype(np.uint8)

def read_band(path):
    with rasterio.open(path) as ds:
        return ds.read(1)

p = argparse.ArgumentParser()
p.add_argument("--subset", required=True, help="subset parquet from select_bentxt_subset.py")
p.add_argument("--s2_root", required=True, help="directory containing BigEarthNet-S2 tile folders")
p.add_argument("--output_dir", required=True)
p.add_argument("--size", type=int, default=224)
p.add_argument("--overwrite", action="store_true")
a = p.parse_args()

df = pd.read_parquet(a.subset)
patch_ids = df["patch_id"].drop_duplicates().tolist()
root = Path(a.s2_root)
out = Path(a.output_dir)
out.mkdir(parents=True, exist_ok=True)

ok = miss = fail = 0
missing_examples = []

for i, patch_id in enumerate(patch_ids, 1):
    dst = out / f"{patch_id}.png"
    if dst.exists() and not a.overwrite:
        ok += 1
        continue

    tile = tile_name(patch_id)
    patch_dir = root / tile / patch_id
    if not patch_dir.exists():
        # fallback search for unusual extraction nesting
        hits = list(root.glob(f"**/{patch_id}"))
        patch_dir = hits[0] if hits else patch_dir

    paths = [patch_dir / f"{patch_id}_{b}.tif" for b in ("B04","B03","B02")]
    if not all(x.exists() for x in paths):
        miss += 1
        if len(missing_examples) < 20:
            missing_examples.append(str(patch_dir))
        continue

    try:
        rgb = np.stack([stretch(read_band(x)) for x in paths], axis=-1)
        im = Image.fromarray(rgb, "RGB")
        if a.size:
            im = im.resize((a.size, a.size), Image.Resampling.BICUBIC)
        im.save(dst, optimize=True)
        ok += 1
    except Exception as e:
        fail += 1
        if fail < 10:
            print("FAILED", patch_id, repr(e))

    if i % 1000 == 0:
        print({"done": i, "ok": ok, "missing": miss, "failed": fail})

print({"ok": ok, "missing": miss, "failed": fail, "total": len(patch_ids)})
if missing_examples:
    print("First missing patch dirs:")
    for x in missing_examples:
        print(x)
