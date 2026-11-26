"""
Dashboard measures, translated one-for-one from the Power BI DAX.

Each function names the DAX measure it reproduces. Two inconsistencies are
inherited deliberately, because changing them silently would make the app
disagree with the existing dashboard:

  Total Spend covers every row, credits included, while Stages 2 and 4 filter
  to debit only. The Executive Overview total therefore exceeds the sum of the
  merchant rankings.

  Average Ticket Size is spend divided by transactions across all rows. Avg
  Ticket is the mean of per-customer means, debit only. Both are labelled
  clearly rather than reconciled.
"""

from __future__ import annotations

import pandas as pd

DEBIT = "DEBIT TRANSACTION"


# --- Executive Overview -------------------------------------------------

def total_spend(df: pd.DataFrame) -> float:
    """DAX: SUM('nbe_merchants_clean'[Amount])"""
    return float(df["Amount"].sum())


def total_transactions(df: pd.DataFrame) -> int:
    """DAX: COUNTROWS('nbe_merchants_clean')"""
    return int(len(df))


def unique_customers(df: pd.DataFrame) -> int:
    """DAX: DISTINCTCOUNT('nbe_merchants_clean'[PAN])"""
    return int(df["PAN"].nunique())


def active_merchants(df: pd.DataFrame) -> int:
    """DAX: DISTINCTCOUNT('nbe_merchants_clean'[merchant])"""
    return int(df["merchant"].nunique())


def average_ticket_size(df: pd.DataFrame) -> float:
    """DAX: DIVIDE([Total Spend], [Total Transactions], 0)"""
    return float(df["Amount"].sum() / len(df)) if len(df) else 0.0


def avg_settlement_lag(df: pd.DataFrame) -> float | None:
    """DAX: AVERAGEX(table, DATEDIFF([Txn date], [Posting Date], DAY))

    Returns None, not NaN, when the lag cannot be computed at all: either the
    file had no `Posting Date` column (Stage 0 creates it empty rather than
    blocking) or no row has both dates. The caller decides how to present an
    unavailable measure; a bare NaN rendered straight to the screen as
    "nan days" is not a presentation decision.

    The methodology is unchanged where the data exists. `.mean()` skips missing
    pairs exactly as before, so a file with partial posting dates returns the
    same average over the rows that have them.
    """
    if "Posting Date" not in df.columns or not len(df):
        return None
    posting = pd.to_datetime(df["Posting Date"], errors="coerce")
    txn = pd.to_datetime(df["Txn date"], errors="coerce")
    lag = (posting - txn).dt.days
    if not lag.notna().any():
        return None
    return float(lag.mean())


def outlier_spend_ratio(df: pd.DataFrame) -> float:
    """DAX: DIVIDE(CALCULATE([Total Spend], [is_outlier] = 1), [Total Spend], 0)"""
    total = df["Amount"].sum()
    if total == 0:
        return 0.0
    return float(df.loc[df["is_outlier"], "Amount"].sum() / total)


# --- Customer Segments --------------------------------------------------

def segment_cardholders(customers: pd.DataFrame) -> int:
    """DAX: COUNTROWS(customer_segments)"""
    return int(len(customers))


def avg_recency(customers: pd.DataFrame) -> float:
    """DAX: AVERAGE(customer_segments[recency])"""
    return float(customers["recency"].mean()) if len(customers) else 0.0


def avg_frequency(customers: pd.DataFrame) -> float:
    """DAX: AVERAGE(customer_segments[frequency])"""
    return float(customers["frequency"].mean()) if len(customers) else 0.0


def avg_ticket(customers: pd.DataFrame) -> float:
    """DAX: AVERAGE(customer_segments[avg_ticket])

    A mean of per-customer means, so a 3-transaction cardholder counts as much
    as a 90-transaction one. Distinct from Average Ticket Size above.
    """
    return float(customers["avg_ticket"].mean()) if len(customers) else 0.0


# --- Merchant Clustering ------------------------------------------------

def cluster_spend(clusters: pd.DataFrame) -> float:
    """DAX: SUM(merchant_clusters[total_amount_egp])"""
    return float(clusters["total_amount_egp"].sum())


def active_merchants_in_cluster(clusters: pd.DataFrame) -> int:
    """DAX: DISTINCTCOUNT('merchant_clusters'[merchant])"""
    return int(clusters["merchant"].nunique())


def avg_vip_concentration(clusters: pd.DataFrame) -> float:
    """DAX: AVERAGE('merchant_clusters'[vip_concentration])

    Unweighted across merchants: a 360-transaction merchant counts the same as
    a 2,700-transaction one.
    """
    return float(clusters["vip_concentration"].mean()) if len(clusters) else 0.0


def avg_mass_concentration(clusters: pd.DataFrame) -> float:
    """DAX: AVERAGE('merchant_clusters'[mass_concentration])"""
    return float(clusters["mass_concentration"].mean()) if len(clusters) else 0.0


# --- Strategic Rankings -------------------------------------------------

def top_target(ranking: pd.DataFrame, rank_column: str, recompute: bool = False) -> str:
    """DAX: CALCULATE(SELECTEDVALUE([merchant]), [rank] = 1)

    The DAX picks the merchant whose stored rank is 1, so filtering to a
    category the leader is absent from leaves the card empty. Pass
    recompute=True for the v2 behaviour, which takes the best-ranked merchant
    still present after filtering.
    """
    if ranking.empty:
        return "No merchant in view"
    if recompute:
        return str(ranking.sort_values(rank_column).iloc[0]["merchant"])
    match = ranking[ranking[rank_column] == 1]
    return str(match.iloc[0]["merchant"]) if len(match) else "No rank-1 merchant in view"


def executive_kpis(df: pd.DataFrame) -> dict:
    return {
        "Total spend": total_spend(df),
        "Transactions": total_transactions(df),
        "Unique cardholders": unique_customers(df),
        "Active merchants": active_merchants(df),
        "Average ticket": average_ticket_size(df),
        "Settlement lag (days)": avg_settlement_lag(df),
        "Outlier spend share": outlier_spend_ratio(df),
    }


def segment_kpis(customers: pd.DataFrame) -> dict:
    return {
        "Cardholders": segment_cardholders(customers),
        "Average recency (days)": avg_recency(customers),
        "Average frequency": avg_frequency(customers),
        "Average ticket": avg_ticket(customers),
    }
