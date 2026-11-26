"""
Stage 1: Cleaning and merchant resolution.

Turns a raw NBE transaction export into the analysis-ready table.

The hard part is `Description`, a free-text field packing gateway, merchant,
city, governorate and an optional reference code into one string.

LOCKED DESIGN DECISION: reference lists are baselines, not whitelists.

The parser identifies a merchant by subtraction, never by lookup: it removes
the gateway prefix, the EGY suffix, the reference code, the governorate and
the city, and whatever survives is the merchant. A merchant is therefore never
rejected for being absent from the reference list. It is resolved to one of
three statuses:

    known    parsed and matched to the reference list (exact, alias, or a
             high-confidence close match)
    new      parsed cleanly but absent from the reference list. A real
             merchant. Flows through every downstream stage unchanged, with
             no penalty, exclusion or special scoring.
    unknown  the parser genuinely could not isolate a merchant name

"Not in the reference list" is NEVER "unknown".

The same principle applies to geography. An unrecognised city is the one way
subtraction can quietly go wrong: if the city is not stripped it stays glued
to the merchant name, and a phantom merchant is born that looks perfectly
valid. Geography is therefore scored for confidence, and probable new cities
are detected and surfaced rather than silently absorbed.

Category is resolved independently of merchant status, with its own status:
`mapped` from the reference, `inferred` from keyword rules, or `Unknown`.
An inferred category is never presented as a reference-mapped one.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

import numpy as np
import pandas as pd

REFERENCE_DIR = Path(__file__).resolve().parent.parent / "reference"

REQUIRED_COLUMNS = [
    "PAN",
    "Txn date",
    "Posting Date",
    "Amount",
    "Currency",
    "DB/CR",
    "Description",
    "Primary Cardholder Auth Method",
]
OPTIONAL_COLUMNS = [
    "On Stmt?",
    "In Dispute?",
    "Date Disputed",
    "Date Released",
    "Released To",
    "Alternative PAN",
]

# Column order of the analysis-ready table. The first 22 match
# nbe_merchants_clean.csv exactly; resolution columns are appended after.
CLEAN_COLUMNS = [
    "PAN", "Txn date", "Posting Date", "Amount", "Currency", "DB/CR",
    "merchant", "category", "gateway", "city", "governorate", "country",
    "ref_code", "is_international", "Description", "auth_method",
    "Alternative PAN", "txn_month", "txn_quarter", "day_of_week",
    "is_egyptian", "is_outlier",
]
RESOLUTION_COLUMNS = [
    "merchant_status", "category_status", "geo_confidence", "merchant_raw",
]

# Roughly 19,500 of 100,000 rows separate geography with "-" or "/" rather
# than a space. Handling only spaces silently loses those rows.
SEPARATORS = (" ", " -", " /")

REF_CODE_PATTERN = re.compile(
    r"\s([0-9A-Z]{1,2}-[0-9A-Z]{3,4}(?:-[0-9A-Z]{3})?)\s*(?=EGY$)"
)
REF_CODE_LIKE = re.compile(r"^[0-9A-Z]{1,2}-[0-9A-Z]{2,4}(-[0-9A-Z]{2,4})?$")

# Similarity required to auto-correct a merchant onto a reference name.
# Deliberately strict: this rewrites data, so it must only catch obvious
# typographic variants such as MCDONALD S -> MCDONALDS.
CLOSE_MATCH_CUTOFF = 0.92

# A trailing token counts as a probable unrecognised city only when it appears
# after many different merchants.
CITY_CANDIDATE_MIN_PREFIXES = 3
CITY_CANDIDATE_MIN_ROWS = 10


class Vocabulary:
    """Reference lists used by the parser. Baselines, never whitelists."""

    def __init__(self, reference_dir: Path = REFERENCE_DIR):
        self.reference_dir = Path(reference_dir)
        self.governorates = self._load("governorates.csv", "governorate")
        self.cities = self._load("cities.csv", "city")
        self.countries = self._load("countries.csv", "country")
        self.gateways = set(self._load("gateways.csv", "gateway"))

        aliases = pd.read_csv(self.reference_dir / "merchant_aliases.csv")
        self.merchant_aliases = dict(zip(aliases["raw"], aliases["clean"]))

        categories = pd.read_csv(self.reference_dir / "merchant_categories.csv")
        self.merchant_categories = dict(zip(categories["merchant"], categories["category"]))
        self.reference_merchants = list(categories["merchant"])

        keywords = pd.read_csv(self.reference_dir / "category_keywords.csv")
        self.category_keywords = (
            keywords.sort_values("priority")[["keyword", "category"]].values.tolist()
        )

    def _load(self, filename: str, column: str) -> list[str]:
        """Load a vocabulary longest-first.

        Order matters: "SOUTH SINAI" must be tested before "SINAI", or the
        longer name gets truncated by a shorter one that is a suffix of it.
        """
        values = pd.read_csv(self.reference_dir / filename)[column].dropna().tolist()
        return sorted(values, key=len, reverse=True)

    def learn_cities(self, new_cities: list[str]) -> None:
        """Extend the city baseline in memory for a re-parse."""
        self.cities = sorted(set(self.cities) | set(new_cities), key=len, reverse=True)


def normalize_merchant(name: str) -> str:
    """Merchant name conventions used by the reference analysis.

    MCDONALD'S -> MCDONALDS, H&M -> HANDM, B.TECH -> BTECH,
    APPLE.COM/BILL -> APPLECOM BILL
    """
    return (
        name.replace("&", "AND").replace("'", "").replace(".", "").replace("/", " ").strip()
    )


def _strip_known_suffix(text: str, vocabulary) -> tuple[str | None, str]:
    """Remove a trailing vocabulary term, tolerating any known separator.

    Also matches when the term is the entire remaining string, which happens on
    descriptions that carry geography but no merchant ("GEIDEA* CAIRO EGY").
    Without this the governorate survives as a phantom merchant named CAIRO.
    """
    for term in vocabulary:
        if text == term:
            return term, ""
        for separator in SEPARATORS:
            suffix = separator + term
            if text.endswith(suffix):
                return term, text[: -len(suffix)].strip()
    return None, text


def _is_degenerate(text: str) -> bool:
    """True when the leftover text cannot be a merchant name."""
    stripped = text.strip()
    if len(stripped) < 2:
        return True
    if stripped.replace(" ", "").isdigit():
        return True
    return bool(REF_CODE_LIKE.match(stripped))


def parse_description(description, vocab: Vocabulary) -> dict:
    """Split one Description into its structured parts.

    Two shapes exist:
      domestic      [GATEWAY*] MERCHANT CITY GOVERNORATE [REF_CODE] EGY
      international MERCHANT COUNTRY
    """
    parsed = {
        "gateway": None, "merchant_raw": None, "city": None, "governorate": None,
        "ref_code": None, "country": None, "had_egy": False, "city_tail": None,
    }
    if description is None or (isinstance(description, float) and np.isnan(description)):
        return parsed

    text = str(description).strip()
    if not text:
        return parsed

    if "*" in text:
        gateway, text = (part.strip() for part in text.split("*", 1))
        parsed["gateway"] = gateway

    country, remainder = _strip_known_suffix(text, vocab.countries)
    if country is not None:
        parsed["country"] = country
        parsed["merchant_raw"] = normalize_merchant(remainder)
        return parsed

    if text.endswith("EGY"):
        parsed["had_egy"] = True
        match = REF_CODE_PATTERN.search(text)
        if match:
            parsed["ref_code"] = match.group(1)
            text = text[: match.start()] + " EGY"
        text = text[:-3].strip()

    parsed["governorate"], text = _strip_known_suffix(text, vocab.governorates)
    parsed["city"], text = _strip_known_suffix(text, vocab.cities)

    # No city matched on a clearly domestic row: the trailing words are the
    # prime suspects for an unrecognised city that stayed glued to the name.
    if parsed["city"] is None and parsed["governorate"] is not None:
        tokens = text.split()
        if len(tokens) >= 2:
            parsed["city_tail"] = " ".join(tokens[-2:])

    parsed["merchant_raw"] = normalize_merchant(text)
    return parsed


def discover_city_candidates(parsed: pd.DataFrame) -> pd.DataFrame:
    """Find trailing tokens that behave like cities but are not in the baseline.

    A real city appears after many different merchants. A word that genuinely
    belongs to one merchant's name does not. Candidates are reported, never
    applied automatically, because applying one rewrites merchant names.
    """
    columns = ["candidate", "rows", "distinct_merchant_prefixes", "sample_description"]
    suspects = parsed[parsed["city_tail"].notna()].copy()
    if suspects.empty:
        return pd.DataFrame(columns=columns)

    frames = []
    for tail_length in (2, 1):
        working = suspects.copy()
        working["candidate"] = working["city_tail"].apply(
            lambda t: " ".join(str(t).split()[-tail_length:])
        )
        working["prefix"] = working.apply(
            lambda r: r["merchant_raw"][: -len(r["candidate"])].strip()
            if isinstance(r["merchant_raw"], str) and r["merchant_raw"].endswith(r["candidate"])
            else r["merchant_raw"],
            axis=1,
        )
        frames.append(
            working.groupby("candidate")
            .agg(
                rows=("candidate", "size"),
                distinct_merchant_prefixes=("prefix", "nunique"),
                sample_description=("Description", "first"),
            )
            .reset_index()
        )

    candidates = pd.concat(frames, ignore_index=True)
    candidates = candidates[
        (candidates["distinct_merchant_prefixes"] >= CITY_CANDIDATE_MIN_PREFIXES)
        & (candidates["rows"] >= CITY_CANDIDATE_MIN_ROWS)
    ].sort_values(["rows", "candidate"], ascending=[False, False])

    # "REHAB CITY" and "CITY" describe the same evidence. Keep the longer one.
    kept = []
    for _, row in candidates.iterrows():
        if any(
            k["candidate"].endswith(" " + row["candidate"]) and k["rows"] == row["rows"]
            for k in kept
        ):
            continue
        kept.append(row)
    if not kept:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(kept).reset_index(drop=True)[columns]


def resolve_merchants(parsed: pd.DataFrame, vocab: Vocabulary):
    """Assign a final merchant name and a status to every row.

    Returns (merchant, merchant_status, auto_corrections).
    """
    reference = set(vocab.reference_merchants)
    # A leftover that is purely a place name means the description carried
    # geography and nothing else, so no merchant could be isolated.
    place_names = set(vocab.governorates) | set(vocab.cities) | set(vocab.countries)
    resolution: dict[str, tuple] = {}
    auto_corrections: dict[str, str] = {}

    for raw in parsed["merchant_raw"].dropna().unique():
        if _is_degenerate(raw) or (raw in place_names and raw not in reference):
            resolution[raw] = (raw, "unknown")
            continue
        alias = vocab.merchant_aliases.get(raw)
        if alias is not None:
            resolution[raw] = (alias, "known")
            continue
        if raw in reference:
            resolution[raw] = (raw, "known")
            continue
        close = difflib.get_close_matches(
            raw, vocab.reference_merchants, n=1, cutoff=CLOSE_MATCH_CUTOFF
        )
        if close:
            resolution[raw] = (close[0], "known")
            auto_corrections[raw] = close[0]
            continue
        # Parsed cleanly, simply not in the baseline. A real merchant.
        resolution[raw] = (raw, "new")

    merchant = parsed["merchant_raw"].map(lambda r: resolution.get(r, (None, "unknown"))[0])
    status = parsed["merchant_raw"].map(lambda r: resolution.get(r, (None, "unknown"))[1])
    status = status.where(parsed["merchant_raw"].notna(), "unknown")
    return merchant, status, auto_corrections


def infer_category(merchant, vocab: Vocabulary):
    """Guess a category from words in the merchant name.

    Rules live in reference/category_keywords.csv, applied in priority order.
    The result is always labelled `inferred`, never `mapped`.
    """
    if not isinstance(merchant, str):
        return None
    tokens = merchant.split()
    for keyword, category in vocab.category_keywords:
        for token in tokens:
            if token == keyword:
                return category
            # Affix matching only for longer keywords, so NETFLIXCOM resolves
            # while short keywords cannot match inside unrelated words.
            if len(keyword) >= 4 and (token.startswith(keyword) or token.endswith(keyword)):
                return category
    return None


def resolve_categories(merchant: pd.Series, vocab: Vocabulary):
    """Assign category and category_status independently of merchant status."""
    resolution: dict[str, tuple] = {}
    for name in merchant.dropna().unique():
        mapped = vocab.merchant_categories.get(name)
        if mapped is not None:
            resolution[name] = (mapped, "mapped")
            continue
        inferred = infer_category(name, vocab)
        resolution[name] = (inferred, "inferred") if inferred else ("Unknown", "Unknown")

    category = merchant.map(lambda m: resolution.get(m, ("Unknown", "Unknown"))[0])
    status = merchant.map(lambda m: resolution.get(m, ("Unknown", "Unknown"))[1])
    return category, status


def score_geo_confidence(parsed: pd.DataFrame, merchant_status: pd.Series) -> pd.Series:
    """How much to trust the geography split on each row.

    high    international, or governorate and city both resolved
    medium  governorate resolved, nothing city-shaped left over
    low     governorate resolved but trailing words look like a city, so the
            merchant name may have absorbed it
    none    no geography markers recognised at all
    """
    confidence = pd.Series("none", index=parsed.index, dtype=object)
    domestic = parsed["country"].isna()
    has_gov = parsed["governorate"].notna()
    has_city = parsed["city"].notna()
    suspect_tail = parsed["city_tail"].notna()

    confidence[parsed["country"].notna()] = "high"
    confidence[domestic & has_gov & has_city] = "high"
    confidence[domestic & has_gov & ~has_city] = "medium"
    confidence[domestic & has_gov & ~has_city & suspect_tail] = "low"
    confidence[merchant_status.values == "unknown"] = "none"
    return confidence


def compute_outlier_flag(amounts: pd.Series) -> pd.Series:
    """Flag high-value transactions with a global Tukey fence.

    Recomputed from whatever data is loaded, so the threshold adapts to a new
    file rather than inheriting one dataset's cutoff.
    """
    q1, q3 = amounts.quantile([0.25, 0.75])
    return amounts > q3 + 1.5 * (q3 - q1)


def clean(
    raw: pd.DataFrame,
    vocab: Vocabulary | None = None,
    learn_geography: bool = False,
    deduplicate: bool = True,
):
    """Run Stage 1. Returns the clean table and a report of what happened.

    learn_geography=True re-parses using discovered city candidates. Off by
    default, because accepting a candidate rewrites merchant names.

    deduplicate=False when the frame has already been through
    `standardize.standardize()`, which removes exact duplicates while it can
    still see every column the file supplied. Deduplicating again here would
    judge "identical" on the reduced column set and delete rows that differ
    only in a column Stage 0 dropped, such as a dispute flag. Left True so
    that calling clean() directly on a raw export still behaves as before.
    """
    vocab = vocab or Vocabulary()
    df = raw.copy()

    rows_in = len(df)
    if deduplicate:
        duplicates_removed = int(df.duplicated().sum())
        df = df.drop_duplicates().reset_index(drop=True)
    else:
        duplicates_removed = 0

    df["Txn date"] = pd.to_datetime(df["Txn date"], errors="coerce")
    df["Posting Date"] = pd.to_datetime(df["Posting Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")

    def run_parse():
        out = pd.DataFrame(
            [parse_description(d, vocab) for d in df["Description"]], index=df.index
        )
        out["Description"] = df["Description"]
        return out

    parsed = run_parse()
    city_candidates = discover_city_candidates(parsed)
    learned_cities = []
    if learn_geography and not city_candidates.empty:
        learned_cities = city_candidates["candidate"].tolist()
        vocab.learn_cities(learned_cities)
        parsed = run_parse()
        city_candidates = discover_city_candidates(parsed)

    merchant, merchant_status, auto_corrections = resolve_merchants(parsed, vocab)
    category, category_status = resolve_categories(merchant, vocab)

    df["merchant"] = merchant
    df["merchant_raw"] = parsed["merchant_raw"]
    df["merchant_status"] = merchant_status
    df["category"] = category
    df["category_status"] = category_status
    df["geo_confidence"] = score_geo_confidence(parsed, merchant_status)
    for column in ("gateway", "city", "governorate", "country", "ref_code"):
        df[column] = parsed[column]

    df["is_international"] = df["country"].notna()
    df["is_egyptian"] = ~df["is_international"]
    df["txn_month"] = df["Txn date"].dt.strftime("%Y-%m")
    df["txn_quarter"] = (
        df["Txn date"].dt.year.astype("Int64").astype(str)
        + "Q"
        + df["Txn date"].dt.quarter.astype("Int64").astype(str)
    )
    df["day_of_week"] = df["Txn date"].dt.day_name()
    df["is_outlier"] = compute_outlier_flag(df["Amount"])

    df = df.rename(columns={"Primary Cardholder Auth Method": "auth_method"})
    for column in CLEAN_COLUMNS + RESOLUTION_COLUMNS:
        if column not in df.columns:
            df[column] = np.nan
    df = df[CLEAN_COLUMNS + RESOLUTION_COLUMNS]

    report = _build_report(
        df, rows_in, duplicates_removed, auto_corrections, city_candidates, learned_cities
    )
    return df, report


def _build_report(df, rows_in, duplicates_removed, auto_corrections, city_candidates, learned_cities):
    """Everything the Load screen needs to explain what the pipeline did."""
    by_status = df.groupby("merchant_status")["merchant"].nunique()
    unknown_rows = df[df["merchant_status"] == "unknown"]
    domestic = df["is_egyptian"]

    return {
        "rows_in": rows_in,
        "rows_out": len(df),
        "duplicates_removed": duplicates_removed,
        # Counts stay strictly separate: new is never folded into unknown.
        "known_merchants": int(by_status.get("known", 0)),
        "new_merchants": int(by_status.get("new", 0)),
        "unknown_merchants": int(by_status.get("unknown", 0)),
        "known_rows": int((df["merchant_status"] == "known").sum()),
        "new_rows": int((df["merchant_status"] == "new").sum()),
        "unknown_rows": int(len(unknown_rows)),
        "unknown_samples": unknown_rows["Description"].head(10).tolist(),
        "new_merchant_table": _merchant_summary(df[df["merchant_status"] == "new"]),
        "auto_corrections": auto_corrections,
        "city_candidates": city_candidates,
        "learned_cities": learned_cities,
        "category_mapped": int((df["category_status"] == "mapped").sum()),
        "category_inferred": int((df["category_status"] == "inferred").sum()),
        "category_unknown": int((df["category_status"] == "Unknown").sum()),
        "geo_confidence_counts": df["geo_confidence"].value_counts().to_dict(),
        "low_confidence_rows": int((df["geo_confidence"] == "low").sum()),
        "geography_parse_rate": float(df.loc[domestic, "governorate"].notna().mean())
        if domestic.any() else 1.0,
        "international_rows": int(df["is_international"].sum()),
        "outlier_threshold": float(
            df["Amount"].quantile(0.75)
            + 1.5 * (df["Amount"].quantile(0.75) - df["Amount"].quantile(0.25))
        ),
        "outliers_flagged": int(df["is_outlier"].sum()),
        "cardholders": int(df["PAN"].nunique()),
        "merchants_total": int(df["merchant"].nunique()),
        "date_min": df["Txn date"].min(),
        "date_max": df["Txn date"].max(),
        "months_covered": int(df["txn_month"].nunique()),
    }


def _merchant_summary(subset: pd.DataFrame) -> pd.DataFrame:
    """The New Merchants Detected table."""
    columns = ["merchant", "sample_description", "category", "category_status",
               "geo_confidence", "transactions", "total_spend"]
    if subset.empty:
        return pd.DataFrame(columns=columns)
    summary = subset.groupby("merchant").agg(
        sample_description=("Description", "first"),
        category=("category", "first"),
        category_status=("category_status", "first"),
        geo_confidence=("geo_confidence", lambda s: s.mode().iloc[0]),
        transactions=("Amount", "size"),
        total_spend=("Amount", "sum"),
    ).reset_index()
    return summary.sort_values("total_spend", ascending=False).reset_index(drop=True)[columns]
