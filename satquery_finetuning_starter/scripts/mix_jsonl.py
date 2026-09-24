#!/usr/bin/env python3
import argparse, json, random
from pathlib import Path

def load(path):
    with open(path, encoding='utf-8') as f: return [json.loads(x) for x in f if x.strip()]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--inputs', nargs='+', required=True); ap.add_argument('--output', required=True); ap.add_argument('--seed', type=int, default=42); args=ap.parse_args()
    rows=[]
    for p in args.inputs:
        d=load(p); print(p, len(d)); rows.extend(d)
    random.Random(args.seed).shuffle(rows)
    out=Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8') as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False)+'\n')
    print('total', len(rows), '->', out)
if __name__=='__main__': main()
