#!/usr/bin/env python3
import argparse, json
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True)
    ap.add_argument('--images-root', required=True, help='LEVIR-CC root containing train/A and train/B')
    ap.add_argument('--output', required=True)
    ap.add_argument('--max-samples', type=int, default=0)
    args = ap.parse_args()
    root = Path(args.images_root).resolve()
    with open(args.json, encoding='utf-8') as f: rows = json.load(f)
    if args.max_samples > 0: rows = rows[:args.max_samples]
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    kept = missing = 0
    with out.open('w', encoding='utf-8') as w:
        for r in rows:
            imgs = [root / p for p in r['image']]
            if not all(p.exists() for p in imgs):
                missing += 1; continue
            item = {
                'image': [str(p.resolve()) for p in imgs],
                'conversations': r['conversations'],
            }
            w.write(json.dumps(item, ensure_ascii=False) + '\n')
            kept += 1
    print({'kept': kept, 'missing_pairs': missing})

if __name__ == '__main__': main()
