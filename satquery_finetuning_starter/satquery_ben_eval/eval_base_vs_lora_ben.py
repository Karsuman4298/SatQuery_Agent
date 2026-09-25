import argparse, json, re, string, csv, gc
from pathlib import Path
import pandas as pd
import torch
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
from peft import PeftModel

def norm_text(s):
    s = str(s).strip().lower()
    s = s.translate(str.maketrans("", "", string.punctuation))
    s = re.sub(r"\s+", " ", s)
    return s

def extract_choice(s):
    s = str(s).strip().lower()
    m = re.search(r"\b([abcd])\b", s)
    if m:
        return m.group(1)
    m = re.search(r"(?:option\s*)?[\(\[]?([abcd])[\)\].,:]?", s)
    return m.group(1) if m else norm_text(s)

def binary_label(s):
    s = norm_text(s)
    if re.search(r"\byes\b", s):
        return "yes"
    if re.search(r"\bno\b", s):
        return "no"
    return s

def lcs_len(a, b):
    a, b = a.split(), b.split()
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j-1] + 1 if x == y else max(prev[j], cur[-1]))
        prev = cur
    return prev[-1]

def rouge_l_f1(pred, ref):
    p, r = norm_text(pred), norm_text(ref)
    if not p or not r:
        return 0.0
    l = lcs_len(p, r)
    pp, rr = len(p.split()), len(r.split())
    precision = l / pp
    recall = l / rr
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)

def make_inputs(processor, image, prompt):
    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": prompt},
        ],
    }]
    return processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    ).to("cuda")

def run_model(tag, base_path, adapter_path, df, rgb_dir, out_jsonl, max_caption_tokens):
    processor = AutoProcessor.from_pretrained(base_path)

    print(f"\nLoading {tag}...")
    base = Qwen3VLForConditionalGeneration.from_pretrained(
        base_path,
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
    ).to("cuda")

    model = base if adapter_path is None else PeftModel.from_pretrained(base, adapter_path)
    model.eval()

    counts = {
        "binary_n": 0, "binary_correct": 0,
        "mcq_n": 0, "mcq_correct": 0,
        "caption_n": 0, "caption_rouge_l_sum": 0.0,
    }

    out_path = Path(out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as fo:
        for j, row in enumerate(df.itertuples(index=False), 1):
            image = str((Path(rgb_dir) / f"{row.patch_id}.png").resolve())
            prompt = str(row.input).strip()
            ref = str(row.output).strip()
            typ = str(row.type).lower()

            inputs = make_inputs(processor, image, prompt)

            with torch.inference_mode():
                ids = model.generate(
                    **inputs,
                    max_new_tokens=max_caption_tokens if typ == "captioning" else 32,
                    do_sample=False,
                )

            gen = ids[:, inputs["input_ids"].shape[1]:]
            pred = processor.batch_decode(
                gen,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0].strip()

            result = {
                "model": tag,
                "patch_id": row.patch_id,
                "type": row.type,
                "category": row.category,
                "question": prompt,
                "reference": ref,
                "prediction": pred,
            }

            if typ == "binary":
                counts["binary_n"] += 1
                ok = binary_label(pred) == binary_label(ref)
                counts["binary_correct"] += int(ok)
                result["correct"] = bool(ok)

            elif typ == "mcq":
                counts["mcq_n"] += 1
                ok = extract_choice(pred) == extract_choice(ref)
                counts["mcq_correct"] += int(ok)
                result["correct"] = bool(ok)

            elif typ == "captioning":
                counts["caption_n"] += 1
                score = rouge_l_f1(pred, ref)
                counts["caption_rouge_l_sum"] += score
                result["rouge_l_f1"] = score

            fo.write(json.dumps(result, ensure_ascii=False) + "\n")

            if j % 50 == 0:
                print(f"{tag}: {j}/{len(df)}")

    summary = {
        "model": tag,
        "binary_n": counts["binary_n"],
        "binary_accuracy": counts["binary_correct"] / max(counts["binary_n"], 1),
        "mcq_n": counts["mcq_n"],
        "mcq_accuracy": counts["mcq_correct"] / max(counts["mcq_n"], 1),
        "caption_n": counts["caption_n"],
        "caption_rouge_l_f1": counts["caption_rouge_l_sum"] / max(counts["caption_n"], 1),
    }

    del model, base, processor
    gc.collect()
    torch.cuda.empty_cache()
    return summary

p = argparse.ArgumentParser()
p.add_argument("--eval_parquet", required=True)
p.add_argument("--rgb_dir", required=True)
p.add_argument("--base", required=True)
p.add_argument("--adapter", required=True)
p.add_argument("--output_dir", required=True)
p.add_argument("--max_caption_tokens", type=int, default=128)
args = p.parse_args()

df = pd.read_parquet(args.eval_parquet)
out = Path(args.output_dir)
out.mkdir(parents=True, exist_ok=True)

base_summary = run_model(
    "Qwen3-VL-2B Base",
    args.base, None, df, args.rgb_dir,
    out / "base_predictions.jsonl",
    args.max_caption_tokens,
)

lora_summary = run_model(
    "Qwen3-VL-2B + BEN LoRA",
    args.base, args.adapter, df, args.rgb_dir,
    out / "lora_predictions.jsonl",
    args.max_caption_tokens,
)

summaries = [base_summary, lora_summary]

with (out / "summary.json").open("w") as f:
    json.dump(summaries, f, indent=2)

with (out / "summary.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=summaries[0].keys())
    w.writeheader()
    w.writerows(summaries)

print("\n================ RESULTS ================")
for s in summaries:
    print(s)

print("\nSaved:", out / "summary.csv")
