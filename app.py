"""
NBE Cardlytics, Project B merchant insight platform.

Run with:  streamlit run app.py

This file is the user interface only. It performs no analysis of its own:
every number on screen comes from a function in pipeline/. That separation
keeps the analysis testable on its own and means the interface can change
without any risk to the methodology.

Presentation primitives live in ui/theme.py (colour, type, spacing) and
ui/components.py (cards, badges, headers). This module composes them into
screens and wires them to pipeline outputs.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from pipeline import charts, insights, kpis, loader
from pipeline.clean import Vocabulary, clean
from pipeline.clustering import FEATURE_SETS, build_merchant_features, cluster_merchants
from pipeline.scoring import (
    V1_BNPL_WEIGHTS, V1_POTENTIAL_WEIGHTS, V2_BNPL_WEIGHTS, V2_LOYALTY_WEIGHTS,
    V2_PARTNERSHIP_WEIGHTS, V2_POTENTIAL_WEIGHTS, rank_correlation, rank_movement,
    score_v1, score_v2,
)
from pipeline.segments import segment_customers
from pipeline.standardize import cleaning_summary
from ui import components as ui
from ui import hero
from ui import theme

APP_DIR = Path(__file__).resolve().parent
# Overridable so the app can be driven against a small sample in tests.
DEMO_FILE = Path(os.environ.get("NBE_DEMO_FILE", APP_DIR / "data" / "demo.xlsx"))
# Same data plus three merchants absent from the reference list, so the
# new-merchant path can be demonstrated. The reference file is never modified.
DEMO_NEW_FILE = APP_DIR / "data" / "demo_new_merchants.xlsx"

LOGO_FILE = APP_DIR / "assets" / "nbe_logo.png"
CO_BRAND_LOGO_FILE = APP_DIR / "assets" / "digital_egypt_logo.png"

st.set_page_config(
    page_title="NBE Cardlytics - Merchant Intelligence",
    layout="wide",
    initial_sidebar_state="auto",   # collapsed on phones, open on desktop
)
st.markdown(theme.css(), unsafe_allow_html=True)
st.markdown(theme.css_v2(), unsafe_allow_html=True)
st.markdown(theme.css_v3(), unsafe_allow_html=True)

if LOGO_FILE.exists():
    st.logo(str(LOGO_FILE), size="large")


# --- navigation model -------------------------------------------------------
# The label carries the screen name; the journey strip carries the workflow
# story. Both are defined once here so they cannot drift apart.

SCREENS = [
    ("1  Load", "Upload data"),
    ("2  Data Quality", "Validate & clean"),
    ("3  Executive Overview", "Understand the landscape"),
    ("4  Customer Segments", "Understand customers"),
    ("5  Merchant Clustering", "Understand merchants"),
    ("6  Strategic Rankings", "Identify opportunities"),
    ("7  Methodology", "Understand the method"),
]
JOURNEY = [step for _, step in SCREENS]
SCREEN_NAMES = [name for name, _ in SCREENS]

VERSION_COPY = {
    "v1": (
        "V1 Baseline",
        "The methodology the team originally submitted, reproduced exactly. "
        "Partnership and Loyalty are plain sorts; BNPL is 50% spend + 50% "
        "frequency with no ticket-size term; min-max normalisation.",
    ),
    "v2": (
        "V2 Enhanced",
        "A diagnostic comparison, not a replacement. All four deliverables become "
        "consistent weighted composites, BNPL gains a ticket-size term, "
        "normalisation moves to percentile rank and growth to half-over-half.",
    ),
}

CLUSTER_MEANING = {
    "VIP-Driven High-Value": "Spend concentrated in the VIP tier. Fewer, larger relationships.",
    "Mass-Driven High-Reach": "Spend spread across the Mass tier. Breadth rather than depth.",
    "Frequent Low-Ticket": "High transaction counts at small ticket sizes. Everyday spend.",
    "High-Ticket Opportunity": "Larger average tickets relative to their volume.",
    "Not enough merchants to cluster": "Too few merchants in view to form clusters.",
}

DELIVERABLES = {
    "partnership": ("Partnership", "Which merchants carry enough volume to negotiate against."),
    "loyalty": ("Loyalty", "Which merchants reach the most cardholders, most often."),
    "bnpl": ("BNPL", "Which merchants suit instalment offers."),
    "potential": ("Potential Growth", "Which merchants combine scale, reach, growth and spread."),
}

SEGMENT_MEANING = {
    "VIP": "Top spend percentile. Highest frequency, most recent activity.",
    "Mass": "Middle band by spend. The broad, high-reach base.",
    "Low-Value": "Bottom spend percentile. Lowest monetary contribution.",
}


# --- pipeline wrappers, cached so a rerun does not re-parse 100k rows --------

@st.cache_data(show_spinner=False)
def run_clean(raw: pd.DataFrame, learn_geography: bool):
    # deduplicate=False: Stage 0 already removed exact duplicates, judged
    # across every column the file supplied rather than the reduced set.
    return clean(raw, Vocabulary(), learn_geography=learn_geography, deduplicate=False)


@st.cache_data(show_spinner=False)
def run_standardize(raw: pd.DataFrame):
    """Stage 0. Maps columns and parses values before any analysis runs."""
    return loader.prepare(raw)


@st.cache_data(show_spinner=False)
def run_segments(clean_df: pd.DataFrame):
    return segment_customers(clean_df)


@st.cache_data(show_spinner=False)
def run_clusters(clean_df: pd.DataFrame, customers: pd.DataFrame, version: str):
    return cluster_merchants(clean_df, customers, version=version)


@st.cache_data(show_spinner=False)
def run_scoring(clean_df: pd.DataFrame, clusters: pd.DataFrame, version: str):
    return score_v1(clean_df, clusters) if version == "v1" else score_v2(clean_df, clusters)


@st.cache_data(show_spinner=False)
def read_demo(path: str) -> pd.DataFrame:
    return loader.read_any(path)


egp = ui.egp
fmt_measure = ui.fmt_measure


def ticket_diagnostic(merchant_df: pd.DataFrame) -> dict:
    """Mean, standard deviation and spread of average ticket size across the
    merchants currently in view. Computed fresh from this file every run, per
    the locked instruction not to hard-code the reference dataset's numbers:
    the ~8% spread noted in the handoff is a property of that specific file,
    not a constant to assume for every upload."""
    ticket = merchant_df["avg_ticket_egp"]
    mean = float(ticket.mean()) if len(ticket) else 0.0
    std = float(ticket.std()) if len(ticket) > 1 else 0.0
    spread = std / mean if mean else 0.0
    return {"mean": mean, "std": std, "spread": spread}


def safe_cluster(filtered: pd.DataFrame, customers: pd.DataFrame, version: str, k: int = 4):
    """Run clustering, guarding the one way K-Means can crash here: fewer
    merchants in view than clusters requested. This happens easily once a
    filter (merchant status = New, a narrow category, ...) narrows the view.
    Falls back to the unclustered feature table rather than raising, so
    Strategic Rankings can still score whatever merchants remain."""
    n_merchants = filtered["merchant"].nunique()
    if n_merchants <= k:
        features = build_merchant_features(filtered, customers)
        features["cluster_raw"] = None
        features["cluster_name"] = "Not enough merchants to cluster"
        features["cluster_id"] = None
        features["pc1"] = 0.0
        features["pc2"] = 0.0
        diagnostics = {
            "version": version, "k": k, "features_used": FEATURE_SETS[version],
            "silhouette": None, "explained_variance": [0.0, 0.0],
            "merchants": int(n_merchants), "cluster_sizes": {}, "insufficient": True,
        }
        return features, diagnostics
    clusters, diagnostics = run_clusters(filtered, customers, version)
    diagnostics = dict(diagnostics, insufficient=False)
    return clusters, diagnostics


def active_version() -> str:
    """The single global V1/V2 selection.

    Previously this lived in three separate radios with three session keys, so
    a user could be on V1 in clustering and V2 in rankings without being told.
    One key now drives every screen. V1 remains the default.
    """
    return st.session_state.get("methodology_version", "v1")


def version_banner() -> None:
    label, description = VERSION_COPY[active_version()]
    ui.insight(label, description, kicker="Analysis method",
               style="good" if active_version() == "v1" else "accent")


def new_merchants_only(filtered: pd.DataFrame, key: str) -> pd.DataFrame:
    """Optional view restricted to merchants absent from the reference list.

    A convenience lens, not a judgement: new merchants are already included
    everywhere by default. Returns the frame unchanged when the box is off, and
    warns rather than silently showing nothing when there are none.
    """
    if not st.checkbox("New merchants only", key=key,
                       help="Show only merchants that are not in the reference list. "
                            "They are included in every ranking either way."):
        return filtered
    subset = filtered[filtered["merchant_status"] == "new"]
    if subset.empty:
        st.warning("No new merchants in the current view. Showing all merchants instead.")
        return filtered
    ui.note(
        f"Restricted to {subset['merchant'].nunique()} new merchant(s), "
        f"{len(subset):,} transactions."
    )
    return subset


# =============================================================================
# Screen 1: Load
# =============================================================================

def screen_load() -> None:
    # The hero is always shown (it used to render only before the first load,
    # so it vanished when you came back to try the other demo). The green
    # "Start your analysis" banner is removed here: that banner style now
    # begins on the Data Quality screen.
    # How far (px) the upload box is pulled up into the hero. If the box sits
    # too high or too low under the "Upload a file here" hint, change this one
    # number: bigger = higher, smaller = lower.
    HERO_UPLOAD_PULL = 185
    st.markdown(
        "<style>"
        'div[class*="st-key-nbe-hero-upload"]{position:relative;z-index:5;'
        f"max-width:44%;margin-top:-{HERO_UPLOAD_PULL}px}}"
        ".nbe-upload-hint{font-weight:800;color:#00704A;margin:0 0 6px}"
        "@media(max-width:1100px){"
        'div[class*="st-key-nbe-hero-upload"]{max-width:100%;margin-top:0}}'
        "</style>",
        unsafe_allow_html=True,
    )
    hero.landing_hero()

    # The "Upload a file" label sits directly above the upload box and they
    # move together, so the word is always right above the button.
    with st.container(key="nbe-hero-upload"):
        st.markdown(
            '<div class="nbe-upload-hint">Upload a file here &#8595;</div>',
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader(
            "Transaction export", type=["xlsx", "xlsm", "csv"],
            label_visibility="collapsed",
        )

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        ui.note(
            "Supported formats: .xlsx, .xlsm, .csv. Column names do not have to "
            "match exactly; common variants are mapped automatically."
        )
        with st.expander("What the pipeline needs"):
            st.markdown(
                "**Required** - the analysis cannot run without these:\n\n"
                "`PAN`, `Txn date`, `Amount`, `Description`, `DB/CR`\n\n"
                "**Expected** - created empty with a warning if absent:\n\n"
                "`Posting Date`, `Currency`, `Primary Cardholder Auth Method`\n\n"
                "Dispute columns are detected and removed. Any `merchant` or "
                "`category` column supplied by the file is ignored: the "
                "Description parser stays the source of truth."
            )

    with right:
        ui.section("Demo environment", "no upload needed")
        demo_choice = st.radio(
            "Demo dataset",
            ["Reference dataset", "New merchant scenario"],
            label_visibility="collapsed",
            captions=[
                "The verified dataset. Every merchant resolves to the reference list.",
                "The same data plus merchants absent from that list.",
            ],
            disabled=not DEMO_NEW_FILE.exists(),
        )
        use_demo = st.button("Run demo dataset", type="primary", width="stretch")

    if use_demo:
        st.session_state["source"] = "demo"
        st.session_state["demo_file"] = (
            str(DEMO_NEW_FILE) if demo_choice.startswith("New") else str(DEMO_FILE)
        )
    if uploaded is not None:
        st.session_state["source"] = "upload"
        st.session_state["uploaded"] = uploaded

    source = st.session_state.get("source")
    if source is None:
        st.info("No dataset loaded yet. Upload a file or run the demo.")
        return

    try:
        if source == "demo":
            demo_path = Path(st.session_state.get("demo_file", str(DEMO_FILE)))
            raw = read_demo(str(demo_path))
            filename = demo_path.name
        else:
            raw = loader.read_any(st.session_state["uploaded"])
            filename = st.session_state["uploaded"].name
    except Exception as error:
        st.error(f"Could not read the file. {error}")
        return

    # --- validation ---------------------------------------------------------
    verdict = loader.validate(raw)

    if verdict["status"] == "blocked":
        ui.section("Validation", "blocked")
        if verdict.get("ambiguous"):
            st.error("Two or more columns could fill the same role. The pipeline will not guess.")
            for target, sources in verdict["ambiguous"].items():
                st.write(f"- **{target}** could be: {', '.join(sources)}")
        if verdict["unmapped"]:
            st.error(
                f"{len(verdict['unmapped'])} required column(s) are missing and could not be "
                f"matched to anything in the file: {', '.join(verdict['unmapped'])}"
            )
        a, b = st.columns(2)
        with a:
            st.markdown("**The pipeline needs**")
            st.code("\n".join(verdict["required"]))
        with b:
            st.markdown("**Your file has**")
            st.code("\n".join(verdict["columns"]))
        return

    if verdict["status"] == "mappable":
        ui.section("Validation", "confirm column mapping")
        st.warning("Some column names differ from the expected export. Confirm the matches below.")
        mapping = {}
        for target, suggestion in verdict["suggestions"].items():
            mapping[target] = st.selectbox(
                f"Which column is '{target}'?",
                options=verdict["columns"],
                index=verdict["columns"].index(suggestion),
                key=f"map_{target}",
            )
        if not st.button("Apply column mapping", type="primary"):
            return
        raw = loader.apply_mapping(raw, mapping)

    # --- standardisation (Stage 0) ------------------------------------------
    with st.spinner("Standardising columns and parsing values"):
        standardised, std_report = run_standardize(raw)

    if std_report["status"] == "blocked":
        ui.section("Validation", "blocked")
        st.error("This file cannot be processed:")
        for problem in std_report["errors"]:
            st.write(f"- {problem}")
        ui.note("Nothing was guessed. Fix the file or map the columns manually above.")
        return

    st.session_state["std_report"] = std_report
    st.session_state["filename"] = filename

    # --- cleaning -----------------------------------------------------------
    learn_geography = st.toggle(
        "Accept detected new cities and re-parse",
        value=False,
        help=(
            "Off by default. An unrecognised city stays attached to the merchant name, "
            "which is flagged rather than silently accepted. Turning this on adds "
            "detected cities to the vocabulary and re-parses, which rewrites those "
            "merchant names."
        ),
    )

    with st.spinner("Parsing descriptions and resolving merchants"):
        clean_df, report = run_clean(standardised, learn_geography)

    st.session_state["clean_df"] = clean_df
    st.session_state["report"] = report
    customers, thresholds = run_segments(clean_df)
    st.session_state["customers"] = customers
    st.session_state["thresholds"] = thresholds

    # --- dataset status -----------------------------------------------------
    ui.section("Dataset loaded", filename)
    ui.kpis([
        ("Rows", f"{report['rows_out']:,}",
         f"{std_report['column_count_in']} columns received", ""),
        ("Columns standardised", f"{std_report['column_count_out']}",
         f"{len(std_report['columns_removed'])} removed", ""),
        ("Period", f"{report['months_covered']} months",
         f"{report['date_min']:%b %Y} to {report['date_max']:%b %Y}", ""),
        ("Cardholders", f"{report['cardholders']:,}", "distinct PANs", ""),
        ("Merchants", f"{report['merchants_total']:,}",
         f"{report['known_merchants']} known, {report['new_merchants']} new, "
         f"{report['unknown_merchants']} unresolved",
         "accent" if report["new_merchants"] else ""),
        ("Status", "Ready",
         f"{len(std_report['warnings'])} warning(s)" if std_report["warnings"]
         else "no warnings", "warn" if std_report["warnings"] else "good"),
    ])

    ui.pipeline_stepper([
        ("STANDARDIZE", f"{std_report['column_count_out']} columns", True),
        ("CLEAN", f"{report['rows_out']:,} rows", True),
        ("SEGMENT", f"{len(customers):,} cardholders", True),
        ("CLUSTER", "ready", True),
        ("SCORE", "ready", True),
    ])

    if std_report["warnings"]:
        st.warning(
            f"{len(std_report['warnings'])} item(s) needed attention during "
            "standardisation. Full detail on the Data Quality screen."
        )

    if report["new_merchants"]:
        ui.insight(
            f"{report['new_merchants']} new merchant(s) detected in this file",
            "Parsed cleanly but absent from the reference list. They are resolved, "
            "categorised where possible, clustered and ranked exactly like known "
            "merchants. See the Data Quality screen for the full trace.",
            kicker="New merchants", style="accent",
        )

    st.success("Dataset ready. Continue to Data Quality, or go straight to Executive Overview.")


# =============================================================================
# Screen 2: Data Quality and Preparation
# =============================================================================

def screen_cleaning() -> None:
    """What the system found in this file, and what it did to it.

    Every figure here is computed from the dataset currently loaded. Nothing on
    this screen is hard-coded to any particular file.
    """
    std_report = st.session_state.get("std_report")
    report = st.session_state.get("report")
    if std_report is None or report is None:
        st.info("Load a dataset on the Load screen first.")
        return

    ui.page_title(
        "Data Quality & Preparation",
        "What the system found in this file, what it cleaned, what it changed, "
        "and what it could not resolve.",
    )

    rows = cleaning_summary(std_report, report)
    warnings = [r for r in rows if r["level"] == "warn"]
    informational = [r for r in rows if r["level"] == "info"]
    passed = [r for r in rows if r["level"] == "ok"]

    ui.kpis([
        ("Rows received", f"{std_report['rows_in']:,}",
         f"{std_report['column_count_in']} columns", ""),
        ("Rows retained", f"{report['rows_out']:,}",
         f"{std_report['duplicates']['removed']:,} duplicates removed", ""),
        ("Columns standardised", f"{std_report['column_count_out']}",
         f"{len(std_report['columns_mapped'])} renamed, "
         f"{len(std_report['columns_removed'])} removed", ""),
        ("Merchants resolved", f"{report['merchants_total']:,}",
         f"{report['known_merchants']} known / {report['new_merchants']} new / "
         f"{report['unknown_merchants']} unresolved",
         "accent" if report["new_merchants"] else ""),
        ("Outliers flagged", f"{report['outliers_flagged']:,}",
         f"above {egp(report['outlier_threshold'])}", ""),
        ("Issues detected", f"{len(warnings)}",
         "needing a human decision" if warnings else "nothing outstanding",
         "warn" if warnings else "good"),
    ])

    ui.section("What happened to this file")

    if warnings:
        st.markdown("**Needs review**")
        for item in warnings:
            ui.status_row(item["step"], item["finding"], item["detail"], "warn")
    if informational:
        st.markdown("**Changes applied**")
        for item in informational:
            ui.status_row(item["step"], item["finding"], item["detail"], "info")
    if passed:
        with st.expander(f"Checks passed ({len(passed)})", expanded=not warnings):
            for item in passed:
                ui.status_row(item["step"], item["finding"], item["detail"], "ok")

    if not warnings:
        st.success(
            "Everything in this file was resolved automatically. No manual "
            "intervention was required."
        )

    # --- new merchants ------------------------------------------------------
    journey_rows = insights.new_merchant_journey(report, None, None)
    if journey_rows:
        ui.section("New merchants detected",
                   "absent from the reference list, included everywhere regardless")
        ui.note(
            "The reference list is a baseline, not a whitelist. A merchant that "
            "parses cleanly but is not on it is 'new', never 'unknown'. Category is "
            "resolved independently, and an inferred category is never presented as "
            "a reference-mapped one."
        )
        columns = st.columns(min(len(journey_rows), 3))
        for index, entry in enumerate(journey_rows):
            with columns[index % len(columns)]:
                honest = entry["category_status"] == "Unknown"
                ui.profile_card(
                    entry["merchant"],
                    f"Category: {entry['category']} ({entry['category_status']})"
                    + (". No keyword matched, so it is reported as Unknown rather "
                       "than guessed." if honest else ""),
                    [
                        ("Status", "New"),
                        ("Geo confidence", str(entry["geo_confidence"]).title()),
                        ("Transactions", f"{entry['transactions']:,}"),
                        ("Spend", egp(entry["spend"])),
                    ],
                    accent=theme.GOLD,
                    badge_html=ui.merchant_badge("new"),
                )
        ui.note(
            "Clustering and ranking status for these merchants appears on the "
            "Merchant Clustering and Strategic Rankings screens."
        )

    # --- detail -------------------------------------------------------------
    ui.section("Detail")
    with st.expander("Column-by-column"):
        before, after = st.columns(2)
        with before:
            st.markdown("**Columns in the uploaded file**")
            st.code("\n".join(str(c) for c in std_report["columns_in"]))
        with after:
            st.markdown("**Standardised columns passed to the pipeline**")
            st.code("\n".join(str(c) for c in std_report["columns_out"]))

        if std_report["columns_mapped"]:
            st.markdown("**Renamed**")
            ui.table(pd.DataFrame(
                list(std_report["columns_mapped"].items()),
                columns=["In the file", "Mapped to"],
            ))
        if std_report["columns_removed"]:
            st.markdown("**Removed**")
            ui.table(pd.DataFrame(
                list(std_report["columns_removed"].items()),
                columns=["Column", "Reason"],
            ))
        if std_report["columns_quarantined"]:
            st.markdown("**Supplied but not trusted**")
            ui.note(
                "These columns duplicate fields the pipeline derives from Description. "
                "They are kept under a 'supplied_' prefix and never used. Description "
                "parsing stays the source of truth."
            )
            st.code("\n".join(str(c) for c in std_report["columns_quarantined"]))

    if report["auto_corrections"]:
        with st.expander(f"Auto-corrected merchant names ({len(report['auto_corrections'])})"):
            ui.note(
                "Merchant names matched onto a reference name above 0.92 similarity. "
                "Deliberately strict, because this rewrites data."
            )
            ui.table(pd.DataFrame(
                list(report["auto_corrections"].items()),
                columns=["Parsed from description", "Corrected to"],
            ))

    if len(report["city_candidates"]):
        with st.expander(f"Possible unrecognised cities ({len(report['city_candidates'])})"):
            ui.note(
                "Trailing tokens that appear after many different merchants. If one is "
                "a real city, it is currently stuck to the merchant name. Accept them "
                "with the toggle on the Load screen, which re-parses and rewrites those "
                "merchant names."
            )
            ui.table(report["city_candidates"])

    if report["unknown_samples"]:
        with st.expander(f"Unresolvable descriptions ({report['unknown_rows']:,} rows)"):
            ui.note(
                "No merchant name could be isolated from these. They count toward "
                "transaction totals but not merchant-level analysis."
            )
            st.code("\n".join(str(s) for s in report["unknown_samples"]))

    st.download_button(
        "Download cleaning report (CSV)",
        pd.DataFrame(rows).to_csv(index=False).encode("utf-8"),
        file_name="cleaning_report.csv",
        mime="text/csv",
    )


# =============================================================================
# Screen 3: Executive Overview
# =============================================================================

def screen_executive(filtered: pd.DataFrame) -> None:
    ui.page_title(
        "Executive Overview",
        "Understand the customer and merchant landscape at a glance.",
    )

    measures = kpis.executive_kpis(filtered)
    ui.kpis([
        ("Total spend", egp(measures["Total spend"]),
         "all transactions, credits included", "accent"),
        ("Transactions", f"{measures['Transactions']:,}", "rows in view", ""),
        ("Cardholders", f"{measures['Unique cardholders']:,}", "distinct PANs", ""),
        ("Active merchants", f"{measures['Active merchants']:,}", "distinct merchants", ""),
        ("Average ticket", egp(measures["Average ticket"]), "spend / transactions", ""),
        ("Settlement lag",
         fmt_measure(measures["Settlement lag (days)"], "{:.1f} days"),
         "txn to posting" if measures["Settlement lag (days)"] is not None
         else "no posting dates in this file", ""),
        ("Outlier spend", f"{measures['Outlier spend share']:.1%}",
         "share of total spend", ""),
    ])
    ui.note(
        "Total spend covers every transaction including credits, matching the "
        "Power BI measure. The merchant rankings use debit only, so the two "
        "totals differ by design."
    )

    ui.section("Where the spend sits")
    a, b = st.columns(2)
    with a:
        st.plotly_chart(charts.spend_by_governorate(filtered), width="stretch")
    with b:
        st.plotly_chart(charts.spend_by_category(filtered), width="stretch")
    st.plotly_chart(charts.spend_volume_trend(filtered), width="stretch")
    with st.expander("Channel and authentication detail"):
        c, d = st.columns([2, 1])
        with c:
            st.plotly_chart(charts.auth_by_weekday(filtered), width="stretch")
        with d:
            st.plotly_chart(charts.gateway_split(filtered), width="stretch")

    signals_col, notes_col = st.columns(2, gap="large")
    with signals_col:
        ui.section("Key business signals", "computed from this file")
        signals = insights.executive_signals(
            filtered, st.session_state["report"], st.session_state.get("thresholds", {})
        )
        if signals:
            for signal in signals:
                ui.insight(signal["headline"], signal["body"], style=signal["style"])
        else:
            ui.note("Not enough data in the current view to surface signals.")

    with notes_col:
        ui.section("What the data shows")
        ui.insight_list(insights.transaction_insights(filtered), kicker="Observation")

    notes = insights.data_quality_notes(st.session_state["report"])
    if notes:
        with st.expander(f"Data quality notes ({len(notes)})"):
            for note_line in notes:
                st.write(f"- {note_line}")


# =============================================================================
# Screen 4: Customer Segments
# =============================================================================

def screen_segments(filtered: pd.DataFrame, filtered_customers: pd.DataFrame) -> None:
    ui.page_title(
        "Customer Segments",
        "Who the cardholders are, and how far the tiers actually separate.",
    )

    if filtered_customers.empty:
        st.warning("No cardholders match the current filters.")
        return

    measures = kpis.segment_kpis(filtered_customers)
    thresholds = st.session_state["thresholds"]
    ui.kpis([
        ("Cardholders", f"{measures['Cardholders']:,}", "in view", ""),
        ("Average recency", f"{measures['Average recency (days)']:.0f} days",
         "since last purchase", ""),
        ("Average frequency", f"{measures['Average frequency']:.0f}",
         "transactions per cardholder", ""),
        ("Average ticket", egp(measures["Average ticket"]),
         "mean of per-cardholder means", "accent"),
    ])
    ui.note(
        "Average ticket here is the mean of per-cardholder averages, so a "
        "3-transaction cardholder counts as much as a 90-transaction one. It is "
        "a different statistic from the Average ticket on the overview screen."
    )

    ui.section("The three tiers", "percentile cuts on total debit spend")
    rows = insights.segment_interpretation(filtered_customers)
    if rows:
        columns = st.columns(len(rows))
        for column, row in zip(columns, rows):
            with column:
                ui.profile_card(
                    row["segment"],
                    SEGMENT_MEANING.get(row["segment"], ""),
                    [
                        ("Cardholders", f"{row['customers']:,}"),
                        ("Share", f"{row['customer_share']:.1%}"),
                        ("Spend", egp(row["spend"])),
                        ("Spend share", f"{row['spend_share']:.1%}"),
                        ("Avg spend", egp(row["avg_monetary"])),
                        ("Avg frequency", f"{row['avg_frequency']:.0f}"),
                        ("Avg recency", f"{row['avg_recency']:.0f} d"),
                        ("Avg ticket", egp(row["avg_ticket"])),
                    ],
                    accent=theme.SEGMENT_COLORS.get(row["segment"]),
                )

    ui.note(
        f"Tiers are percentile cuts on total spend, computed from this file at "
        f"{egp(thresholds['low_value_cut'])} and {egp(thresholds['vip_cut'])}. "
        "Percentiles rather than fixed amounts, so the tiers stay meaningful "
        "when spending baselines shift."
    )

    ui.section("Distribution")
    st.plotly_chart(charts.segment_overview(filtered_customers), width="stretch")
    a, b = st.columns(2)
    with a:
        st.plotly_chart(charts.segment_spend_box(filtered_customers), width="stretch")
    with b:
        st.plotly_chart(charts.recency_monetary_scatter(filtered_customers),
                        width="stretch")

    left, right = st.columns(2, gap="large")
    with left:
        ui.section("Business interpretation", "described, not asserted")
        for signal in insights.segment_business_summary(filtered_customers):
            ui.insight(signal["headline"], signal["body"], style=signal["style"])
    with right:
        ui.section("What the data shows")
        ui.insight_list(insights.segment_insights(filtered_customers), kicker="Observation")

    with st.expander("Detailed distributions"):
        st.plotly_chart(charts.rfm_distributions(filtered_customers), width="stretch")
        st.plotly_chart(charts.category_by_segment(filtered, filtered_customers),
                        width="stretch")


# =============================================================================
# Screen 5: Merchant Clustering
# =============================================================================

def screen_clustering(filtered: pd.DataFrame, customers: pd.DataFrame) -> None:
    ui.page_title(
        "Merchant Clustering",
        "What kind of merchant each one is, grouped by behaviour rather than name.",
    )
    version = active_version()
    version_banner()
    if version == "v1":
        ui.note(
            "V1 clustering uses ten features, six of which are merchant-size proxies. "
            "V2 uses seven size-neutral features. Switch method in the sidebar."
        )
    else:
        ui.note(
            "V2 clustering uses seven size-neutral features so behaviour, not size, "
            "drives the grouping. Cluster names are inherited from V1's naming rules, "
            "so they may fit less closely here."
        )

    filtered = new_merchants_only(filtered, key="cluster_new_only")

    with st.spinner("Clustering merchants"):
        clusters, diag = safe_cluster(filtered, customers, version)

    if diag["insufficient"]:
        st.warning(
            f"Only {diag['merchants']} merchant(s) in the current filter view. K-Means "
            f"needs at least {diag['k']} merchants to form {diag['k']} clusters. Widen "
            "the filters in the sidebar to see clustering."
        )
        if not clusters.empty:
            table = clusters[["merchant", "merchant_status", "total_amount_egp",
                              "transaction_count", "avg_ticket_egp"]].copy()
            table.insert(1, "Status", table.pop("merchant_status").str.title())
            table.columns = ["Merchant", "Status", "Spend (EGP)", "Transactions",
                             "Avg ticket (EGP)"]
            ui.table(table)
        return

    status_counts = clusters["merchant_status"].value_counts()
    ui.kpis([
        ("Active merchants", f"{kpis.active_merchants_in_cluster(clusters):,}",
         f"{status_counts.get('new', 0)} new, {status_counts.get('unknown', 0)} unresolved",
         "accent" if status_counts.get("new", 0) else ""),
        ("Cluster spend", egp(kpis.cluster_spend(clusters)), "debit only, this view", ""),
        ("Avg VIP concentration", f"{kpis.avg_vip_concentration(clusters):.1%}",
         "unweighted across merchants", ""),
        ("Avg Mass concentration", f"{kpis.avg_mass_concentration(clusters):.1%}",
         "unweighted across merchants", ""),
        ("Silhouette", f"{diag['silhouette']:.3f}", f"K={diag['k']}, {version} features",
         "warn" if diag["silhouette"] < 0.35 else "good"),
    ])
    if diag["silhouette"] < 0.35:
        ui.note(
            "A silhouette below 0.35 means the clusters overlap substantially. Treat the "
            "grouping as a working view, not a hard boundary."
        )

    ui.section("Cluster profiles", f"{version} features")
    profiles = insights.cluster_profile_rows(clusters)
    for start in range(0, len(profiles), 2):
        columns = st.columns(2)
        for column, row in zip(columns, profiles[start:start + 2]):
            with column:
                badge = (
                    f'<span class="badge badge-new">{row["new_merchants"]} new</span>'
                    if row["new_merchants"] else ""
                )
                ui.profile_card(
                    row["cluster_name"],
                    CLUSTER_MEANING.get(row["cluster_name"], "")
                    + f" Top: {', '.join(row['top_merchants'])}.",
                    [
                        ("Merchants", f"{row['merchants']}"),
                        ("Spend", egp(row["spend"])),
                        ("Avg ticket", egp(row["avg_ticket"])),
                        ("Transactions", f"{row['transactions']:,}"),
                        ("VIP conc.", f"{row['vip_concentration']:.0%}"
                         if row["vip_concentration"] is not None else "n/a"),
                        ("Mass conc.", f"{row['mass_concentration']:.0%}"
                         if row["mass_concentration"] is not None else "n/a"),
                    ],
                    accent=theme.CLUSTER_COLORS.get(row["cluster_name"], theme.NAVY),
                    badge_html=badge,
                )

    ui.section("Merchants in two dimensions", "PCA projection of the clustering features")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(charts.pca_scatter(clusters, diag["explained_variance"]),
                        width="stretch")
    with right:
        st.plotly_chart(charts.concentration_quadrant(clusters), width="stretch")

    st.plotly_chart(charts.cluster_profiles(clusters, diag["features_used"]),
                    width="stretch")
    ui.section("What the data shows")
    ui.insight_list(insights.cluster_insights(clusters, diag), kicker="Observation")

    new_view = clusters[clusters["merchant_status"] == "new"]
    if not new_view.empty:
        ui.section("New merchants in this view",
                   "clustered on equal terms, no penalty or exclusion")
        ordered_new = new_view.sort_values("total_amount_egp", ascending=False)
        columns = st.columns(min(len(ordered_new), 3))
        for index, (_, row) in enumerate(ordered_new.iterrows()):
            with columns[index % len(columns)]:
                ui.profile_card(
                    row["merchant"], f"Clustered into {row['cluster_name']}",
                    [
                        ("Spend", egp(row["total_amount_egp"])),
                        ("Transactions", f"{int(row['transaction_count']):,}"),
                        ("Avg ticket", egp(row["avg_ticket_egp"])),
                        ("Category", str(row.get("category", "Unknown"))),
                    ],
                    accent=theme.GOLD, badge_html=ui.merchant_badge("new"),
                )

    ui.section("All merchants in this view")
    table = clusters[["merchant", "merchant_status", "cluster_name", "category",
                      "total_amount_egp", "transaction_count", "avg_ticket_egp",
                      "vip_concentration", "mass_concentration"]].copy()
    table = table.sort_values("total_amount_egp", ascending=False)
    table.insert(1, "Status", table.pop("merchant_status").str.title())
    table["total_amount_egp"] = table["total_amount_egp"].map(lambda v: f"{v:,.0f}")
    table["avg_ticket_egp"] = table["avg_ticket_egp"].map(lambda v: f"{v:,.0f}")
    table["vip_concentration"] = table["vip_concentration"].map(lambda v: f"{v:.0%}")
    table["mass_concentration"] = table["mass_concentration"].map(lambda v: f"{v:.0%}")
    table.columns = ["Merchant", "Status", "Cluster", "Category", "Spend (EGP)",
                     "Transactions", "Avg ticket (EGP)", "VIP conc.", "Mass conc."]
    ui.table(table, height=340)


# =============================================================================
# Screen 6: Strategic Rankings
# =============================================================================

def _ranking_reason(row: pd.Series, deliverable: str, version: str) -> str:
    """Describe what drove a merchant's position, from its own score components.

    Reads columns already present in the scoring output. Nothing is recomputed.
    """
    parts = []
    if version == "v1":
        if deliverable == "partnership":
            parts.append(f"spend {egp(row['total_amount_egp'])}")
        elif deliverable == "loyalty":
            parts.append(f"{int(row['transaction_count']):,} transactions")
        elif deliverable == "bnpl":
            if "norm_spend" in row:
                parts.append(f"spend {row['norm_spend']:.0f}/100")
            if "norm_frequency" in row:
                parts.append(f"frequency {row['norm_frequency']:.0f}/100")
        else:
            for key in ("spend", "reach", "growth", "strategic"):
                if f"{key}_norm" in row:
                    parts.append(f"{key} {row[f'{key}_norm']:.0f}")
    else:
        component_map = {
            "partnership": ("spend", "reach", "strategic"),
            "loyalty": ("frequency", "repeat", "reach"),
            "bnpl": ("ticket", "high_ticket", "frequency"),
            "potential": ("spend", "reach", "growth", "strategic"),
        }
        for key in component_map[deliverable]:
            column = f"{key}_norm"
            if column in row:
                parts.append(f"{key.replace('_', ' ')} {row[column]:.0f}")
    if "unique_customers" in row:
        parts.append(f"{int(row['unique_customers']):,} customers")
    return "   ".join(parts)


def screen_rankings(filtered: pd.DataFrame, customers: pd.DataFrame) -> None:
    ui.page_title(
        "Strategic Rankings",
        "Which merchants to act on, and why each one is where it is.",
    )
    version = active_version()
    version_banner()

    filtered = new_merchants_only(filtered, key="ranking_new_only")

    with st.spinner("Clustering and scoring merchants"):
        clusters, diag = safe_cluster(filtered, customers, version)

    if diag["insufficient"]:
        st.warning(
            f"Only {diag['merchants']} merchant(s) in the current filter view. Rankings "
            "need more merchants to be meaningful. Widen the filters in the sidebar."
        )
        return

    rankings = run_scoring(filtered, clusters, version)

    diagnostic = ticket_diagnostic(clusters)
    if diagnostic["spread"] < 0.15:
        st.info(
            f"Average ticket size in this view: mean {egp(diagnostic['mean'])}, spread "
            f"{diagnostic['spread']:.1%} of the mean. That is a narrow spread, so ticket-"
            "size-driven rankings (BNPL in particular) will look close to a volume "
            "ranking. That is a property of this data, not a flaw in the formula."
        )
    else:
        ui.note(
            f"Average ticket size in this view: mean {egp(diagnostic['mean'])}, spread "
            f"{diagnostic['spread']:.1%} of the mean."
        )

    tabs = st.tabs([label for label, _ in DELIVERABLES.values()])
    for tab, (deliverable, (label, question)) in zip(tabs, DELIVERABLES.items()):
        with tab:
            _render_deliverable(
                deliverable, label, question, rankings, version, filtered, customers
            )

    ui.section("Are the four deliverables actually different?")
    correlation = rank_correlation(rankings)
    off_diagonal = correlation.to_numpy()[~np.eye(len(correlation), dtype=bool)]
    st.plotly_chart(
        charts.correlation_heatmap(
            correlation, f"Spearman correlation between the four rankings ({version})"
        ),
        width="stretch",
    )
    if off_diagonal.min() > 0.90:
        st.warning(
            f"Every pair correlates above {off_diagonal.min():.2f}. The four deliverables "
            "are ordering merchants the same way, so they are answering one question "
            "rather than four. On this data that is caused by merchant volume being the "
            "only dimension that varies, not by the formulas."
        )
    else:
        ui.note(
            f"Correlations run from {off_diagonal.min():.2f} to {off_diagonal.max():.2f}. "
            "The further below 1.00, the more genuinely different the four deliverables are."
        )
    ui.insight_list(insights.ranking_insights(rankings, version), kicker="Observation")


def _render_deliverable(deliverable, label, question, rankings, version,
                        filtered, customers) -> None:
    rank_column = f"{deliverable}_rank"
    score_column = f"{deliverable}_score"
    table_all = rankings[deliverable]
    has_score = score_column in table_all.columns

    ui.note(question)

    cells = [
        ("Top target (stored rank 1)",
         kpis.top_target(table_all, rank_column, recompute=False),
         "blank if the rank-1 merchant was filtered out, matching Power BI", ""),
        ("Merchants ranked", f"{len(table_all):,}", "all statuses included", ""),
    ]
    if version == "v2":
        cells.append((
            "Top target (best still in view)",
            kpis.top_target(table_all, rank_column, recompute=True),
            "v2 behaviour: best-ranked merchant among those remaining", "accent",
        ))
    ui.kpis(cells)

    ordered = table_all.sort_values(rank_column)

    ui.section("Top 5", "and what put them there")
    for _, row in ordered.head(5).iterrows():
        ui.rank_row(
            int(row[rank_column]), row["merchant"],
            _ranking_reason(row, deliverable, version),
            "Score" if has_score else "Spend",
            f"{row[score_column]:.1f}" if has_score else egp(row["total_amount_egp"]),
            badge_html=ui.merchant_badge(row["merchant_status"])
            if row["merchant_status"] != "known" else "",
        )

    top25 = ordered.head(25)
    new_in_top = top25[top25["merchant_status"] == "new"]
    if not new_in_top.empty:
        ui.insight(
            f"{len(new_in_top)} new merchant(s) in the top 25: "
            + ", ".join(new_in_top["merchant"].tolist()),
            "New merchants compete on equal terms; nothing excludes or penalises them.",
            kicker="New merchants ranked", style="accent",
        )

    with st.expander(f"Ranks 6 to {min(25, len(ordered))}"):
        columns = ["merchant", "merchant_status", rank_column]
        if has_score:
            columns.append(score_column)
        columns += ["total_amount_egp", "transaction_count", "avg_ticket_egp", "cluster_name"]
        display = ordered[columns].iloc[5:25].copy()
        display.insert(2, "Status", display.pop("merchant_status").str.title())
        display["total_amount_egp"] = display["total_amount_egp"].map(lambda v: f"{v:,.0f}")
        display["avg_ticket_egp"] = display["avg_ticket_egp"].map(lambda v: f"{v:,.0f}")
        header = ["Merchant", "Rank", "Status"]
        if has_score:
            display[score_column] = display[score_column].map(lambda v: f"{v:.1f}")
            header.append("Score")
        header += ["Spend (EGP)", "Transactions", "Avg ticket (EGP)", "Cluster"]
        display.columns = header
        ui.table(display)

    with st.expander(f"Compare V1 and V2 for {label}"):
        other_version = "v2" if version == "v1" else "v1"
        with st.spinner(f"Scoring under {other_version}"):
            other_clusters, other_diag = safe_cluster(filtered, customers, other_version)
        if other_diag["insufficient"]:
            st.info("Not enough merchants in view to compare both versions.")
        else:
            other_rankings = run_scoring(filtered, other_clusters, other_version)
            v1_rankings = rankings if version == "v1" else other_rankings
            v2_rankings = other_rankings if version == "v1" else rankings
            movement = rank_movement(v1_rankings, v2_rankings)
            st.plotly_chart(charts.rank_movement_chart(movement, deliverable),
                            width="stretch")
            for signal in insights.version_comparison_signals(movement, deliverable):
                ui.insight(signal["headline"], signal["body"], style=signal["style"])
            ui.note("Positive movement means a merchant ranked worse under V1 and "
                    "better under V2. Switching method changes scores only; the "
                    "underlying transaction data is identical.")


# =============================================================================
# Screen 7: Methodology and diagnostics
# =============================================================================

def _weights_table(weights: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [(k.replace("_", " ").title(), f"{v:.0%}") for k, v in weights.items()],
        columns=["Component", "Weight"],
    )


def screen_methodology(filtered: pd.DataFrame, customers: pd.DataFrame) -> None:
    """The engineering-review screen.

    Everything here is recomputed from the loaded file. None of the numbers
    quoted about the reference dataset are hard-coded, because they are
    properties of that specific file rather than constants.
    """
    ui.page_title(
        "Methodology & Diagnostics",
        "What was built, why, and what the data can and cannot support.",
    )
    report = st.session_state["report"]
    thresholds = st.session_state["thresholds"]
    std_report = st.session_state["std_report"]

    with st.expander("1 · Data Preparation", expanded=True):
        st.markdown(
            "**In business terms.** A raw card export arrives as one free-text "
            "`Description` field per transaction, packing the payment gateway, the "
            "merchant, the city, the governorate and a reference code into one string. "
            "Stage 0 standardises whatever columns the file happens to use. Stage 1 "
            "takes the description apart and identifies the merchant by subtraction, "
            "removing everything it recognises until only the merchant name is left."
        )
        st.markdown(
            "**Why by subtraction.** A lookup would reject any merchant not already on "
            "the list. Subtraction cannot, which is what makes the reference list a "
            "baseline rather than a whitelist."
        )
        with st.expander("Technical detail"):
            st.markdown(
                f"- Columns resolved in three tiers: exact name, alias table, fuzzy "
                f"match. Ambiguity blocks rather than guesses.\n"
                f"- This file: {std_report['column_count_in']} columns in, "
                f"{std_report['column_count_out']} standardised, "
                f"{len(std_report['columns_removed'])} removed.\n"
                f"- Exact duplicates judged across every supplied column before any is "
                f"dropped: {std_report['duplicates']['removed']:,} removed.\n"
                f"- Merchant close-match cutoff 0.92, deliberately strict because it "
                f"rewrites data."
            )
            ui.table(pd.DataFrame([
                ("Known", report["known_merchants"], f"{report['known_rows']:,}",
                 "matched by name, alias, or close match above 0.92 similarity"),
                ("New", report["new_merchants"], f"{report['new_rows']:,}",
                 "parsed cleanly, absent from the reference list"),
                ("Unresolvable", report["unknown_merchants"], f"{report['unknown_rows']:,}",
                 "no merchant name could be isolated"),
            ], columns=["Status", "Merchants", "Rows", "Meaning"]))

    with st.expander("2 · Customer Segmentation"):
        st.markdown(
            "**In business terms.** Cardholders are split into three tiers by total "
            "debit spend, using percentile cuts rather than fixed amounts so the tiers "
            "stay meaningful if spending baselines shift. The tiers are then checked "
            "against recency and frequency to confirm they behave like real groups "
            "rather than arbitrary bins."
        )
        with st.expander("Technical detail"):
            st.markdown(
                f"- VIP: top 20% of debit spend. Mass: 30th to 80th percentile. "
                f"Low-Value: bottom 30%.\n"
                f"- Cuts from this file: {egp(thresholds['low_value_cut'])} and "
                f"{egp(thresholds['vip_cut'])}.\n"
                f"- Recency snapshot: {thresholds.get('snapshot_note', '')}.\n"
                f"- Filters narrow the customer table; they never reassign segments. "
                f"Recomputing on every filter change would answer a different question "
                f"from the one the Power BI model answers."
            )

    with st.expander("3 · Merchant Clustering"):
        st.markdown(
            "**In business terms.** Merchants are grouped by how they behave, not by "
            "what they sell. K-Means with K=4, and because K-Means numbering is "
            "arbitrary the clusters are named from their own profiles, so the names "
            "stay meaningful when new data arrives."
        )
        with st.expander("Technical detail"):
            st.markdown(
                "- V1: ten features, six of which are merchant-size proxies.\n"
                "- V2: seven size-neutral features.\n"
                "- Features standardised before fitting; volume features log-scaled.\n"
                "- Names describe the profile, not a fixed group of merchants."
            )

    with st.expander("4 · Strategic Scoring"):
        st.markdown(
            "**In business terms.** Four questions are asked of every merchant: who is "
            "worth a partnership, who drives loyalty, who suits BNPL, and who has the "
            "most overall potential."
        )
        left, right = st.columns(2)
        with left:
            st.markdown("**V1 Baseline, as originally submitted**")
            st.write("Clustering: ten features, six of which measure merchant size.")
            st.write("Partnership: plain sort by total spend.")
            st.write("Loyalty: plain sort by transaction count.")
            st.write("BNPL:")
            ui.table(_weights_table(V1_BNPL_WEIGHTS))
            st.write("Potential:")
            ui.table(_weights_table(V1_POTENTIAL_WEIGHTS))
            ui.note("Min-max normalisation. Growth = mean of month-over-month percentages.")
        with right:
            st.markdown("**V2 Enhanced, the diagnostic comparison**")
            st.write("Clustering: seven size-neutral features.")
            st.write("Partnership:")
            ui.table(_weights_table(V2_PARTNERSHIP_WEIGHTS))
            st.write("Loyalty:")
            ui.table(_weights_table(V2_LOYALTY_WEIGHTS))
            st.write("BNPL:")
            ui.table(_weights_table(V2_BNPL_WEIGHTS))
            st.write("Potential:")
            ui.table(_weights_table(V2_POTENTIAL_WEIGHTS))
            ui.note("Percentile-rank normalisation. Growth = second half against first half.")

    with st.expander("5 · V1 against V2"):
        st.markdown(
            "**V1 is the reference and the default.** It reproduces the team's "
            "submitted deliverables exactly, and the Power BI dashboard is built on it. "
            "V2 is shown beside it, never in place of it, so the effect of each "
            "methodological choice is visible rather than asserted."
        )
        st.markdown(
            "**Clustering features.** Six of V1's ten features measure the same thing, "
            "how large a merchant is. Because they are strongly correlated, "
            "standardisation gives size roughly six votes and behaviour four, so the "
            "clusters separate by size and the behavioural names overpromise.\n\n"
            "**BNPL.** V1 scores 50% total spend + 50% transaction count, with no "
            "ticket-size term at all, so the largest supermarkets top a list meant to "
            "surface high-ticket merchants. V2 gives ticket size 40% and high-ticket "
            "share 30%.\n\n"
            "**Normalisation.** Min-max lets one extreme merchant compress everyone "
            "else into a narrow band. Percentile rank cannot.\n\n"
            "**Growth.** A mean of month-over-month percentages is asymmetric: +100% "
            "then -50% returns spend to where it started but averages to +25%. "
            "Comparing halves of the period does not have that flaw.\n\n"
            "**Consistency.** Under V1, two deliverables are plain sorts and two are "
            "weighted composites, so they cannot be compared like for like."
        )
        ui.note(
            "Switching method recomputes scores only. The underlying transaction data, "
            "the cleaning and the customer segments are identical either way."
        )

    with st.expander("6 · Validation & Diagnostics", expanded=True):
        ui.section("Parameters derived from this file")
        ui.note(
            "Every threshold below is recalculated per upload. Nothing is inherited "
            "from the dataset the analysis was originally built on."
        )
        ui.table(pd.DataFrame([
            ("Outlier threshold", egp(report["outlier_threshold"]),
             "Q3 + 1.5 x IQR over all transactions"),
            ("Rows flagged as outliers", f"{report['outliers_flagged']:,}",
             f"{report['outliers_flagged'] / max(report['rows_out'], 1):.1%} of rows"),
            ("Recency snapshot", f"{(report['date_max'] + pd.Timedelta(days=1)):%Y-%m-%d}",
             "last transaction date + 1 day"),
            ("Low-Value / Mass cut", egp(thresholds["low_value_cut"]),
             "30th percentile of debit spend"),
            ("Mass / VIP cut", egp(thresholds["vip_cut"]),
             "80th percentile of debit spend"),
            ("Months covered", f"{report['months_covered']}",
             "divisor for monthly averages"),
            ("Cardholders", f"{report['cardholders']:,}", "distinct PANs"),
            ("Merchants", f"{report['merchants_total']:,}", "all statuses"),
        ], columns=["Parameter", "Value", "How it is derived"]))

        ui.section("The ticket-size diagnostic")
        st.write(
            "The four deliverables can only differ from one another if merchants differ "
            "from one another. This chart is the honest test of whether they do."
        )
        with st.spinner("Building merchant view"):
            merchant_view = build_merchant_features(filtered, customers)
        diagnostic = ticket_diagnostic(merchant_view)
        ui.kpis([
            ("Merchants in view", f"{len(merchant_view):,}", "after filters", ""),
            ("Mean average ticket", egp(diagnostic["mean"]), "across merchants", ""),
            ("Standard deviation", egp(diagnostic["std"]), "across merchants", ""),
            ("Spread", f"{diagnostic['spread']:.1%}", "std / mean",
             "warn" if diagnostic["spread"] < 0.15 else "accent"),
        ])
        if diagnostic["spread"] < 0.15:
            st.warning(
                f"A spread of {diagnostic['spread']:.1%} means average ticket is close to "
                "constant across merchants. Any ranking that leans on ticket size will "
                "therefore look similar to a volume ranking, whichever formula is used. "
                "This is a property of the data, and no scoring change can manufacture a "
                "signal that is not present."
            )
        st.plotly_chart(charts.ticket_variance(merchant_view.assign(
            category=merchant_view.get("category", "Unknown"))), width="stretch")

        ui.section("Verification")
        st.markdown(
            "`verify.py` re-runs the whole pipeline from the raw Excel and compares "
            "every stage against the team's original notebook outputs, column by "
            "column. It must return 43 of 43 or the methodology has drifted."
        )
        ui.table(pd.DataFrame([
            ("Stage 1, cleaning", "nbe_merchants_clean.csv", "22 columns compared"),
            ("Stage 3, segmentation", "customer_segments.csv", "10 columns compared"),
            ("Stage 2, clustering", "merchant_clusters.csv", "cluster names + 6 metrics"),
            ("Stage 4, scoring", "4 ranking CSVs", "rank position per merchant"),
        ], columns=["Stage", "Reference output", "What is checked"]))
        ui.note("Run from the project root: python verify.py    "
                "Reference outputs ship in outputs/.")

        ui.section("Limitations")
        for limitation in [
            "The uploaded file must carry the same columns as an NBE export. This is a "
            "purpose-built pipeline, not a general analysis tool.",
            "Merchant names are extracted by subtraction, so an unrecognised city can stay "
            "attached to a merchant name. Such rows are flagged with low geography "
            "confidence and the suspected city is surfaced on the Data Quality screen.",
            "Inferred categories are keyword guesses and are labelled as such everywhere. "
            "They are never presented as reference-mapped.",
            "All amounts are assumed to be EGP. There is no currency conversion.",
            "K-Means cluster numbering is arbitrary, so clusters are named from their "
            "profiles. Names still describe the profile, not a fixed group of merchants.",
            "Percentile segments and the outlier threshold get unstable on small files.",
            "This is a prototype: no authentication, no encryption, no audit log, and "
            "nothing is persisted between sessions.",
        ]:
            st.write(f"- {limitation}")

        notes = insights.data_quality_notes(report)
        if notes:
            ui.section("Notes on this dataset")
            for note_line in notes:
                st.write(f"- {note_line}")

    screen_downloads(filtered, customers)


# =============================================================================
# Export centre
# =============================================================================

def screen_downloads(filtered: pd.DataFrame, customers: pd.DataFrame) -> None:
    ui.section("Export centre", "reflects the current filters and method")
    ui.note(
        "Everything below reflects the current sidebar filters and the selected "
        "analysis method. Merchant tables carry merchant_status so new merchants "
        "stay identifiable downstream."
    )

    if not st.button("Prepare exports"):
        ui.note("Exports are built on request rather than on every page render.")
        return

    version = active_version()
    with st.spinner("Preparing outputs"):
        clusters, diag = safe_cluster(filtered, customers, version)
        groups = {
            "Data": {
                "transactions_clean.csv": filtered,
                "customer_segments.csv": customers,
            },
            "Analysis": {},
            "Reports": {},
        }
        if not diag["insufficient"]:
            rankings = run_scoring(filtered, clusters, version)
            groups["Analysis"][f"merchant_clusters_{version}.csv"] = clusters
            for name, table in rankings.items():
                groups["Analysis"][f"{name}_ranking_{version}.csv"] = table
        std_report = st.session_state.get("std_report")
        report = st.session_state.get("report")
        if std_report is not None and report is not None:
            groups["Reports"]["cleaning_report.csv"] = pd.DataFrame(
                cleaning_summary(std_report, report)
            )

    for group_name, files in groups.items():
        if not files:
            continue
        st.markdown(f"**{group_name}**")
        columns = st.columns(4)
        for index, (filename, table) in enumerate(files.items()):
            with columns[index % 4]:
                st.download_button(
                    filename,
                    data=table.to_csv(index=False).encode("utf-8"),
                    file_name=filename,
                    mime="text/csv",
                    width="stretch",
                    key=f"dl_{filename}",
                )
    if diag["insufficient"]:
        st.info("Merchant-level outputs need more merchants in view than clusters requested.")


# =============================================================================
# Sidebar
# =============================================================================

def sidebar_navigation() -> str:
    # Co-branding lives in the masthead now (NBE mark left, Digital Egypt mark
    # right, both sized to match) rather than as a full-width image at the top
    # of the sidebar, which rendered the partner mark far larger than NBE's own
    # and pushed the workflow list down.
    st.sidebar.markdown('<div class="nbe-navhead">WORKFLOW</div>', unsafe_allow_html=True)
    choice = st.sidebar.radio(
        "Navigation", SCREEN_NAMES, label_visibility="collapsed", key="nav",
    )
    if "clean_df" not in st.session_state and choice != SCREEN_NAMES[0]:
        st.sidebar.caption("Load a dataset to enable the analysis screens.")
    return choice


def sidebar_method() -> None:
    st.sidebar.markdown('<div class="nbe-navhead">ANALYSIS METHOD</div>',
                        unsafe_allow_html=True)
    label = st.sidebar.radio(
        "Analysis method",
        ["V1 Baseline", "V2 Enhanced"],
        label_visibility="collapsed",
        key="methodology_label",
        captions=["Original submitted methodology", "Enhanced diagnostic comparison"],
        help=(
            "V1 reproduces the team's submitted deliverables exactly and is the "
            "default. V2 is a comparison, not a replacement. Switching changes scores "
            "only; the underlying data is identical."
        ),
    )
    st.session_state["methodology_version"] = "v1" if label.startswith("V1") else "v2"


def sidebar_filters(clean_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Draw the sidebar filters and return the filtered transaction and customer tables.

    The customer table is FILTERED, not recomputed. Segments stay as assigned on
    the full dataset, matching the Power BI model where customer_segments is a
    precomputed table that slicers filter. Recomputing would reassign people to
    different tiers every time a filter moved, which is a different question
    from the one the dashboard answers.
    """
    customers = st.session_state["customers"]
    st.sidebar.markdown('<div class="nbe-navhead">FILTERS</div>', unsafe_allow_html=True)

    def options(column):
        return sorted(clean_df[column].dropna().unique().tolist())

    with st.sidebar.expander("Period"):
        dates = st.date_input(
            "Transaction date",
            value=(clean_df["Txn date"].min().date(), clean_df["Txn date"].max().date()),
            min_value=clean_df["Txn date"].min().date(),
            max_value=clean_df["Txn date"].max().date(),
        )

    with st.sidebar.expander("Customers"):
        segments = st.multiselect("Customer segment", ["VIP", "Mass", "Low-Value"])
        outliers = st.radio(
            "High-value transactions",
            ["Include", "Exclude only outliers", "Outliers only"],
            help="Outlier means above Q3 + 1.5 x IQR, recomputed from this file.",
        )

    with st.sidebar.expander("Merchants"):
        chosen = {
            "merchant": st.multiselect(
                "Merchant", options("merchant"),
                help="Narrowing below the cluster count disables clustering; the app "
                     "says so rather than failing.",
            ),
            "category": st.multiselect("Category", options("category")),
            "governorate": st.multiselect("Governorate", options("governorate")),
            "gateway": st.multiselect("Gateway", options("gateway")),
            "merchant_status": st.multiselect(
                "Merchant status", options("merchant_status"),
                help="New merchants are included by default, exactly like known ones.",
            ),
        }

    mask = pd.Series(True, index=clean_df.index)
    if isinstance(dates, (tuple, list)) and len(dates) == 2:
        start, end = pd.Timestamp(dates[0]), pd.Timestamp(dates[1])
        mask &= clean_df["Txn date"].between(start, end)
    for column, values in chosen.items():
        if values:
            mask &= clean_df[column].isin(values)
    if outliers == "Exclude only outliers":
        mask &= ~clean_df["is_outlier"]
    elif outliers == "Outliers only":
        mask &= clean_df["is_outlier"]

    filtered_customers = customers
    if segments:
        filtered_customers = filtered_customers[filtered_customers["segment"].isin(segments)]
        mask &= clean_df["PAN"].isin(filtered_customers["PAN"])

    filtered = clean_df[mask]
    filtered_customers = filtered_customers[
        filtered_customers["PAN"].isin(filtered["PAN"].unique())
    ]

    active = {k: v for k, v in chosen.items() if v}
    if segments:
        active["segment"] = segments
    if outliers != "Include":
        active["outliers"] = outliers
    if isinstance(dates, (tuple, list)) and len(dates) == 2:
        if (dates[0] != clean_df["Txn date"].min().date()
                or dates[1] != clean_df["Txn date"].max().date()):
            active["period"] = f"{dates[0]:%d %b %Y} to {dates[1]:%d %b %Y}"
    return filtered, filtered_customers, active


def filter_banner(filtered: pd.DataFrame, total: pd.DataFrame, active: dict) -> bool:
    """Say what is being excluded. Returns False when nothing is left to show."""
    ui.filter_chips(active, len(filtered), len(total))
    if filtered.empty:
        st.warning("No transactions match the current filters. Widen them in the sidebar.")
        return False
    return True


# =============================================================================
# Shell
# =============================================================================

screen = sidebar_navigation()
screen_index = SCREEN_NAMES.index(screen)
loaded = "clean_df" in st.session_state

# The method selector only appears on the screens it actually drives.
if loaded and screen_index in (4, 5, 6):
    sidebar_method()

chips = [("PROJECT GRADUATION", "")]
if loaded:
    _report = st.session_state["report"]
    if screen_index in (4, 5, 6):
        chips.insert(0, (VERSION_COPY[active_version()][0], ""))
    if _report["new_merchants"]:
        chips.insert(0, (f"{_report['new_merchants']} new merchants", "gold"))
    chips.insert(0, (f"{st.session_state.get('filename', 'dataset')}  ·  "
                     f"{_report['rows_out']:,} rows", "green"))
else:
    chips.insert(0, ("No dataset loaded", "idle"))

ui.masthead(
    LOGO_FILE if LOGO_FILE.exists() else None,
    chips,
    partner_logo_path=CO_BRAND_LOGO_FILE if CO_BRAND_LOGO_FILE.exists() else None,
)
ui.journey(JOURNEY, screen_index, SCREEN_NAMES)

if screen_index == 0:
    screen_load()
elif not loaded:
    st.info("Load a dataset on the Load screen first.")
elif screen_index == 1:
    screen_cleaning()
else:
    _clean = st.session_state["clean_df"]
    _filtered, _filtered_customers, _active = sidebar_filters(_clean)
    if filter_banner(_filtered, _clean, _active):
        if screen_index == 2:
            screen_executive(_filtered)
        elif screen_index == 3:
            screen_segments(_filtered, _filtered_customers)
        elif screen_index == 4:
            screen_clustering(_filtered, st.session_state["customers"])
        elif screen_index == 5:
            screen_rankings(_filtered, st.session_state["customers"])
        elif screen_index == 6:
            screen_methodology(_filtered, _filtered_customers)

ui.team_footer(["Saleh", "Zeyad", "Yousef", "Toka", "Aya"])

with st.sidebar:
    ui.footer()
