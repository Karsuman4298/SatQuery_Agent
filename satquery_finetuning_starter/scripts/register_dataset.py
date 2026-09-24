#!/usr/bin/env python3
import argparse
from pathlib import Path

BEGIN='# SATQUERY_DATASET_BEGIN'
END='# SATQUERY_DATASET_END'

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--qwen-root', required=True); ap.add_argument('--annotations', required=True); ap.add_argument('--name', default='satquery_rs'); args=ap.parse_args()
    target=Path(args.qwen_root)/'qwen-vl-finetune/qwenvl/data/__init__.py'
    text=target.read_text()
    if BEGIN in text:
        a=text.index(BEGIN); b=text.index(END)+len(END); text=text[:a]+text[b:]
    ann=str(Path(args.annotations).resolve())
    block=f'''\n{BEGIN}\nSATQUERY_RS = {{\n    "annotation_path": r"{ann}",\n    "data_path": "",\n}}\ndata_dict["{args.name}"] = SATQUERY_RS\n{END}\n'''
    target.write_text(text.rstrip()+block)
    print('Registered', args.name, 'in', target)
if __name__=='__main__': main()
