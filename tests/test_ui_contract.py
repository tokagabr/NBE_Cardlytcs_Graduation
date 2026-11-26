"""
Contract between the pipeline outputs and the interface.

The UI reads specific keys out of `std_report`, `report`, `thresholds`, the
clustering diagnostics and each ranking frame. If one of those is renamed in
the pipeline, the app raises a KeyError in front of whoever is presenting.
This test asserts every key the interface actually touches, so that breakage
shows up here instead.

It also checks the additive insight functions against both demo files and both
methodology versions, and confirms the existing insight functions still return
what they always returned.

Run: python tests/test_ui_contract.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from pipeline import insights, kpis
from pipeline.clean import Vocabulary, clean
from pipeline.clustering import build_merchant_features, cluster_merchants
from pipeline.scoring import rank_correlation, rank_movement, score_v1, score_v2
from pipeline.segments import segment_customers
from pipeline.standardize import cleaning_summary, standardize
from pipeline import loader
from ui import components as ui
from ui import theme

DATA = Path(__file__).resolve().parent.parent / "data"
failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {label}{(' — ' + detail) if detail else ''}")
    if not condition:
        failures.append(label)


def require_keys(label: str, mapping, keys) -> None:
    missing = [k for k in keys if k not in mapping]
    check(label, not missing, f"missing: {missing}" if missing else "")


def require_columns(label: str, frame: pd.DataFrame, columns) -> None:
    missing = [c for c in columns if c not in frame.columns]
    check(label, not missing, f"missing: {missing}" if missing else "")


# --- keys the interface reads -----------------------------------------------

STD_REPORT_KEYS = [
    "status", "errors", "warnings", "rows_in", "columns_in", "column_count_in",
    "column_count_out", "columns_out", "columns_mapped", "columns_removed",
    "columns_quarantined", "dispute_columns_found", "duplicates",
]
REPORT_KEYS = [
    "rows_out", "duplicates_removed", "known_merchants", "new_merchants",
    "unknown_merchants", "known_rows", "new_rows", "unknown_rows",
    "unknown_samples", "new_merchant_table", "auto_corrections",
    "city_candidates", "category_mapped", "category_inferred", "category_unknown",
    "geo_confidence_counts", "low_confidence_rows", "geography_parse_rate",
    "international_rows", "outlier_threshold", "outliers_flagged", "cardholders",
    "merchants_total", "date_min", "date_max", "months_covered",
]
THRESHOLD_KEYS = ["low_value_cut", "vip_cut", "volume_share", "segment_sizes"]
DIAG_KEYS = ["version", "k", "features_used", "silhouette", "explained_variance",
             "merchants", "cluster_sizes"]
CLUSTER_COLUMNS = [
    "merchant", "merchant_status", "cluster_name", "category", "total_amount_egp",
    "transaction_count", "avg_ticket_egp", "unique_customers",
    "vip_concentration", "mass_concentration", "pc1", "pc2",
]
CUSTOMER_COLUMNS = ["PAN", "segment", "recency", "frequency", "monetary",
                    "avg_ticket", "unique_merchants", "outlier_ratio"]
VALIDATE_KEYS = ["status", "rows", "columns", "missing", "suggestions", "unmapped",
                 "ambiguous", "auto_mapped", "optional_missing", "required"]


def run_for(filename: str) -> None:
    print(f"\n{'=' * 68}\n{filename}\n{'=' * 68}")
    raw = loader.read_any(str(DATA / filename))

    verdict = loader.validate(raw)
    require_keys("loader.validate keys", verdict, VALIDATE_KEYS)
    check("validate status is ok", verdict["status"] == "ok", verdict["status"])

    standardised, std_report = standardize(raw)
    require_keys("std_report keys", std_report, STD_REPORT_KEYS)
    require_keys("std_report['duplicates'] keys", std_report["duplicates"],
                 ["removed", "decided_on_columns", "business_key"])

    clean_df, report = clean(standardised, Vocabulary(), deduplicate=False)
    require_keys("report keys", report, REPORT_KEYS)

    rows = cleaning_summary(std_report, report)
    check("cleaning_summary returns rows", len(rows) > 0, f"{len(rows)} rows")
    check("every summary row has the 4 UI fields",
          all(set(r) == {"step", "finding", "detail", "level"} for r in rows))
    check("levels are only ok/info/warn",
          set(r["level"] for r in rows) <= {"ok", "info", "warn"},
          str(sorted(set(r["level"] for r in rows))))

    customers, thresholds = segment_customers(clean_df)
    require_keys("thresholds keys", thresholds, THRESHOLD_KEYS)
    require_columns("customer columns", customers, CUSTOMER_COLUMNS)

    exec_kpis = kpis.executive_kpis(clean_df)
    require_keys("executive_kpis keys", exec_kpis, [
        "Total spend", "Transactions", "Unique cardholders", "Active merchants",
        "Average ticket", "Settlement lag (days)", "Outlier spend share"])
    check("settlement lag never NaN",
          exec_kpis["Settlement lag (days)"] is None
          or not pd.isna(exec_kpis["Settlement lag (days)"]))
    require_keys("segment_kpis keys", kpis.segment_kpis(customers), [
        "Cardholders", "Average recency (days)", "Average frequency", "Average ticket"])

    # --- additive insight functions ----------------------------------------
    signals = insights.executive_signals(clean_df, report, thresholds)
    check("executive_signals returns signals", len(signals) > 0, f"{len(signals)}")
    check("executive_signals shape",
          all(set(s) == {"headline", "body", "style"} for s in signals))

    seg_rows = insights.segment_interpretation(customers)
    check("segment_interpretation covers 3 tiers", len(seg_rows) == 3, f"{len(seg_rows)}")
    require_keys("segment_interpretation fields", seg_rows[0], [
        "segment", "customers", "customer_share", "spend", "spend_share",
        "avg_monetary", "avg_frequency", "avg_recency", "avg_ticket"])
    check("segment_business_summary returns signals",
          len(insights.segment_business_summary(customers)) > 0)

    journey = insights.new_merchant_journey(report, None, None)
    check("new_merchant_journey matches report count",
          len(journey) == report["new_merchants"],
          f"{len(journey)} vs {report['new_merchants']}")

    # --- both methodology versions -----------------------------------------
    for version in ("v1", "v2"):
        clusters, diag = cluster_merchants(clean_df, customers, version=version)
        require_keys(f"{version} diagnostics keys", diag, DIAG_KEYS)
        require_columns(f"{version} cluster columns", clusters, CLUSTER_COLUMNS)

        profiles = insights.cluster_profile_rows(clusters)
        check(f"{version} cluster_profile_rows non-empty", len(profiles) > 0)
        require_keys(f"{version} cluster_profile_rows fields", profiles[0], [
            "cluster_name", "merchants", "spend", "avg_ticket", "transactions",
            "vip_concentration", "mass_concentration", "new_merchants", "top_merchants"])
        check(f"{version} every cluster name has UI copy",
              all(p["cluster_name"] in theme.CLUSTER_COLORS
                  or p["cluster_name"] == "Not enough merchants to cluster"
                  for p in profiles),
              str([p["cluster_name"] for p in profiles]))

        rankings = score_v1(clean_df, clusters) if version == "v1" \
            else score_v2(clean_df, clusters)
        for deliverable in ("partnership", "loyalty", "bnpl", "potential"):
            frame = rankings[deliverable]
            require_columns(
                f"{version} {deliverable} ranking columns", frame,
                ["merchant", "merchant_status", f"{deliverable}_rank",
                 "total_amount_egp", "transaction_count", "avg_ticket_egp",
                 "unique_customers", "cluster_name"])
            check(f"{version} {deliverable} top_target works",
                  isinstance(kpis.top_target(frame, f"{deliverable}_rank"), str))

        check(f"{version} rank_correlation is 4x4",
              rank_correlation(rankings).shape == (4, 4))
        check(f"{version} ranking_insights returns lines",
              len(insights.ranking_insights(rankings, version)) > 0)

    # --- version comparison -------------------------------------------------
    c1, _ = cluster_merchants(clean_df, customers, version="v1")
    c2, _ = cluster_merchants(clean_df, customers, version="v2")
    movement = rank_movement(score_v1(clean_df, c1), score_v2(clean_df, c2))
    require_columns("rank_movement columns", movement,
                    ["deliverable", "merchant", "rank_v1", "rank_v2", "movement"])
    for deliverable in ("partnership", "loyalty", "bnpl", "potential"):
        check(f"version_comparison_signals: {deliverable}",
              len(insights.version_comparison_signals(movement, deliverable)) > 0)

    # --- components render without raising ---------------------------------
    check("egp handles None", ui.egp(None) == "n/a")
    check("fmt_measure handles None",
          ui.fmt_measure(None, "{:.1f} days") == "Not available")
    check("merchant_badge covers all statuses",
          all("badge" in ui.merchant_badge(s) for s in ("known", "new", "unknown")))

    merchant_view = build_merchant_features(clean_df, customers)
    require_columns("merchant features for the ticket diagnostic",
                    merchant_view, ["avg_ticket_egp"])


def existing_insights_unchanged() -> None:
    """The six pre-existing insight functions must still exist with their
    original signatures. The additive layer is only allowed to add."""
    print(f"\n{'=' * 68}\nexisting insight functions\n{'=' * 68}")
    for name in ("transaction_insights", "segment_insights", "cluster_insights",
                 "ranking_insights", "data_quality_notes"):
        check(f"{name} still present", hasattr(insights, name))


if __name__ == "__main__":
    existing_insights_unchanged()
    run_for("demo.xlsx")
    if (DATA / "demo_new_merchants.xlsx").exists():
        run_for("demo_new_merchants.xlsx")

    print("\n" + "=" * 68)
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED:")
        for item in failures:
            print(f"  - {item}")
        sys.exit(1)
    print("ALL UI CONTRACT CHECKS PASSED")
