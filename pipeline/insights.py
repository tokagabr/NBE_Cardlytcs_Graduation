"""
Auto-written insights.

Every sentence is a template filled from the data currently loaded, so a new
upload produces new sentences rather than the ones written for the demo file.
Each rule returns None when its condition does not hold, which keeps the app
from asserting something the data does not support.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import scoring


def _egp(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"EGP {value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"EGP {value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"EGP {value / 1_000:.0f}K"
    return f"EGP {value:,.0f}"


def transaction_insights(df: pd.DataFrame) -> list[str]:
    out = []
    if df.empty:
        return ["No transactions match the current filters."]

    by_category = df.groupby("category")["Amount"].agg(["sum", "size", "mean"])
    top = by_category["sum"].idxmax()
    share = by_category.loc[top, "sum"] / by_category["sum"].sum()
    out.append(
        f"{top} is the largest category at {share:.1%} of spend "
        f"({_egp(by_category.loc[top, 'sum'])} across {int(by_category.loc[top, 'size']):,} transactions)."
    )

    outlier_share = df.loc[df["is_outlier"], "Amount"].sum() / df["Amount"].sum()
    out.append(
        f"Transactions above the outlier threshold are {df['is_outlier'].mean():.1%} of volume "
        f"but {outlier_share:.1%} of spend."
    )

    monthly = df.groupby("txn_month")["Amount"].sum()
    if len(monthly) >= 2:
        change = (monthly.iloc[-1] - monthly.iloc[0]) / monthly.iloc[0]
        direction = "up" if change >= 0 else "down"
        out.append(
            f"Spend moved {direction} {abs(change):.1%} between {monthly.index[0]} "
            f"and {monthly.index[-1]}."
        )

    by_gov = df.groupby("governorate")["Amount"].sum().sort_values(ascending=False)
    if len(by_gov) >= 3:
        out.append(
            f"The top three governorates ({', '.join(by_gov.head(3).index)}) account for "
            f"{by_gov.head(3).sum() / by_gov.sum():.1%} of domestic spend."
        )
    return out


def segment_insights(customers: pd.DataFrame) -> list[str]:
    if customers.empty:
        return ["No cardholders match the current filters."]

    out = []
    volume = customers.groupby("segment")["monetary"].sum()
    counts = customers["segment"].value_counts()
    total = volume.sum()

    if "VIP" in volume:
        out.append(
            f"VIP cardholders are {counts.get('VIP', 0) / len(customers):.0%} of the base "
            f"and drive {volume['VIP'] / total:.0%} of spend ({_egp(volume['VIP'])})."
        )
    if "Low-Value" in volume:
        out.append(
            f"Low-Value cardholders are {counts.get('Low-Value', 0) / len(customers):.0%} of the base "
            f"but contribute {volume['Low-Value'] / total:.0%} of spend."
        )

    profile = customers.groupby("segment")[["recency", "frequency"]].mean()
    if {"VIP", "Low-Value"}.issubset(profile.index):
        out.append(
            f"VIPs return more often (average recency {profile.loc['VIP', 'recency']:.0f} days, "
            f"{profile.loc['VIP', 'frequency']:.0f} transactions) than Low-Value cardholders "
            f"({profile.loc['Low-Value', 'recency']:.0f} days, "
            f"{profile.loc['Low-Value', 'frequency']:.0f} transactions)."
        )
    return out


def cluster_insights(clusters: pd.DataFrame, diagnostics: dict) -> list[str]:
    out = [
        f"K-Means found {diagnostics['k']} clusters across {diagnostics['merchants']} merchants "
        f"with a silhouette score of {diagnostics['silhouette']:.3f}. "
        f"PC1 carries {diagnostics['explained_variance'][0]:.0%} of the variance."
    ]
    if diagnostics["silhouette"] < 0.35:
        out.append(
            "A silhouette below 0.35 means the clusters overlap substantially. "
            "Treat the grouping as a working view, not a hard boundary."
        )
    profile = clusters.groupby("cluster_name").agg(
        merchants=("merchant", "size"),
        spend=("total_amount_egp", "sum"),
        ticket=("avg_ticket_egp", "mean"),
    )
    largest = profile["spend"].idxmax()
    out.append(
        f"{largest} is the largest cluster by spend: {int(profile.loc[largest, 'merchants'])} merchants, "
        f"{_egp(profile.loc[largest, 'spend'])}, average ticket {_egp(profile.loc[largest, 'ticket'])}."
    )
    spread = profile["ticket"].max() - profile["ticket"].min()
    if spread / profile["ticket"].mean() < 0.15:
        out.append(
            f"Average ticket varies by only {_egp(spread)} across clusters, so these groups are "
            "separated by size and audience mix rather than by ticket size."
        )
    return out


def ranking_insights(rankings: dict, version: str) -> list[str]:
    out = []
    correlations = scoring.rank_correlation(rankings)
    values = correlations.to_numpy()
    off_diagonal = values[~np.eye(len(values), dtype=bool)]
    lowest, highest = off_diagonal.min(), off_diagonal.max()
    out.append(
        f"Under {version} scoring the four rankings correlate between {lowest:.2f} and {highest:.2f}."
    )
    if lowest > 0.9:
        out.append(
            "Correlations above 0.90 mean the four deliverables are ordering merchants the same way, "
            "so they are answering one question rather than four."
        )

    bnpl = rankings["bnpl"]
    top = bnpl.head(5)
    out.append(
        f"Top BNPL candidates: {', '.join(top['merchant'])}, "
        f"averaging {_egp(top['avg_ticket_egp'].mean())} per transaction."
    )
    return out


def data_quality_notes(report: dict) -> list[str]:
    """Warnings the user should see before trusting the numbers.

    Reads the report shape produced by clean.clean() after the Phase 1b
    merchant-resolution rework. New and unresolvable merchants are reported
    separately and never combined.
    """
    notes = []
    if report.get("new_merchants"):
        notes.append(
            f"{report['new_merchants']} merchant(s) are not in the reference list. "
            "They are treated as real merchants and included in every stage. "
            "Check their sample descriptions on the Load screen."
        )
    if report.get("unknown_merchants"):
        notes.append(
            f"{report['unknown_rows']:,} row(s) carried no isolatable merchant name. "
            "They count toward transaction totals but not merchant-level analysis."
        )
    if report.get("category_inferred"):
        notes.append(
            f"{report['category_inferred']:,} row(s) have a keyword-inferred category "
            "rather than a reference-mapped one. Treat those category totals as "
            "provisional."
        )
    if report.get("low_confidence_rows"):
        notes.append(
            f"{report['low_confidence_rows']:,} row(s) have low geography confidence: "
            "a city may have stayed attached to the merchant name."
        )
    candidates = report.get("city_candidates")
    if candidates is not None and len(candidates):
        notes.append(
            f"{len(candidates)} possible unrecognised city name(s) detected: "
            + ", ".join(candidates["candidate"].tolist()[:5])
            + ". Add them to reference/cities.csv, or accept them on the Load screen."
        )
    if report["geography_parse_rate"] < 0.95:
        notes.append(
            f"Only {report['geography_parse_rate']:.1%} of domestic descriptions yielded "
            "a governorate. Check the reference vocabularies before trusting the "
            "geographic charts."
        )
    if report["rows_out"] < 5000:
        notes.append(
            f"Only {report['rows_out']:,} rows loaded. Percentile segments and outlier "
            "thresholds get unstable on small files."
        )
    if report["months_covered"] < 3:
        notes.append(
            f"Only {report['months_covered']} month(s) of data. Trend and growth "
            "figures need a longer period to mean anything."
        )
    if report["duplicates_removed"]:
        notes.append(f"{report['duplicates_removed']:,} exact duplicate row(s) were removed.")
    return notes


# =============================================================================
# ADDITIVE LAYER (UI redesign)
#
# Everything below was added to support the "Key Insight / Why it matters"
# presentation. Nothing above this line was modified: the six functions that
# existed before return exactly what they returned before, byte for byte.
#
# These functions READ finished pipeline outputs and phrase them. They compute
# no threshold, fit nothing, and decide nothing about the analysis. Where a
# figure is needed it comes from an existing report, threshold dict, KPI or
# ranking frame. Every one returns [] when its precondition is absent, so a
# file that cannot support a signal simply does not show it.
#
# Return shape: list of {headline, body, style} where style is "", "accent",
# "good" or "warn".
# =============================================================================


def _signal(headline: str, body: str, style: str = "") -> dict:
    return {"headline": headline, "body": body, "style": style}


def executive_signals(df, report: dict, thresholds: dict) -> list[dict]:
    """Key business signals for the Executive Overview.

    Sources, all pre-existing:
      thresholds["volume_share"]   from segments.segment_customers
      report[...]                  from clean.clean
      df                           the filtered transaction table
    """
    signals: list[dict] = []
    if df is None or df.empty:
        return signals

    share = (thresholds or {}).get("volume_share") or {}
    if share.get("VIP") is not None:
        sizes = (thresholds or {}).get("segment_sizes") or {}
        total_customers = sum(sizes.values()) or 0
        vip_pct = (sizes.get("VIP", 0) / total_customers * 100) if total_customers else None
        headline = f"VIP cardholders account for {share['VIP']:.1%} of debit volume"
        body = (
            f"They are {vip_pct:.1f}% of the cardholder base. "
            if vip_pct is not None else ""
        ) + (
            "Concentration this high means partnership and loyalty economics are "
            "driven by a small group, so retention of that group matters more than "
            "broad acquisition."
        )
        signals.append(_signal(headline, body, "accent"))

    if report.get("new_merchants"):
        signals.append(_signal(
            f"{report['new_merchants']} merchant(s) in this file are not in the reference list",
            "They parsed cleanly and are treated as real merchants: categorised where "
            "possible, clustered, and ranked on equal terms. The reference list is a "
            "baseline, not a whitelist.",
            "accent",
        ))

    debit = df[df["DB/CR"] == "DEBIT TRANSACTION"] if "DB/CR" in df.columns else df
    if not debit.empty and "category" in debit.columns:
        by_category = debit.groupby("category")["Amount"].sum().sort_values(ascending=False)
        if len(by_category) >= 2:
            top_share = by_category.iloc[0] / by_category.sum()
            top_three = by_category.head(3).sum() / by_category.sum()
            signals.append(_signal(
                f"{by_category.index[0]} is the largest category at {top_share:.1%} of debit spend",
                f"The top three categories together carry {top_three:.1%}. Category "
                "concentration is where category-level partnership terms would have "
                "the most leverage.",
            ))

    if not debit.empty and "merchant" in debit.columns:
        by_merchant = debit.groupby("merchant")["Amount"].sum().sort_values(ascending=False)
        if len(by_merchant) >= 5:
            top5 = by_merchant.head(5).sum() / by_merchant.sum()
            signals.append(_signal(
                f"The top 5 merchants carry {top5:.1%} of debit spend",
                f"Led by {by_merchant.index[0]} at {_egp(by_merchant.iloc[0])}. "
                "A small number of counterparties dominate the volume available to "
                "negotiate against.",
            ))

    if report.get("outliers_flagged") and report.get("rows_out"):
        pct = report["outliers_flagged"] / report["rows_out"]
        signals.append(_signal(
            f"{report['outliers_flagged']:,} transactions ({pct:.1%}) are high-value outliers",
            f"The threshold, {_egp(report['outlier_threshold'])}, is recomputed from "
            "this file rather than inherited. High-value transactions are the "
            "population BNPL targeting is interested in.",
        ))

    return signals


def segment_interpretation(customers) -> list[dict]:
    """Per-segment description, phrased strictly from the measured values.

    Deliberately descriptive rather than prescriptive: it reports what the
    metrics are, and does not assert a business claim the data cannot support.
    """
    out: list[dict] = []
    if customers is None or customers.empty or "segment" not in customers.columns:
        return out

    total_monetary = customers["monetary"].sum()
    total_customers = len(customers)

    for name in ("VIP", "Mass", "Low-Value"):
        group = customers[customers["segment"] == name]
        if group.empty:
            continue
        out.append({
            "segment": name,
            "customers": int(len(group)),
            "customer_share": len(group) / total_customers if total_customers else 0.0,
            "spend": float(group["monetary"].sum()),
            "spend_share": float(group["monetary"].sum() / total_monetary)
            if total_monetary else 0.0,
            "avg_monetary": float(group["monetary"].mean()),
            "avg_frequency": float(group["frequency"].mean()),
            "avg_recency": float(group["recency"].mean()),
            "avg_ticket": float(group["avg_ticket"].mean()),
            "outlier_ratio": float(group["outlier_ratio"].mean())
            if "outlier_ratio" in group.columns else None,
            "merchants": float(group["unique_merchants"].mean())
            if "unique_merchants" in group.columns else None,
        })
    return out


def segment_business_summary(customers) -> list[dict]:
    """Comparative reading of the segment table. Description, not prescription."""
    rows = segment_interpretation(customers)
    if len(rows) < 2:
        return []
    by_name = {r["segment"]: r for r in rows}
    out: list[dict] = []

    vip, low = by_name.get("VIP"), by_name.get("Low-Value")
    if vip and low:
        out.append(_signal(
            f"VIP is {vip['customer_share']:.1%} of cardholders and "
            f"{vip['spend_share']:.1%} of spend",
            f"Low-Value is {low['customer_share']:.1%} of cardholders and "
            f"{low['spend_share']:.1%} of spend. The tiers are cut on spend "
            "percentiles, so this gap is by construction; what is not by "
            "construction is how far the other metrics separate with it.",
            "accent",
        ))
        out.append(_signal(
            f"VIP transacts {vip['avg_frequency']:.0f} times on average against "
            f"{low['avg_frequency']:.0f} for Low-Value",
            f"Recency separates too: {vip['avg_recency']:.0f} days since last "
            f"purchase against {low['avg_recency']:.0f}. Segments cut on spend "
            "alone that also separate on frequency and recency behave like "
            "genuine tiers rather than arbitrary bins.",
            "good",
        ))

    mass = by_name.get("Mass")
    if mass:
        out.append(_signal(
            f"Mass is the reach tier: {mass['customers']:,} cardholders, "
            f"{mass['spend_share']:.1%} of spend",
            f"Average spend per cardholder is {_egp(mass['avg_monetary'])} against "
            f"{_egp(by_name['VIP']['avg_monetary'])} for VIP."
            if "VIP" in by_name else
            f"Average spend per cardholder is {_egp(mass['avg_monetary'])}.",
        ))
    return out


def cluster_profile_rows(clusters) -> list[dict]:
    """Per-cluster figures for the cluster cards. Aggregation only."""
    if clusters is None or clusters.empty or "cluster_name" not in clusters.columns:
        return []
    rows = []
    for name, group in clusters.groupby("cluster_name"):
        rows.append({
            "cluster_name": name,
            "merchants": int(len(group)),
            "spend": float(group["total_amount_egp"].sum()),
            "avg_ticket": float(group["avg_ticket_egp"].mean()),
            "transactions": int(group["transaction_count"].sum()),
            "customers": int(group["unique_customers"].sum()),
            "vip_concentration": float(group["vip_concentration"].mean())
            if "vip_concentration" in group.columns else None,
            "mass_concentration": float(group["mass_concentration"].mean())
            if "mass_concentration" in group.columns else None,
            "new_merchants": int((group["merchant_status"] == "new").sum())
            if "merchant_status" in group.columns else 0,
            "top_merchants": group.sort_values("total_amount_egp", ascending=False)
            ["merchant"].head(4).tolist(),
        })
    return sorted(rows, key=lambda r: r["spend"], reverse=True)


def version_comparison_signals(movement, deliverable: str) -> list[dict]:
    """Read a rank_movement frame for one deliverable.

    Uses only scoring.rank_movement output. No new statistic is computed:
    mean absolute movement and the largest mover are summaries of that frame.
    """
    if movement is None or len(movement) == 0:
        return []
    subset = movement[movement["deliverable"] == deliverable]
    if subset.empty:
        return []

    mean_shift = subset["movement"].abs().mean()
    unchanged = int((subset["movement"] == 0).sum())
    biggest = subset.loc[subset["movement"].abs().idxmax()]

    signals = [_signal(
        f"Merchants move {mean_shift:.1f} places on average between V1 and V2 "
        f"for this deliverable",
        f"{unchanged} of {len(subset)} merchants hold the same rank. A large "
        "average movement means the two methodologies genuinely disagree here; "
        "a small one means the change is cosmetic for this deliverable.",
        "accent" if mean_shift >= 5 else "",
    )]
    if abs(biggest["movement"]) > 0:
        direction = "up" if biggest["movement"] > 0 else "down"
        signals.append(_signal(
            f"{biggest['merchant']} moves {abs(int(biggest['movement']))} places "
            f"{direction} under V2",
            f"V1 rank {int(biggest['rank_v1'])}, V2 rank {int(biggest['rank_v2'])}. "
            "Positive movement means a merchant ranked worse under V1 and better "
            "under V2.",
        ))
    return signals


def new_merchant_journey(report: dict, clusters, rankings: dict | None) -> list[dict]:
    """Trace each new merchant through resolution, clustering and ranking.

    Reads the new-merchant table from clean.clean(), the clustering output and
    the ranking frames. Nothing is inferred: if a merchant is absent from a
    stage's output, that is reported as absent rather than assumed.
    """
    table = report.get("new_merchant_table")
    if table is None or table.empty:
        return []

    out = []
    for _, row in table.iterrows():
        merchant = row["merchant"]
        entry = {
            "merchant": merchant,
            "category": row["category"],
            "category_status": row["category_status"],
            "geo_confidence": row["geo_confidence"],
            "transactions": int(row["transactions"]),
            "spend": float(row["total_spend"]),
            "cluster_name": None,
            "ranks": {},
        }
        if clusters is not None and not clusters.empty:
            match = clusters[clusters["merchant"] == merchant]
            if not match.empty:
                entry["cluster_name"] = match.iloc[0]["cluster_name"]
        if rankings:
            for deliverable, frame in rankings.items():
                column = f"{deliverable}_rank"
                if column in frame.columns:
                    match = frame[frame["merchant"] == merchant]
                    if not match.empty:
                        entry["ranks"][deliverable] = (
                            int(match.iloc[0][column]), int(len(frame))
                        )
        out.append(entry)
    return out
