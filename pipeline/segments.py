"""
Stage 3: Customer RFM segmentation.

Builds one row per card (PAN) from debit transactions, then splits cardholders
into VIP / Mass / Low-Value using percentile cuts on total spend.

Percentiles rather than fixed EGP thresholds is the important design choice:
a fixed cutoff breaks the moment spending baselines shift, while percentiles
adapt to whatever data arrives and keep segment sizes stable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DEBIT = "DEBIT TRANSACTION"

# From the team's segmentation justification: bottom 30% / middle 50% / top 20%.
LOW_VALUE_PERCENTILE = 0.30
VIP_PERCENTILE = 0.80

SEGMENT_COLUMNS = [
    "PAN",
    "segment",
    "recency",
    "frequency",
    "monetary",
    "avg_ticket",
    "unique_merchants",
    "unique_categories",
    "is_international_any",
    "outlier_ratio",
]


def snapshot_date(clean_df: pd.DataFrame) -> pd.Timestamp:
    """The 'today' that recency is measured against.

    Derived from the data (last transaction plus one day) rather than a fixed
    calendar date, so recency stays meaningful on a newly uploaded file.
    """
    return clean_df["Txn date"].max() + pd.Timedelta(days=1)


def build_rfm(clean_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate debit transactions into one behavioural row per card."""
    debit = clean_df[clean_df["DB/CR"] == DEBIT]
    reference_date = snapshot_date(clean_df)

    rfm = (
        debit.groupby("PAN")
        .agg(
            last_purchase=("Txn date", "max"),
            frequency=("Amount", "size"),
            monetary=("Amount", "sum"),
            avg_ticket=("Amount", "mean"),
            unique_merchants=("merchant", "nunique"),
            unique_categories=("category", "nunique"),
            is_international_any=("is_international", "any"),
            outlier_ratio=("is_outlier", "mean"),
        )
        .reset_index()
    )
    rfm["recency"] = (reference_date - rfm["last_purchase"]).dt.days
    rfm["outlier_ratio"] = rfm["outlier_ratio"].round(4)
    return rfm.drop(columns=["last_purchase"])


def assign_segments(rfm: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Cut cardholders into three tiers on total spend.

    qcut over the *rank* of monetary, not monetary itself. Ranking first
    guarantees the exact 30/50/20 split even when many cardholders share the
    same spend total, which plain quantile cuts cannot promise on small files.
    Method carried over from the reference Stage 3 notebook.
    """
    low_cut, vip_cut = rfm["monetary"].quantile([LOW_VALUE_PERCENTILE, VIP_PERCENTILE])

    rfm = rfm.copy()
    rfm["segment"] = pd.qcut(
        rfm["monetary"].rank(method="first"),
        q=[0, LOW_VALUE_PERCENTILE, VIP_PERCENTILE, 1.0],
        labels=["Low-Value", "Mass", "VIP"],
    ).astype(str)

    thresholds = {
        "low_value_cut": float(low_cut),
        "vip_cut": float(vip_cut),
        "snapshot_note": "recency measured from last transaction date + 1 day",
    }
    return rfm, thresholds


def segment_customers(clean_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Run Stage 3. Returns the customer table and the thresholds used."""
    rfm = build_rfm(clean_df)
    segmented, thresholds = assign_segments(rfm)
    segmented = segmented[SEGMENT_COLUMNS].sort_values("PAN").reset_index(drop=True)

    volume = segmented.groupby("segment")["monetary"].sum()
    thresholds["volume_share"] = (volume / volume.sum()).round(4).to_dict()
    thresholds["segment_sizes"] = segmented["segment"].value_counts().to_dict()
    return segmented, thresholds
