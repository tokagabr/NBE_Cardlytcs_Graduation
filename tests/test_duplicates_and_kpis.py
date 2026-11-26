"""Regression tests for the two fixes made after Phase 5.5.

1. avg_settlement_lag must never surface NaN.
2. Exact duplicates must be judged on the file as supplied, not on the
   reduced column set, so rows differing only in a dropped column survive.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from pipeline import kpis, loader
from pipeline.clean import Vocabulary, clean
from pipeline.standardize import standardize

DATA = Path(__file__).resolve().parent.parent / "data"
raw = pd.read_excel(DATA / "demo.xlsx")
fails = []

def check(label, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}: {got!r} (expected {want!r})")
    if not ok:
        fails.append(label)

def pipeline(df):
    std, rep = standardize(df)
    return clean(std, Vocabulary(), deduplicate=False)[0], rep

print("\nSETTLEMENT LAG")
c, _ = pipeline(raw)
lag = kpis.executive_kpis(c)["Settlement lag (days)"]
check("present when Posting Date exists", round(lag, 5), 0.79153)
c2, _ = pipeline(raw.drop(columns=["Posting Date"]))
check("None when Posting Date absent", kpis.executive_kpis(c2)["Settlement lag (days)"], None)
check("None on an empty frame", kpis.avg_settlement_lag(c.head(0)), None)
partial = c.copy()
partial.loc[partial.index[:50000], "Posting Date"] = pd.NaT
check("computed over rows that have it", round(kpis.avg_settlement_lag(partial), 4), 0.7896)
allmissing = c.copy(); allmissing["Posting Date"] = pd.NaT
check("None when every posting date is blank", kpis.avg_settlement_lag(allmissing), None)

print("\nDUPLICATES")
pair = raw.head(1).copy(); twin = pair.copy(); twin["In Dispute?"] = "Y"
c3, r3 = pipeline(pd.concat([raw, pair, twin], ignore_index=True))
check("row differing only by a dropped column survives", len(c3), 100_001)
check("  and the true duplicate is still removed", r3["duplicates"]["removed"], 1)
c4, r4 = pipeline(pd.concat([raw, raw.head(3)], ignore_index=True))
check("fully identical rows are removed", len(c4), 100_000)
check("  count reported", r4["duplicates"]["removed"], 3)
c5, r5 = pipeline(raw)
check("untouched demo unchanged", len(c5), 100_000)
check("  nothing removed", r5["duplicates"]["removed"], 0)
check("decision uses all supplied columns", r5["duplicates"]["decided_on_columns"], 14)
_, r6 = clean(raw, Vocabulary())
check("standalone clean() still dedupes by default", r6["duplicates_removed"], 0)

print("\n" + ("ALL PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
