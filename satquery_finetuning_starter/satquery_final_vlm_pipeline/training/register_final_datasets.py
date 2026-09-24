import argparse
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument("--qwen_root", required=True)
p.add_argument("--ben", default="")
p.add_argument("--final", default="")
a=p.parse_args()

init=Path(a.qwen_root)/"qwen-vl-finetune/qwenvl/data/__init__.py"
txt=init.read_text()

BEGIN="# SATQUERY_FINAL_DATASETS_BEGIN"
END="# SATQUERY_FINAL_DATASETS_END"
if BEGIN in txt and END in txt:
    pre=txt.split(BEGIN)[0]
    post=txt.split(END,1)[1]
    txt=pre+post

blocks=[]
if a.ben:
    blocks.append(f'''SATQUERY_BEN = {{
    "annotation_path": r"{Path(a.ben).resolve()}",
    "data_path": "",
}}
data_dict["satquery_ben"] = SATQUERY_BEN''')
if a.final:
    blocks.append(f'''SATQUERY_FINAL = {{
    "annotation_path": r"{Path(a.final).resolve()}",
    "data_path": "",
}}
data_dict["satquery_final"] = SATQUERY_FINAL''')

append="\n"+BEGIN+"\n"+"\n\n".join(blocks)+"\n"+END+"\n"
init.write_text(txt.rstrip()+append)
print("Updated", init)
