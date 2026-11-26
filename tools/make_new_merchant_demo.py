"""
Build `data/demo_new_merchants.xlsx`, a demo variant containing merchants that
are genuinely absent from the reference list.

Why this exists: the reference dataset resolves 77 of 77 merchants to `known`,
so the entire new-merchant path (detection, badging, category inference,
clustering, ranking) is invisible when demonstrating the app. This variant adds
a small number of real-looking merchants so the feature can be shown.

The original `data/demo.xlsx` is read only and never modified. Reference and
verification results continue to come from that file.

Injected rows are cloned from existing transactions so amounts, dates, PANs and
gateway prefixes stay realistic. Only the merchant token inside `Description`
is rewritten, which is exactly how a genuinely new merchant would arrive.

Usage:  python tools/make_new_merchant_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from pipeline.clean import Vocabulary, clean  # noqa: E402
from pipeline.standardize import standardize  # noqa: E402

SOURCE = ROOT / "data" / "demo.xlsx"
TARGET = ROOT / "data" / "demo_new_merchants.xlsx"

# Each entry: the new merchant name, the existing merchant whose rows are
# cloned, and how many rows to clone. Donors are chosen so each new merchant
# lands in a different part of the spend distribution, and the names are chosen
# so category keyword inference has something to work with.
INJECTIONS = [
    # High ticket, electronics. Should infer a category from the keyword rules.
    {"name": "NOOR ELECTRONICS", "donor": "SPINNEYS", "rows": 900},
    # Mid volume, pharmacy. Different governorate spread from its donor.
    {"name": "SHIFA PHARMACY", "donor": "PIZZA HUT", "rows": 600},
    # Low volume, no keyword in the name. Should resolve as new with an
    # Unknown category, which is the honest outcome and worth showing.
    {"name": "BARAKA TRADING", "donor": "CAREEM", "rows": 250},
]


def build() -> pd.DataFrame:
    raw = pd.read_excel(SOURCE)
    frames = [raw]

    for spec in INJECTIONS:
        donor_rows = raw[raw["Description"].str.contains(spec["donor"], na=False)]
        if donor_rows.empty:
            raise SystemExit(f"Donor merchant '{spec['donor']}' not found in {SOURCE.name}")
        if len(donor_rows) < spec["rows"]:
            raise SystemExit(
                f"Donor '{spec['donor']}' has only {len(donor_rows)} rows, "
                f"need {spec['rows']}"
            )
        injected = donor_rows.head(spec["rows"]).copy()
        injected["Description"] = injected["Description"].str.replace(
            spec["donor"], spec["name"], regex=False
        )
        frames.append(injected)

    return pd.concat(frames, ignore_index=True)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Source demo file not found: {SOURCE}")

    combined = build()
    combined.to_excel(TARGET, index=False)

    # Prove the file does what it claims before handing it over.
    standardised, std_report = standardize(combined)
    clean_df, report = clean(standardised, Vocabulary(), deduplicate=False)

    print(f"Wrote {TARGET}")
    print(f"  rows: {len(combined):,} ({len(combined) - len(pd.read_excel(SOURCE)):,} injected)")
    print(f"  standardisation: {std_report['status']}")
    print(f"  known merchants:       {report['known_merchants']}")
    print(f"  new merchants:         {report['new_merchants']}")
    print(f"  unresolvable merchants:{report['unknown_merchants']}")
    print("\n  New merchants detected:")
    table = report["new_merchant_table"]
    if table.empty:
        raise SystemExit("FAILED: no new merchants detected in the generated file.")
    for _, row in table.iterrows():
        print(
            f"    {row['merchant']:20s} category={row['category']} "
            f"({row['category_status']}) geo={row['geo_confidence']} "
            f"txns={row['transactions']:,}"
        )

    expected = {spec["name"] for spec in INJECTIONS}
    found = set(table["merchant"])
    if expected != found:
        raise SystemExit(f"FAILED: expected {expected}, detected {found}")
    print("\n  All injected merchants detected as 'new'.")


if __name__ == "__main__":
    main()
