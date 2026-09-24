import argparse, json, re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--input", required=True)
p.add_argument("--output", required=True)
a = p.parse_args()

tag = re.compile(r"^\s*\[(?:vqa|caption)\]\s*", re.I)
suffixes = [
    re.compile(r"\s*A short answer is\s*$", re.I),
    re.compile(r"\s*A short answer to the question is\s*$", re.I),
]

n = 0
with open(a.input, encoding="utf-8") as fi, open(a.output, "w", encoding="utf-8") as fo:
    for line in fi:
        if not line.strip():
            continue
        x = json.loads(line)
        for t in x["conversations"]:
            if t.get("from") == "human":
                v = t.get("value","")
                head = "<image>\n" if "<image>" in v else ""
                v = v.replace("<image>", "").strip()
                v = tag.sub("", v)
                for rx in suffixes:
                    v = rx.sub("", v)
                t["value"] = head + v.strip()
        fo.write(json.dumps(x, ensure_ascii=False) + "\n")
        n += 1
print({"written": n, "output": a.output})
