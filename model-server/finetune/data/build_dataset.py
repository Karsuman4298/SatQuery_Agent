"""Build validated JSONL records for remote-sensing LoRA/QLoRA training.

Inputs are JSONL files containing image path, question, tool context, and a
judge-approved target. This script intentionally rejects records without an
explicit uncertainty/unsupported label for unanswerable questions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    with path.open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def normalize(record: dict) -> dict:
    required = ("question", "target")
    missing = [key for key in required if not record.get(key)]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    target = record["target"]
    if not isinstance(target, dict):
        raise ValueError("target must be an object")
    if "claims" not in target and target.get("source_type") != "unsupported":
        raise ValueError("target must contain claims or explicitly be unsupported")
    if not record.get("image") and target.get("source_type") != "unsupported":
        raise ValueError("answerable multimodal records require an image")
    return {
        "system": record.get("system", "You are a professional remote-sensing analyst."),
        "image": record.get("image"),
        "tool_context": record.get("tool_context", {}),
        "user": record["question"],
        "target": target,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    output_records = []
    for input_path in args.inputs:
        for record in read_jsonl(input_path):
            output_records.append(normalize(record))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as stream:
        for record in output_records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"wrote {len(output_records)} validated records to {args.output}")


if __name__ == "__main__":
    main()
