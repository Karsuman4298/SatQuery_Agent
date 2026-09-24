#!/usr/bin/env python3
import argparse, json, os
from pathlib import Path

GROUNDING_WORDS = ('bounding box', 'bbox', 'locate ', 'coordinates', 'location of the referred')

def find_images(root: Path):
    idx = {}
    for p in root.rglob('*'):
        if p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp'}:
            idx.setdefault(p.name, p.resolve())
    return idx

def is_grounding(record):
    text = ' '.join(str(x.get('value','')) for x in record.get('conversations', [])).lower()
    return any(k in text for k in GROUNDING_WORDS)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', required=True)
    ap.add_argument('--images', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--keep-grounding', action='store_true')
    args = ap.parse_args()

    with open(args.json, 'r', encoding='utf-8') as f:
        rows = json.load(f)
    image_index = find_images(Path(args.images))
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    kept = missing = filtered = 0
    with out.open('w', encoding='utf-8') as w:
        for r in rows:
            if not args.keep_grounding and is_grounding(r):
                filtered += 1; continue
            img = r.get('image')
            if isinstance(img, list):
                names = [Path(x).name for x in img]
                try: resolved = [str(image_index[n]) for n in names]
                except KeyError: missing += 1; continue
            else:
                name = Path(str(img)).name
                if name not in image_index:
                    missing += 1; continue
                resolved = str(image_index[name])
            item = {'image': resolved, 'conversations': r['conversations']}
            w.write(json.dumps(item, ensure_ascii=False) + '\n')
            kept += 1
    print({'kept': kept, 'filtered_grounding': filtered, 'missing_images': missing})

if __name__ == '__main__': main()
