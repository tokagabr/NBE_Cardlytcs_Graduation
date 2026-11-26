"""
Stage 2: Merchant clustering.

Aggregates debit transactions to one row per merchant, then groups merchants
with K-Means.

Two feature sets are available:

  v1  the original ten features, reproducing the reference analysis exactly.
      Six of the ten (total spend, transaction count, unique customers, mass
      customer count, mass spend, mass frequency) are all proxies for merchant
      size and are strongly correlated, so after standardisation "how big is
      this merchant" outvotes "how does this merchant behave" six to four.

  v2  size-neutral features. One volume term is kept for context; the rest
      describe shape (ticket size, segment mix, visits per customer). The
      intent is clusters whose names describe behaviour rather than size.

Cluster names are assigned from cluster profiles, never from K-Means IDs.
K-Means numbers its clusters arbitrarily and the numbering changes between
runs on different data, so naming by ID would relabel every cluster on a new
upload. This is carried over from the reference analysis and is the reason
the pipeline survives a new dataset at all.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

DEBIT = "DEBIT TRANSACTION"
RANDOM_STATE = 42
N_INIT = 50
DEFAULT_K = 4

CLUSTER_NAMES = [
    "VIP-Driven High-Value",
    "Mass-Driven High-Reach",
    "Frequent Low-Ticket",
    "High-Ticket Opportunity",
]

# Bank-mandated cluster numbering, used by downstream reporting.
BANK_ID_BY_NAME = {
    "VIP-Driven High-Value": 1,
    "Mass-Driven High-Reach": 2,
    "Frequent Low-Ticket": 3,
    "High-Ticket Opportunity": 4,
}

FEATURE_SETS = {
    "v1": [
        "total_amount_egp",
        "transaction_count",
        "avg_ticket_egp",
        "unique_customers",
        "mass_customer_count",
        "mass_spend_amount",
        "mass_frequency",
        "mass_concentration",
        "avg_ticket_mass",
        "vip_concentration",
    ],
    "v2": [
        "avg_ticket_egp",
        "avg_ticket_mass",
        "mass_concentration",
        "vip_concentration",
        "txns_per_customer",
        "high_ticket_share",
        "total_amount_egp",
    ],
}

# Skewed count/amount features need a log transform before standardisation.
LOG_FEATURES = {
    "total_amount_egp",
    "transaction_count",
    "unique_customers",
    "mass_spend_amount",
    "mass_frequency",
}


def build_merchant_features(clean_df: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """One row per merchant, with spend broken out by customer segment."""
    debit = clean_df[clean_df["DB/CR"] == DEBIT].merge(
        customers[["PAN", "segment"]], on="PAN", how="left"
    )

    core = (
        debit.groupby("merchant")
        .agg(
            total_amount_egp=("Amount", "sum"),
            transaction_count=("Amount", "count"),
            avg_ticket_egp=("Amount", "mean"),
            unique_customers=("PAN", "nunique"),
            high_ticket_share=("is_outlier", "mean"),
        )
        .reset_index()
    )

    by_segment = (
        debit.groupby(["merchant", "segment"])["Amount"]
        .agg(["sum", "count", "nunique"])
        .reset_index()
    )
    by_segment.columns = [
        "merchant",
        "segment",
        "segment_amount",
        "segment_count",
        "segment_customers",
    ]
    wide = by_segment.pivot(index="merchant", columns="segment").fillna(0)
    wide.columns = [
        f"{segment.lower().replace('-', '_')}_{metric}" for metric, segment in wide.columns
    ]
    features = core.merge(wide.reset_index(), on="merchant", how="left")

    for segment in ("mass", "vip", "low_value"):
        for metric, alias in (
            ("segment_amount", "spend_amount"),
            ("segment_count", "frequency"),
            ("segment_customers", "customer_count"),
        ):
            source = f"{segment}_{metric}"
            features[f"{segment}_{alias}"] = (
                features[source] if source in features else 0.0
            )
        features[f"{segment}_concentration"] = (
            features[f"{segment}_spend_amount"] / features["total_amount_egp"]
        ).fillna(0)

    features["avg_ticket_mass"] = (
        features["mass_spend_amount"] / features["mass_frequency"].replace(0, np.nan)
    ).fillna(0)
    features["txns_per_customer"] = (
        features["transaction_count"] / features["unique_customers"].replace(0, np.nan)
    ).fillna(0)

    # merchant_status and category_status travel with the merchant through
    # every downstream stage. New merchants are clustered and scored exactly
    # like known ones: no penalty, no exclusion, no special formula.
    attributes = clean_df.groupby("merchant").agg(
        category=("category", lambda s: s.mode().iloc[0] if not s.mode().empty else "Unknown"),
        category_status=("category_status", lambda s: s.mode().iloc[0] if not s.mode().empty else "Unknown"),
        merchant_status=("merchant_status", lambda s: s.mode().iloc[0] if not s.mode().empty else "unknown"),
        geo_confidence=("geo_confidence", lambda s: s.mode().iloc[0] if not s.mode().empty else "none"),
    )
    return features.merge(attributes, left_on="merchant", right_index=True, how="left")


def _scale(features: pd.DataFrame, feature_names: list[str]) -> np.ndarray:
    matrix = features[feature_names].copy()
    for column in matrix.columns.intersection(LOG_FEATURES):
        matrix[column] = np.log1p(matrix[column])
    return StandardScaler().fit_transform(matrix)


def k_selection_evidence(
    features: pd.DataFrame, version: str = "v1", k_range: range = range(2, 9)
) -> pd.DataFrame:
    """Inertia and silhouette across candidate K, for the elbow chart."""
    matrix = _scale(features, FEATURE_SETS[version])
    rows = []
    for k in k_range:
        model = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=N_INIT).fit(matrix)
        rows.append(
            {
                "k": k,
                "inertia": model.inertia_,
                "silhouette": silhouette_score(matrix, model.labels_),
            }
        )
    return pd.DataFrame(rows)


def name_clusters(profiles: pd.DataFrame) -> dict:
    """Map raw cluster labels to bank-approved names using cluster profiles.

    Each name is claimed by the unclaimed cluster that best fits it, in a fixed
    priority order, so exactly one cluster ends up with each name.
    """
    rules = [
        ("VIP-Driven High-Value", "vip_concentration"),
        ("Mass-Driven High-Reach", "mass_concentration"),
        ("Frequent Low-Ticket", "transaction_count"),
        ("High-Ticket Opportunity", "avg_ticket_egp"),
    ]
    names, claimed = {}, set()
    # With K != 4 the bank's four names cannot cover every cluster. Extra
    # clusters keep a profile-derived label rather than an arbitrary number.
    for name, metric in rules[: min(len(rules), len(profiles))]:
        remaining = profiles[~profiles.index.isin(claimed)]
        if remaining.empty:
            break
        winner = remaining[metric].idxmax()
        names[winner] = name
        claimed.add(winner)

    for cluster in profiles.index:
        if cluster not in names:
            spend_rank = profiles.loc[cluster, "transaction_count"]
            names[cluster] = f"Cluster {cluster} (volume {spend_rank:,.0f})"
    return names


def cluster_merchants(
    clean_df: pd.DataFrame,
    customers: pd.DataFrame,
    version: str = "v1",
    k: int = DEFAULT_K,
) -> tuple[pd.DataFrame, dict]:
    """Run Stage 2. Returns merchant rows with cluster labels, plus diagnostics."""
    features = build_merchant_features(clean_df, customers)
    feature_names = FEATURE_SETS[version]
    matrix = _scale(features, feature_names)

    model = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=N_INIT)
    features["cluster_raw"] = model.fit_predict(matrix)

    profiles = features.groupby("cluster_raw")[
        ["vip_concentration", "mass_concentration", "transaction_count", "avg_ticket_egp"]
    ].mean()
    names = name_clusters(profiles)
    features["cluster_name"] = features["cluster_raw"].map(names)
    features["cluster_id"] = features["cluster_name"].map(BANK_ID_BY_NAME)

    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    coordinates = pca.fit_transform(matrix)
    features["pc1"], features["pc2"] = coordinates[:, 0], coordinates[:, 1]

    diagnostics = {
        "version": version,
        "k": k,
        "features_used": feature_names,
        "silhouette": float(silhouette_score(matrix, features["cluster_raw"])),
        "explained_variance": pca.explained_variance_ratio_.tolist(),
        "merchants": len(features),
        "cluster_sizes": features["cluster_name"].value_counts().to_dict(),
    }
    return features.sort_values(["cluster_id", "total_amount_egp"], ascending=[True, False]), diagnostics
