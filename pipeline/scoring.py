"""
Stage 4: Merchant scoring and rankings.

Produces four deliverables: partnership targets, loyalty candidates, BNPL
candidates, and an overall potential score.

Two scoring versions run side by side.

v1 reproduces the reference analysis exactly, including three behaviours worth
   naming because they are what v2 exists to address:
     - partnership and loyalty are plain sorts (by spend, by transaction count)
       while BNPL and potential are weighted composites, so the four are not
       methodologically comparable
     - the BNPL formula is 50% total spend + 50% transaction count, which has
       no ticket-size term at all, so the largest supermarkets top a list that
       should surface high-ticket merchants
     - min-max normalisation lets a single extreme merchant compress everyone
       else into the bottom of the range

v2 keeps the same four deliverables but scores them consistently, gives BNPL a
   ticket-size term, measures growth with a half-over-half comparison instead
   of an average of month-over-month percentages, and normalises by percentile
   rank so one outlier cannot flatten a component.

Neither version is "the answer". They are shown together so the effect of each
choice is visible.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEBIT = "DEBIT TRANSACTION"

V1_BNPL_WEIGHTS = {"spend": 0.50, "frequency": 0.50}
V1_POTENTIAL_WEIGHTS = {"spend": 0.25, "reach": 0.25, "growth": 0.25, "strategic": 0.25}

V2_PARTNERSHIP_WEIGHTS = {"spend": 0.40, "reach": 0.30, "strategic": 0.30}
V2_LOYALTY_WEIGHTS = {"frequency": 0.40, "repeat": 0.30, "reach": 0.30}
V2_BNPL_WEIGHTS = {"avg_ticket": 0.40, "high_ticket_share": 0.30, "frequency": 0.30}
V2_POTENTIAL_WEIGHTS = {"spend": 0.25, "reach": 0.25, "growth": 0.25, "strategic": 0.25}


def min_max_score(series: pd.Series) -> pd.Series:
    """Scale to 0-100. Constant input scores a neutral 50 rather than dividing by zero."""
    spread = series.max() - series.min()
    if spread == 0:
        return pd.Series(50.0, index=series.index)
    return (series - series.min()) / spread * 100


def percentile_score(series: pd.Series) -> pd.Series:
    """Scale to 0-100 by rank.

    Unlike min-max, a single extreme value cannot squash the rest of the field
    into a narrow band at the bottom.
    """
    if series.nunique() <= 1:
        return pd.Series(50.0, index=series.index)
    return series.rank(pct=True) * 100


def month_span(clean_df: pd.DataFrame) -> int:
    """Distinct months present, so monthly averages match the file's real range."""
    return max(int(clean_df["txn_month"].nunique()), 1)


def average_mom_growth(monthly: pd.DataFrame) -> pd.Series:
    """v1 growth: mean of month-over-month percentage changes.

    Kept for reproduction. Note this is asymmetric: +100% followed by -50%
    returns spend to its starting value but averages to +25%.
    """
    pivot = monthly.pivot(index="merchant", columns="month", values="Amount").fillna(0)
    growth = {}
    for merchant, row in pivot.iterrows():
        values = row.values
        rates = [
            0 if values[i - 1] == 0 else (values[i] - values[i - 1]) / values[i - 1] * 100
            for i in range(1, len(values))
        ]
        growth[merchant] = float(np.mean(rates)) if rates else 0.0
    return pd.Series(growth, name="growth_raw")


def half_over_half_growth(monthly: pd.DataFrame) -> pd.Series:
    """v2 growth: second half of the period versus first half.

    One comparison over aggregated spend rather than an average of ratios,
    so a single quiet month cannot dominate the result.
    """
    pivot = monthly.pivot(index="merchant", columns="month", values="Amount").fillna(0)
    months = sorted(pivot.columns)
    if len(months) < 2:
        return pd.Series(0.0, index=pivot.index, name="growth_raw")
    midpoint = len(months) // 2
    first = pivot[months[:midpoint]].sum(axis=1)
    second = pivot[months[midpoint:]].sum(axis=1)
    growth = np.where(first > 0, (second - first) / first * 100, 0.0)
    return pd.Series(growth, index=pivot.index, name="growth_raw")


def build_scoring_base(
    clean_df: pd.DataFrame, clusters: pd.DataFrame, version: str = "v1"
) -> pd.DataFrame:
    """Merchant metrics plus the four score components."""
    debit = clean_df[clean_df["DB/CR"] == DEBIT]
    months = month_span(clean_df)

    base = (
        debit.groupby("merchant")
        .agg(
            total_amount_egp=("Amount", "sum"),
            transaction_count=("Amount", "count"),
            unique_customers=("PAN", "nunique"),
            avg_ticket_egp=("Amount", "mean"),
            high_ticket_share=("is_outlier", "mean"),
        )
        .reset_index()
    )
    base["avg_monthly_spend"] = base["total_amount_egp"] / months
    base["avg_monthly_transactions"] = base["transaction_count"] / months
    base["repeat_rate"] = base["transaction_count"] / base["unique_customers"].replace(0, np.nan)
    base["repeat_rate"] = base["repeat_rate"].fillna(0)

    monthly = (
        debit.groupby(["merchant", "txn_month"])["Amount"]
        .sum()
        .reset_index()
        .rename(columns={"txn_month": "month"})
    )
    growth = average_mom_growth(monthly) if version == "v1" else half_over_half_growth(monthly)
    base = base.merge(growth.rename("growth_raw"), left_on="merchant", right_index=True, how="left")
    base["growth_raw"] = base["growth_raw"].fillna(0)

    geography = debit.groupby("merchant").agg(
        unique_governorates=("governorate", "nunique"),
        unique_cities=("city", "nunique"),
    )
    geography["strategic_raw"] = geography["unique_governorates"] * 2 + geography["unique_cities"]
    base = base.merge(geography.reset_index(), on="merchant", how="left")

    base = base.merge(
        clusters[["merchant", "cluster_id", "cluster_name", "merchant_status",
                  "category", "category_status", "geo_confidence",
                  "mass_customer_count", "mass_spend_amount",
                  "mass_concentration", "vip_concentration"]],
        on="merchant",
        how="left",
    )

    scale = min_max_score if version == "v1" else percentile_score
    base["spend_raw"] = base["total_amount_egp"]
    base["reach_raw"] = base["unique_customers"]
    base["spend_norm"] = scale(base["spend_raw"])
    base["reach_norm"] = scale(base["reach_raw"])
    base["growth_norm"] = scale(base["growth_raw"])
    base["strategic_norm"] = scale(base["strategic_raw"])
    base["frequency_norm"] = scale(base["transaction_count"])
    base["ticket_norm"] = scale(base["avg_ticket_egp"])
    base["high_ticket_norm"] = scale(base["high_ticket_share"])
    base["repeat_norm"] = scale(base["repeat_rate"])
    return base


def _rank(frame: pd.DataFrame, sort_by: list[str], ascending: list[bool], rank_name: str) -> pd.DataFrame:
    ranked = frame.sort_values(by=sort_by, ascending=ascending).reset_index(drop=True)
    ranked[rank_name] = ranked.index + 1
    return ranked


def score_v1(clean_df: pd.DataFrame, clusters: pd.DataFrame) -> dict:
    """Reproduce the reference rankings."""
    base = build_scoring_base(clean_df, clusters, version="v1")

    partnership = _rank(
        base.copy(),
        ["total_amount_egp", "avg_monthly_spend", "merchant"],
        [False, False, True],
        "partnership_rank",
    )
    loyalty = _rank(
        base.copy(),
        ["transaction_count", "avg_monthly_transactions", "merchant"],
        [False, False, True],
        "loyalty_rank",
    )

    bnpl = base.copy()
    bnpl["norm_spend"] = bnpl["spend_norm"]
    bnpl["norm_frequency"] = bnpl["frequency_norm"]
    bnpl["bnpl_score"] = (
        V1_BNPL_WEIGHTS["spend"] * bnpl["norm_spend"]
        + V1_BNPL_WEIGHTS["frequency"] * bnpl["norm_frequency"]
    )
    bnpl = _rank(
        bnpl,
        ["bnpl_score", "total_amount_egp", "transaction_count", "merchant"],
        [False, False, False, True],
        "bnpl_rank",
    )

    potential = base.copy()
    potential["potential_score"] = sum(
        weight * potential[f"{component}_norm"]
        for component, weight in V1_POTENTIAL_WEIGHTS.items()
    ).clip(0, 100)
    potential = _rank(
        potential,
        ["potential_score", "total_amount_egp", "merchant"],
        [False, False, True],
        "potential_rank",
    )
    return {"partnership": partnership, "loyalty": loyalty, "bnpl": bnpl, "potential": potential}


def score_v2(clean_df: pd.DataFrame, clusters: pd.DataFrame) -> dict:
    """Corrected scoring: four consistent composites, ticket-aware BNPL."""
    base = build_scoring_base(clean_df, clusters, version="v2")

    partnership = base.copy()
    partnership["partnership_score"] = sum(
        weight * partnership[f"{component}_norm"]
        for component, weight in V2_PARTNERSHIP_WEIGHTS.items()
    )
    partnership = _rank(
        partnership, ["partnership_score", "merchant"], [False, True], "partnership_rank"
    )

    loyalty = base.copy()
    loyalty["loyalty_score"] = sum(
        weight * loyalty[f"{component}_norm"]
        for component, weight in V2_LOYALTY_WEIGHTS.items()
    )
    loyalty = _rank(loyalty, ["loyalty_score", "merchant"], [False, True], "loyalty_rank")

    bnpl = base.copy()
    bnpl["bnpl_score"] = (
        V2_BNPL_WEIGHTS["avg_ticket"] * bnpl["ticket_norm"]
        + V2_BNPL_WEIGHTS["high_ticket_share"] * bnpl["high_ticket_norm"]
        + V2_BNPL_WEIGHTS["frequency"] * bnpl["frequency_norm"]
    )
    bnpl = _rank(bnpl, ["bnpl_score", "avg_ticket_egp", "merchant"], [False, False, True], "bnpl_rank")

    potential = base.copy()
    potential["potential_score"] = sum(
        weight * potential[f"{component}_norm"]
        for component, weight in V2_POTENTIAL_WEIGHTS.items()
    ).clip(0, 100)
    potential = _rank(
        potential, ["potential_score", "total_amount_egp", "merchant"], [False, False, True], "potential_rank"
    )
    return {"partnership": partnership, "loyalty": loyalty, "bnpl": bnpl, "potential": potential}


def rank_movement(v1: dict, v2: dict) -> pd.DataFrame:
    """How far each merchant moved between the two scoring versions."""
    frames = []
    for deliverable in ("partnership", "loyalty", "bnpl", "potential"):
        column = f"{deliverable}_rank"
        merged = v1[deliverable][["merchant", column]].merge(
            v2[deliverable][["merchant", column]], on="merchant", suffixes=("_v1", "_v2")
        )
        merged["deliverable"] = deliverable
        merged["movement"] = merged[f"{column}_v1"] - merged[f"{column}_v2"]
        frames.append(
            merged.rename(columns={f"{column}_v1": "rank_v1", f"{column}_v2": "rank_v2"})[
                ["deliverable", "merchant", "rank_v1", "rank_v2", "movement"]
            ]
        )
    return pd.concat(frames, ignore_index=True)


def rank_correlation(rankings: dict) -> pd.DataFrame:
    """Spearman correlation between the four deliverables.

    If the four rankings correlate near 1.0 they are answering one question,
    not four, which is a property of the data rather than of the formulas.
    """
    merged = None
    for deliverable in ("partnership", "loyalty", "bnpl", "potential"):
        column = f"{deliverable}_rank"
        piece = rankings[deliverable][["merchant", column]]
        merged = piece if merged is None else merged.merge(piece, on="merchant")
    return merged.drop(columns="merchant").corr(method="spearman")
