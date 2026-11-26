"""
Plotly figures for the dashboard.

Presentation only: every function takes a finished pipeline output and draws
it. No figure computes, filters or reshapes anything that affects a result.

Colours come from ui.theme, which is the single source of truth for the whole
application. This module used to declare its own palette, which had drifted
from app.py's (two different inks, two different golds). Segment and cluster
colours still carry the values used in the team's written deck, so the app and
the report stay readable side by side.

Heights come from ui.theme as well, tuned for a 1366x768 laptop.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from ui import theme

INK = theme.NAVY
GOLD = theme.GOLD
BLUE = theme.BLUE
GRAY = theme.GRAY
RULE = theme.RULE
GREEN = theme.GREEN

SEGMENT_COLORS = theme.SEGMENT_COLORS
CLUSTER_COLORS = theme.CLUSTER_COLORS

LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=INK, size=12, family="Urbanist, Inter, system-ui, sans-serif"),
)

# Fixed pixel budget for the band below the plot that holds the x-axis title
# (when there is one) and the legend. Kept as pixels rather than a fraction
# of `height` because legend `y` is a fraction of the *whole figure*: a
# fraction tuned for a 260px chart pushes the legend well past the margin on
# a 640px one. Computing `y` from this constant for the actual height below
# keeps the gap the same regardless of which CHART_* size is used.
# A few charts (pca_scatter, concentration_quadrant) also carry an x-axis
# title in this same band, stacked above the legend, so the budget covers
# both a title line and a legend line rather than just one.
BOTTOM_BAND_PX = 60


def _style(fig: go.Figure, title: str = "", height: int = theme.CHART_MD,
           bottom_band: int = BOTTOM_BAND_PX) -> go.Figure:
    """Apply the house style.

    Axis styling goes through update_xaxes/update_yaxes rather than the layout
    dict, because a layout dict only reaches the first axis of a subplot and
    leaves the others with default gridlines.

    Title stays top-left, in its own reserved band. The legend moves below
    the plot instead of sharing that band: with both up top there was only
    ever room for one line of text before the other overlapped it, since the
    old 34px top margin was one line tall, not two.

    `bottom_band` defaults to BOTTOM_BAND_PX but is overridable per chart.
    Automargin (below) grows the *plot's* margin for long or rotated tick
    labels, but the legend's `y` is a fraction of the whole figure and does
    not know about that growth — a chart whose x-axis labels are long enough
    to rotate (e.g. cluster_profiles' feature names) needs a caller-supplied
    band tall enough for both the rotated labels and the legend beneath them,
    not just the default one-line budget.
    """
    fig.update_layout(
        **LAYOUT, height=height, legend_title_text="",
        margin=dict(l=8, r=20, t=48, b=bottom_band + 10),
        title=dict(text=f"<b>{title}</b>" if title else "",
                   font=dict(size=16, color=INK, family="Urbanist, Inter, system-ui, sans-serif"),
                   x=0, xanchor="left", y=1, yanchor="top", pad=dict(t=4, l=4)),
        legend=dict(orientation="h", yanchor="top", y=-(bottom_band / height),
                    xanchor="center", x=0.5, font=dict(size=12, color=theme.MUTED)),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="rgba(0,112,74,.35)",
                        font=dict(color=INK, size=13, family="Urbanist, Inter, system-ui, sans-serif")),
        bargap=0.3,
    )
    # Rounded bar ends (plotly 6.1+). Older plotly does not know the property,
    # and a missing flourish must never stop a chart from drawing.
    try:
        fig.update_layout(barcornerradius=7)
    except (ValueError, AttributeError):
        pass
    # automargin lets plotly grow the margin beyond the fixed value above
    # when a tick label or axis title actually needs more room — the fixed
    # margin is a floor, not a ceiling, so long merchant/category names on
    # the y-axis of the horizontal bar charts no longer get clipped or drawn
    # over the plot itself.
    # Subplot titles are annotations; give them the same voice as chart titles.
    fig.update_annotations(font=dict(size=14, family="Urbanist, Inter, system-ui, sans-serif"))
    soft = "rgba(11,42,59,0.07)"
    fig.update_xaxes(gridcolor=soft, zeroline=False, linecolor="rgba(11,42,59,0.14)",
                     tickfont=dict(size=12, color=theme.MUTED),
                     title_font=dict(size=12, color=theme.MUTED), automargin=True)
    fig.update_yaxes(gridcolor=soft, zeroline=False, showline=False,
                     tickfont=dict(size=12, color=theme.MUTED),
                     title_font=dict(size=12, color=theme.MUTED), automargin=True)
    return fig


# --- Executive Overview -------------------------------------------------

def spend_by_governorate(df: pd.DataFrame) -> go.Figure:
    data = df.groupby("governorate")["Amount"].sum().sort_values().reset_index()
    fig = px.bar(data, x="Amount", y="governorate", orientation="h",
                 color_discrete_sequence=[GREEN])
    return _style(fig, "Spend by governorate", theme.CHART_LG)


def spend_by_category(df: pd.DataFrame) -> go.Figure:
    data = df.groupby(["category", "DB/CR"])["Amount"].sum().reset_index()
    fig = px.bar(data, x="Amount", y="category", color="DB/CR", orientation="h",
                 color_discrete_sequence=[GREEN, GOLD])
    return _style(fig, "Spend by category, debit against credit", theme.CHART_LG,
                  bottom_band=92)


def spend_volume_trend(df: pd.DataFrame) -> go.Figure:
    monthly = df.groupby("txn_month").agg(
        spend=("Amount", "sum"), transactions=("Amount", "size")
    ).reset_index()
    outlier = df[df["is_outlier"]].groupby("txn_month")["Amount"].sum()
    monthly["outlier_share"] = (
        monthly["txn_month"].map(outlier).fillna(0) / monthly["spend"]
    )

    fig = go.Figure()
    fig.add_bar(x=monthly["txn_month"], y=monthly["spend"], name="Spend", marker_color=GREEN)
    fig.add_scatter(x=monthly["txn_month"], y=monthly["transactions"], name="Transactions",
                    yaxis="y2", line=dict(color=GOLD, width=3))
    fig.add_scatter(x=monthly["txn_month"], y=monthly["outlier_share"] * 100,
                    name="Outlier spend share (%)", yaxis="y2",
                    line=dict(color=BLUE, width=2, dash="dot"))
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False))
    return _style(fig, "Spend and volume trend", theme.CHART_MD)


def gateway_split(df: pd.DataFrame) -> go.Figure:
    data = df.groupby("gateway")["Amount"].sum().reset_index()
    fig = px.pie(data, values="Amount", names="gateway", hole=0.55,
                 color_discrete_sequence=[INK, GOLD, BLUE, "#12A06A", GRAY])
    return _style(fig, "Spend by payment gateway", theme.CHART_SM)


def auth_by_weekday(df: pd.DataFrame) -> go.Figure:
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    data = df.groupby(["day_of_week", "auth_method"]).size().reset_index(name="transactions")
    fig = px.bar(data, x="day_of_week", y="transactions", color="auth_method",
                 barmode="group", category_orders={"day_of_week": order},
                 color_discrete_sequence=[INK, GOLD, BLUE, "#12A06A", GRAY])
    return _style(fig, "Authentication method by day of week", theme.CHART_MD)


# --- Customer Segments --------------------------------------------------

def segment_overview(customers: pd.DataFrame) -> go.Figure:
    from plotly.subplots import make_subplots

    counts = customers["segment"].value_counts().reindex(["Low-Value", "Mass", "VIP"])
    volume = customers.groupby("segment")["monetary"].sum().reindex(["Low-Value", "Mass", "VIP"])
    colors = [SEGMENT_COLORS[s] for s in counts.index]

    fig = make_subplots(rows=1, cols=2, specs=[[{"type": "bar"}, {"type": "pie"}]],
                        subplot_titles=("Cardholders per segment", "Share of spend"))
    fig.add_bar(x=counts.index, y=counts.values, marker_color=colors, showlegend=False, row=1, col=1)
    fig.add_pie(labels=volume.index, values=volume.values,
                marker=dict(colors=colors), hole=0.4, row=1, col=2)
    return _style(fig, "", theme.CHART_MD)


def rfm_distributions(customers: pd.DataFrame) -> go.Figure:
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=3,
                        subplot_titles=("Recency (days)", "Frequency (transactions)",
                                        "Monetary (EGP, log scale)"))
    fig.add_histogram(x=customers["recency"], marker_color=BLUE, nbinsx=40, row=1, col=1)
    fig.add_histogram(x=customers["frequency"], marker_color="#12A06A", nbinsx=40, row=1, col=2)
    fig.add_histogram(x=np.log10(customers["monetary"].clip(lower=1)), marker_color=GOLD,
                      nbinsx=40, row=1, col=3)
    fig.update_xaxes(title_text="log10(EGP)", row=1, col=3)
    fig.update_layout(showlegend=False)
    return _style(fig, "", theme.CHART_SM)


def segment_spend_box(customers: pd.DataFrame) -> go.Figure:
    fig = px.box(customers, x="segment", y="monetary", color="segment",
                 log_y=True, category_orders={"segment": ["Low-Value", "Mass", "VIP"]},
                 color_discrete_map=SEGMENT_COLORS)
    return _style(fig, "Total spend by segment (log scale)", theme.CHART_LG,
                  bottom_band=86)


def recency_monetary_scatter(customers: pd.DataFrame) -> go.Figure:
    fig = px.scatter(customers, x="recency", y="monetary", color="segment",
                     log_y=True, opacity=0.55, color_discrete_map=SEGMENT_COLORS,
                     hover_data=["frequency", "unique_merchants"])
    return _style(fig, "Recency against spend", theme.CHART_LG, bottom_band=86)


def category_by_segment(clean_df: pd.DataFrame, customers: pd.DataFrame) -> go.Figure:
    joined = clean_df.merge(customers[["PAN", "segment"]], on="PAN", how="inner")
    data = joined.groupby(["category", "segment"])["Amount"].sum().reset_index()
    fig = px.bar(data, x="Amount", y="category", color="segment", orientation="h",
                 color_discrete_map=SEGMENT_COLORS)
    return _style(fig, "Category preference by segment", theme.CHART_LG)


# --- Clustering ---------------------------------------------------------

def k_selection(evidence: pd.DataFrame, chosen_k: int) -> go.Figure:
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Inertia (elbow)", "Silhouette score"))
    fig.add_scatter(x=evidence["k"], y=evidence["inertia"], mode="lines+markers",
                    line=dict(color=INK, width=3), showlegend=False, row=1, col=1)
    fig.add_scatter(x=evidence["k"], y=evidence["silhouette"], mode="lines+markers",
                    line=dict(color=GOLD, width=3), showlegend=False, row=1, col=2)
    for col in (1, 2):
        fig.add_vline(x=chosen_k, line=dict(color=BLUE, dash="dash"), row=1, col=col)
    return _style(fig, "", theme.CHART_SM)


def pca_scatter(clusters: pd.DataFrame, variance: list[float]) -> go.Figure:
    fig = px.scatter(clusters, x="pc1", y="pc2", color="cluster_name",
                     hover_name="merchant", size="total_amount_egp", size_max=26,
                     color_discrete_map=CLUSTER_COLORS)
    fig.update_layout(
        xaxis_title=f"PC1 ({variance[0]:.0%} of variance)",
        yaxis_title=f"PC2 ({variance[1]:.0%} of variance)",
    )
    return _style(fig, "Merchants in PCA space", theme.CHART_XL)


def cluster_profiles(clusters: pd.DataFrame, features: list[str]) -> go.Figure:
    summary = clusters.groupby("cluster_name")[features].mean()
    normalized = (summary - summary.min()) / (summary.max() - summary.min() + 1e-9)
    data = normalized.reset_index().melt(id_vars="cluster_name",
                                         var_name="feature", value_name="level")
    fig = px.bar(data, x="feature", y="level", color="cluster_name", barmode="group",
                 color_discrete_map=CLUSTER_COLORS)
    fig.update_layout(yaxis_title="relative level")
    # This axis carries every clustering feature name (up to eleven, several
    # of them long: mass_customer_count, avg_ticket_mass...). Left to
    # Plotly's own choice of angle, that many long labels rotate at a
    # shallow slant tall enough to run into the legend below, since the
    # legend's position is a fixed fraction of the figure and does not grow
    # with the tick labels. Fixing the angle keeps the label band a known
    # height; the taller figure and the wider bottom_band below give both
    # the rotated labels and the legend their own clear space rather than
    # sharing the old one-line budget.
    fig.update_xaxes(tickangle=-35, title_text="")
    return _style(fig, "Average feature level per cluster", 480, bottom_band=150)


def concentration_quadrant(clusters: pd.DataFrame) -> go.Figure:
    fig = px.scatter(clusters, x="mass_concentration", y="vip_concentration",
                     size="total_amount_egp", color="cluster_name", hover_name="merchant",
                     size_max=34, color_discrete_map=CLUSTER_COLORS)
    fig.update_layout(xaxis_title="Mass concentration", yaxis_title="VIP concentration")
    return _style(fig, "Audience concentration", theme.CHART_XL)


# --- Diagnostics --------------------------------------------------------

def ticket_variance(clusters: pd.DataFrame) -> go.Figure:
    data = clusters.sort_values("avg_ticket_egp")
    fig = px.bar(data, x="avg_ticket_egp", y="merchant", orientation="h", color="category",
                 color_discrete_sequence=px.colors.qualitative.Set2)
    mean = data["avg_ticket_egp"].mean()
    fig.add_vline(x=mean, line=dict(color=INK, dash="dash"),
                  annotation_text=f"mean {mean:,.0f} EGP")
    fig.update_layout(showlegend=False)
    return _style(fig, "Average ticket by merchant", 640)


def correlation_heatmap(matrix: pd.DataFrame, title: str) -> go.Figure:
    labels = [c.replace("_rank", "").title() for c in matrix.columns]
    fig = px.imshow(matrix.values, x=labels, y=labels, zmin=0, zmax=1,
                    text_auto=".3f", color_continuous_scale=["#FFFFFF", GOLD, INK])
    return _style(fig, title, theme.CHART_MD)


def rank_movement_chart(movement: pd.DataFrame, deliverable: str) -> go.Figure:
    data = movement[movement["deliverable"] == deliverable].nlargest(20, "movement", keep="all")
    data = pd.concat([data, movement[movement["deliverable"] == deliverable].nsmallest(10, "movement")])
    data = data.drop_duplicates("merchant").sort_values("movement")
    fig = px.bar(data, x="movement", y="merchant", orientation="h",
                 color=data["movement"] > 0,
                 color_discrete_map={True: "#12A06A", False: "#B4553F"})
    fig.update_layout(showlegend=False, xaxis_title="Places gained under v2")
    return _style(fig, f"Biggest rank movements: {deliverable}", theme.CHART_XL)
