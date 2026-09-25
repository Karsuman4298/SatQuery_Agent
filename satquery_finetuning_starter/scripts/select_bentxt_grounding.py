import argparse
from pathlib import Path

import pandas as pd


parser = argparse.ArgumentParser()

parser.add_argument(
    "--input",
    required=True,
)

parser.add_argument(
    "--output",
    required=True,
)

parser.add_argument(
    "--reference",
    type=int,
    default=40000,
)

parser.add_argument(
    "--point",
    type=int,
    default=20000,
)

parser.add_argument(
    "--seed",
    type=int,
    default=42,
)

args = parser.parse_args()


cols = [
    "patch_id",
    "input",
    "output",
    "type",
    "category",
    "split",
]

df = pd.read_parquet(
    args.input,
    columns=cols,
)


# --------------------------------------------------------
# Training split only
# --------------------------------------------------------

df = df[
    df["split"]
    .astype(str)
    .str.lower()
    .eq("train")
].copy()


# --------------------------------------------------------
# Bounding-box examples only
# --------------------------------------------------------

df = df[
    df["type"]
    .astype(str)
    .str.lower()
    .eq("bounding box")
].copy()


df["category_norm"] = (
    df["category"]
    .astype(str)
    .str.lower()
    .str.strip()
)


# --------------------------------------------------------
# Remove malformed rows
# --------------------------------------------------------

df = df[
    df["input"].notna()
    & df["output"].notna()
    & df["patch_id"].notna()
].copy()


# --------------------------------------------------------
# Reference grounding
# --------------------------------------------------------

reference = df[
    df["category_norm"].eq("reference")
].sample(
    n=min(
        args.reference,
        len(
            df[
                df["category_norm"]
                .eq("reference")
            ]
        ),
    ),
    random_state=args.seed,
)


# --------------------------------------------------------
# Point grounding
# --------------------------------------------------------

point = df[
    df["category_norm"].eq("point")
].sample(
    n=min(
        args.point,
        len(
            df[
                df["category_norm"]
                .eq("point")
            ]
        ),
    ),
    random_state=args.seed + 1,
)


out = pd.concat(
    [reference, point],
    ignore_index=True,
)


out = out.sample(
    frac=1.0,
    random_state=args.seed,
).reset_index(drop=True)


Path(args.output).parent.mkdir(
    parents=True,
    exist_ok=True,
)


out.to_parquet(
    args.output,
    index=False,
)


print(
    {
        "rows": len(out),
        "unique_patches": out[
            "patch_id"
        ].nunique(),
        "categories": out[
            "category_norm"
        ].value_counts().to_dict(),
        "output": args.output,
    }
)