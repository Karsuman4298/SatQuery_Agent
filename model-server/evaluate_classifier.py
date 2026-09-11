"""Evaluate IntentClassifier against a held-out test set.

Produces per-task precision, recall, F1, and a confusion matrix.
Applies the 90% per-task gate: tasks that fall below 90% precision OR recall
are disabled via classifier.set_enabled_tasks().

Usage:
    python evaluate_classifier.py [--testset tests/query_classification_testset.jsonl]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

from app.agent.classifier import IntentClassifier, TaskLabel


TASK_LABELS: list[TaskLabel] = ["vqa", "segmentation", "change_detection", "fusion", "conversational"]


async def run_evaluation(testset_path: str) -> dict:
    classifier = IntentClassifier()
    await classifier.initialize()

    # Load held-out test set
    examples: list[dict] = []
    with open(testset_path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    print(f"\nEvaluating {len(examples)} held-out examples...\n")

    # Classify each example
    predictions: list[tuple[str, str | None, float]] = []  # (true_label, predicted, confidence)
    for i, ex in enumerate(examples):
        query = ex["query"]
        true_label = ex["label"]
        predicted, confidence, scores = await classifier.classify(query)
        predictions.append((true_label, predicted, confidence))
        if predicted != true_label:
            print(f"  MISS [{i+1:3d}] true={true_label:<20s} pred={str(predicted):<20s} conf={confidence:.3f}  q=\"{query}\"")

    # Build confusion matrix
    confusion: dict[str, dict[str, int]] = {t: defaultdict(int) for t in TASK_LABELS}
    for true_label, predicted, _ in predictions:
        pred_str = predicted if predicted else "AMBIGUOUS"
        confusion[true_label][pred_str] += 1

    # Per-task metrics
    metrics: dict[str, dict[str, float]] = {}
    for task in TASK_LABELS:
        tp = confusion[task].get(task, 0)
        fn = sum(v for k, v in confusion[task].items() if k != task)
        fp = sum(confusion[other].get(task, 0) for other in TASK_LABELS if other != task)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        metrics[task] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": tp + fn,
        }

    # Overall accuracy
    correct = sum(1 for t, p, _ in predictions if t == p)
    accuracy = correct / len(predictions) if predictions else 0.0

    # 90% gate
    passed_tasks: set[TaskLabel] = set()
    failed_tasks: set[TaskLabel] = set()
    for task in TASK_LABELS:
        m = metrics[task]
        if m["precision"] >= 0.90 and m["recall"] >= 0.90:
            passed_tasks.add(task)
        else:
            failed_tasks.add(task)

    # Print results
    print("\n" + "=" * 80)
    print("HELD-OUT EVALUATION RESULTS")
    print("=" * 80)

    print(f"\nOverall accuracy: {accuracy:.1%} ({correct}/{len(predictions)})\n")

    print(f"{'Task':<20s} {'Precision':>10s} {'Recall':>10s} {'F1':>10s} {'Support':>8s} {'Gate':>8s}")
    print("-" * 66)
    for task in TASK_LABELS:
        m = metrics[task]
        gate_status = "PASS" if task in passed_tasks else "FAIL"
        print(f"{task:<20s} {m['precision']:>10.1%} {m['recall']:>10.1%} {m['f1']:>10.1%} {m['support']:>8d} {gate_status:>8s}")

    print(f"\n\nCONFUSION MATRIX (rows=true, cols=predicted)")
    all_preds = sorted(set(p for _, p, _ in predictions if p) | set(TASK_LABELS))
    true_pred_label = "True \\ Pred"
    header = f"{true_pred_label:<20s}" + "".join(f"{p:>14s}" for p in all_preds)
    print(header)
    print("-" * len(header))
    for true_task in TASK_LABELS:
        row = f"{true_task:<20s}"
        for pred_task in all_preds:
            count = confusion[true_task].get(pred_task, 0)
            cell = f"{count:>14d}" if count > 0 else f"{'·':>14s}"
            row += cell
        print(row)

    print(f"\n90% GATE RESULT:")
    print(f"  Passed: {sorted(passed_tasks)}")
    if failed_tasks:
        print(f"  FAILED (will fall back to explicit mode selection): {sorted(failed_tasks)}")
    else:
        print(f"  All tasks passed the 90% gate.")

    # Apply the gate to the classifier
    classifier.set_enabled_tasks(passed_tasks)

    return {
        "accuracy": round(accuracy, 4),
        "metrics": metrics,
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "passed_tasks": sorted(passed_tasks),
        "failed_tasks": sorted(failed_tasks),
        "total_examples": len(predictions),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate IntentClassifier on held-out test set")
    parser.add_argument(
        "--testset",
        default="tests/query_classification_testset.jsonl",
        help="Path to JSONL test set file",
    )
    args = parser.parse_args()

    if not Path(args.testset).exists():
        print(f"ERROR: Test set file not found: {args.testset}", file=sys.stderr)
        sys.exit(1)

    result = asyncio.run(run_evaluation(args.testset))

    # Write machine-readable output
    output_path = Path(args.testset).parent / "classification_eval_results.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nMachine-readable results written to: {output_path}")


if __name__ == "__main__":
    main()
