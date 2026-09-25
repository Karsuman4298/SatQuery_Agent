import argparse
import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def wrap(text, width=62):
    text = str(text)
    return "\n".join(textwrap.wrap(text, width=width))


def shorten(text, max_chars=500):
    text = str(text).strip()
    return text if len(text) <= max_chars else text[:max_chars] + "..."


def make_metric_chart(summary_csv, output_path):
    df = pd.read_csv(summary_csv)

    labels = ["Binary Accuracy", "MCQ Accuracy", "Caption ROUGE-L"]
    x = list(range(len(labels)))
    width = 0.34

    fig, ax = plt.subplots(figsize=(10, 6))

    for i, row in df.iterrows():
        vals = [
            float(row["binary_accuracy"]) * 100.0,
            float(row["mcq_accuracy"]) * 100.0,
            float(row["caption_rouge_l_f1"]) * 100.0,
        ]
        pos = [p + (i - (len(df)-1)/2) * width for p in x]
        bars = ax.bar(pos, vals, width=width, label=row["model"])

        for b, v in zip(bars, vals):
            ax.text(
                b.get_x() + b.get_width()/2,
                b.get_height() + 1,
                f"{v:.1f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Score (%)")
    ax.set_ylim(0, 105)
    ax.set_title("BigEarthNet Held-Out Evaluation: Base Qwen vs BEN LoRA")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def make_example_figure(row, rgb_dir, output_path):
    image_path = Path(rgb_dir) / f"{row['patch_id']}.png"
    image = Image.open(image_path).convert("RGB")

    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1])

    ax_img = fig.add_subplot(gs[0, :])
    ax_img.imshow(image)
    ax_img.axis("off")
    ax_img.set_title(
        f"BigEarthNet held-out sample | {row['type']} | {row.get('category', '')}",
        fontsize=14,
    )

    ax_base = fig.add_subplot(gs[1, 0])
    ax_base.axis("off")

    base_text = (
        "QUESTION\n"
        + wrap(shorten(row["question"]))
        + "\n\nGROUND TRUTH\n"
        + wrap(shorten(row["reference"]))
        + "\n\nBASE QWEN3-VL\n"
        + wrap(shorten(row["base_prediction"]))
    )

    if row["type"] in ("binary", "mcq"):
        base_text += "\n\nResult: " + ("CORRECT" if row.get("base_correct") else "INCORRECT")
    elif row["type"] == "captioning":
        base_text += f"\n\nROUGE-L: {float(row.get('base_rouge_l', 0)):.3f}"

    ax_base.text(
        0.02, 0.98, base_text,
        va="top", ha="left",
        fontsize=10,
        transform=ax_base.transAxes,
    )
    ax_base.set_title("Base Qwen3-VL-2B")

    ax_lora = fig.add_subplot(gs[1, 1])
    ax_lora.axis("off")

    lora_text = (
        "QUESTION\n"
        + wrap(shorten(row["question"]))
        + "\n\nGROUND TRUTH\n"
        + wrap(shorten(row["reference"]))
        + "\n\nQWEN3-VL + BEN LoRA\n"
        + wrap(shorten(row["lora_prediction"]))
    )

    if row["type"] in ("binary", "mcq"):
        lora_text += "\n\nResult: " + ("CORRECT" if row.get("lora_correct") else "INCORRECT")
    elif row["type"] == "captioning":
        lora_text += f"\n\nROUGE-L: {float(row.get('lora_rouge_l', 0)):.3f}"

    ax_lora.text(
        0.02, 0.98, lora_text,
        va="top", ha="left",
        fontsize=10,
        transform=ax_lora.transAxes,
    )
    ax_lora.set_title("Fine-Tuned Qwen3-VL-2B")

    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--lora", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--rgb_dir", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--num_binary", type=int, default=3)
    parser.add_argument("--num_mcq", type=int, default=3)
    parser.add_argument("--num_caption", type=int, default=3)
    args = parser.parse_args()

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    base = load_jsonl(args.base).rename(columns={
        "prediction": "base_prediction",
        "correct": "base_correct",
        "rouge_l_f1": "base_rouge_l",
    })

    lora = load_jsonl(args.lora).rename(columns={
        "prediction": "lora_prediction",
        "correct": "lora_correct",
        "rouge_l_f1": "lora_rouge_l",
    })

    key_cols = ["patch_id", "type", "category", "question", "reference"]

    keep_lora = key_cols + [
        c for c in ["lora_prediction", "lora_correct", "lora_rouge_l"]
        if c in lora.columns
    ]

    df = base.merge(lora[keep_lora], on=key_cols, how="inner")

    print("Matched samples:", len(df))

    make_metric_chart(
        args.summary,
        outdir / "01_metric_comparison.png",
    )

    selected = []

    for task, n in [
        ("binary", args.num_binary),
        ("mcq", args.num_mcq),
    ]:
        task_df = df[df["type"] == task].copy()

        improved = task_df[
            (task_df["base_correct"] == False)
            & (task_df["lora_correct"] == True)
        ]

        if len(improved) < n:
            fallback = task_df[task_df["lora_correct"] == True]
            improved = pd.concat(
                [improved, fallback],
                ignore_index=True,
            ).drop_duplicates(subset=["patch_id"])

        selected.extend(improved.head(n).to_dict("records"))

    caption_df = df[df["type"] == "captioning"].copy()

    if len(caption_df):
        caption_df["rouge_gain"] = (
            caption_df["lora_rouge_l"].fillna(0)
            - caption_df["base_rouge_l"].fillna(0)
        )
        caption_df = caption_df.sort_values(
            "rouge_gain",
            ascending=False,
        )
        selected.extend(
            caption_df.head(args.num_caption).to_dict("records")
        )

    for i, row in enumerate(selected, start=2):
        safe_patch = str(row["patch_id"]).replace("/", "_")
        filename = f"{i:02d}_{row['type']}_{safe_patch}.png"

        make_example_figure(
            row,
            args.rgb_dir,
            outdir / filename,
        )

    with open(
        outdir / "selected_examples.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            selected,
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    print("\nCreated:")
    for p in sorted(outdir.iterdir()):
        print(" -", p)


if __name__ == "__main__":
    main()
