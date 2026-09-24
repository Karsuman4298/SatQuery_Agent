#!/usr/bin/env python3
"""Export a subset of BigEarthNet.txt + BigEarthNet-v2 LMDB into Qwen JSONL.

Prerequisite: follow BigEarthNet.txt instructions and convert S1/S2 data with rico-hdl:
  rico-hdl bigearthnet --bigearthnet-s1-dir ... --bigearthnet-s2-dir ... --target-dir Encoded-BigEarthNet
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image


def robust_rgb(chw):
    arr = np.asarray(chw, dtype=np.float32)
    out = []
    for c in arr:
        lo, hi = np.percentile(c, [2, 98])
        if hi <= lo: hi = lo + 1.0
        x = np.clip((c - lo) / (hi - lo), 0, 1)
        out.append((x * 255).astype(np.uint8))
    return np.stack(out, axis=-1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ben-code-dir', required=True, help='Folder containing ben_txt_datamodule.py')
    ap.add_argument('--lmdb', required=True)
    ap.add_argument('--metadata', required=True)
    ap.add_argument('--split', default='train', choices=['train','validation','test','bench'])
    ap.add_argument('--max-samples', type=int, default=50000)
    ap.add_argument('--size', type=int, default=448)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--image-dir', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    sys.path.insert(0, str(Path(args.ben_code_dir).resolve()))
    from ben_txt_datamodule import BENTxTDataset

    ds = BENTxTDataset(
        lmdb_file=args.lmdb,
        metadata_file=args.metadata,
        bands=('B04','B03','B02'),
        img_size=args.size,
        upsample_mode='bilinear',
        types=['binary','mcq','captioning'],
        splits=[args.split],
        transform=None,
    )
    n = min(args.max_samples, len(ds))
    rng = np.random.default_rng(args.seed)
    indices = rng.choice(len(ds), size=n, replace=False) if n < len(ds) else np.arange(len(ds))
    image_dir = Path(args.image_dir); image_dir.mkdir(parents=True, exist_ok=True)
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with out.open('w', encoding='utf-8') as w:
        for idx in indices:
            row = ds.text_data.iloc[int(idx)]
            sample = ds[int(idx)]
            img_path = image_dir / f'{row.patch_id}.jpg'
            if not img_path.exists():
                Image.fromarray(robust_rgb(sample['image_input'].numpy())).save(img_path, quality=92)
            item = {
                'image': str(img_path.resolve()),
                'conversations': [
                    {'from':'human','value':'<image>\n' + str(sample['text_input'])},
                    {'from':'gpt','value':str(sample['reference_output'])},
                ]
            }
            w.write(json.dumps(item, ensure_ascii=False) + '\n')
            written += 1
    print(f'Wrote {written} samples to {out}')

if __name__ == '__main__': main()
