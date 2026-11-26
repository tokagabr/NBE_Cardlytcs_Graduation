"""
Verification harness.

Runs the whole pipeline from the raw Excel and checks every stage against the
six reference outputs produced by the original notebooks. Any drift in v1
methodology shows up here immediately.

Usage:  python verify.py [path/to/raw.xlsx] [path/to/reference/dir]

Both arguments default to paths relative to this file, so from the project
root `python verify.py` works with no arguments at all:

    python verify.py                      # data/demo.xlsx  +  outputs/
    python verify.py data/demo.xlsx outputs
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.clean import Vocabulary, clean
from pipeline.standardize import standardize
from pipeline.clustering import cluster_merchants
from pipeline.scoring import score_v1
from pipeline.segments import segment_customers

# Everything resolves relative to this file, never to the caller's working
# directory, so the script runs the same from anywhere on any machine.
HERE = Path(__file__).resolve().parent

RAW = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else HERE / "data" / "demo.xlsx"
REF = Path(sys.argv[2]).expanduser() if len(sys.argv) > 2 else HERE / "outputs"

if not RAW.is_absolute():
    RAW = (Path.cwd() / RAW) if (Path.cwd() / RAW).exists() else (HERE / RAW)
if not REF.is_absolute():
    REF = (Path.cwd() / REF) if (Path.cwd() / REF).exists() else (HERE / REF)

if not RAW.exists():
    sys.exit(f"Raw data file not found: {RAW}\nUsage: python verify.py [raw.xlsx] [reference_dir]")
if not REF.is_dir():
    sys.exit(f"Reference directory not found: {REF}\nUsage: python verify.py [raw.xlsx] [reference_dir]")

EXPECTED_REFERENCE_FILES = [
    "nbe_merchants_clean.csv", "customer_segments.csv", "merchant_clusters.csv",
    "partnership_ranking.csv", "loyalty_ranking.csv", "bnpl_ranking.csv",
    "potential_merchant_score.csv",
]
absent = [f for f in EXPECTED_REFERENCE_FILES if not (REF / f).exists()]
if absent:
    sys.exit(
        f"Reference directory {REF} is missing {len(absent)} file(s):\n  "
        + "\n  ".join(absent)
    )

print(f"raw data  : {RAW}")
print(f"reference : {REF}")

results: list[tuple[str, str, float]] = []


def compare(label: str, mine: pd.Series, theirs: pd.Series) -> float:
    if mine.dtype.kind == "f" and theirs.dtype.kind == "f":
        score = float(np.isclose(mine, theirs, equal_nan=True).mean())
    else:
        score = float(
            (mine.fillna("~").astype(str) == theirs.fillna("~").astype(str)).mean()
        )
    return score


def section(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


raw = pd.read_excel(RAW)
# Route through Stage 0 as the app does, so verification covers the real path.
standardised, standardisation = standardize(raw)
if standardisation["status"] == "blocked":
    sys.exit("Standardisation blocked: " + "; ".join(standardisation["errors"]))
clean_df, report = clean(standardised, Vocabulary(), deduplicate=False)

section("STAGE 1  clean.py  vs  nbe_merchants_clean.csv")
reference = pd.read_csv(REF / "nbe_merchants_clean.csv", low_memory=False)
reference["Txn date"] = pd.to_datetime(reference["Txn date"])
reference["Posting Date"] = pd.to_datetime(reference["Posting Date"])
for column in reference.columns:
    score = compare(column, clean_df[column], reference[column])
    results.append(("stage1", column, score))
    print(f"  {column:20s} {score:9.4%}{'' if score == 1 else '   MISMATCH'}")

section("STAGE 3  segments.py  vs  customer_segments.csv")
customers, thresholds = segment_customers(clean_df)
reference_segments = pd.read_csv(REF / "customer_segments.csv").sort_values("PAN").reset_index(drop=True)
for column in reference_segments.columns:
    score = compare(column, customers[column], reference_segments[column])
    results.append(("stage3", column, score))
    print(f"  {column:22s} {score:9.4%}{'' if score == 1 else '   MISMATCH'}")

section("STAGE 2  clustering.py v1  vs  merchant_clusters.csv")
clusters, diagnostics = cluster_merchants(clean_df, customers, version="v1")
reference_clusters = pd.read_csv(REF / "merchant_clusters.csv")
merged = clusters.merge(reference_clusters, on="merchant", suffixes=("_mine", "_ref"))
name_match = float((merged["cluster_name_mine"] == merged["cluster_name_ref"]).mean())
results.append(("stage2", "cluster_name", name_match))
print(f"  cluster_name         {name_match:9.4%}{'' if name_match == 1 else '   MISMATCH'}")
print(f"  silhouette           {diagnostics['silhouette']:.4f}   (reference notebook: 0.325)")
for column in ["total_amount_egp", "avg_ticket_egp", "transaction_count",
               "unique_customers", "mass_concentration", "vip_concentration"]:
    score = float(np.isclose(merged[f"{column}_mine"], merged[f"{column}_ref"]).mean())
    results.append(("stage2", column, score))
    print(f"  {column:20s} {score:9.4%}{'' if score == 1 else '   MISMATCH'}")

section("STAGE 4  scoring.py v1  vs  ranking CSVs")
rankings = score_v1(clean_df, clusters)
files = {
    "partnership": "partnership_ranking.csv",
    "loyalty": "loyalty_ranking.csv",
    "bnpl": "bnpl_ranking.csv",
    "potential": "potential_merchant_score.csv",
}
for deliverable, filename in files.items():
    reference_ranking = pd.read_csv(REF / filename)
    column = f"{deliverable}_rank"
    merged = rankings[deliverable][["merchant", column]].merge(
        reference_ranking[["merchant", column]], on="merchant", suffixes=("_m", "_r")
    )
    score = float((merged[f"{column}_m"] == merged[f"{column}_r"]).mean())
    results.append(("stage4", deliverable, score))
    print(f"  {deliverable:20s} {score:9.4%}{'' if score == 1 else '   MISMATCH'}")

section("MERCHANT RESOLUTION")
print(f"  known merchants      {report['known_merchants']}")
print(f"  new merchants        {report['new_merchants']}")
print(f"  unknown merchants    {report['unknown_merchants']}")
print(f"  auto-corrections     {len(report['auto_corrections'])}")
print(f"  city candidates      {len(report['city_candidates'])}")
print(f"  category mapped      {report['category_mapped']:,} rows")
print(f"  category inferred    {report['category_inferred']:,} rows")
print(f"  category Unknown     {report['category_unknown']:,} rows")
print(f"  geo confidence       {report['geo_confidence_counts']}")

failures = [r for r in results if r[2] < 1.0]
section("RESULT")
if failures:
    print(f"  {len(failures)} of {len(results)} checks FAILED:")
    for stage, name, score in failures:
        print(f"    {stage}  {name}  {score:.4%}")
    sys.exit(1)
print(f"  All {len(results)} checks passed. v1 methodology reproduces exactly.")
