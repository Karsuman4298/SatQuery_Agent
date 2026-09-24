#!/usr/bin/env python3
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('path'); args=ap.parse_args()
    good=bad=0
    with open(args.path, encoding='utf-8') as f:
        for ln,line in enumerate(f,1):
            try:
                r=json.loads(line)
                imgs=r.get('image', [])
                imgs=[imgs] if isinstance(imgs,str) else imgs
                conv=r['conversations']
                prompt=' '.join(str(x.get('value','')) for x in conv if x.get('from')=='human')
                if prompt.count('<image>') != len(imgs): raise ValueError(f'<image> count {prompt.count("<image>")} != images {len(imgs)}')
                if not all(Path(x).exists() for x in imgs): raise FileNotFoundError('missing image')
                if not conv or conv[-1].get('from')!='gpt': raise ValueError('last turn must be gpt')
                good += 1
            except Exception as e:
                bad += 1
                if bad <= 20: print('BAD', ln, e)
    print({'good':good,'bad':bad})
    if bad: raise SystemExit(2)
if __name__=='__main__': main()
