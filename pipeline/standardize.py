"""
Stage 0: Standardisation and validation.

Runs before `clean.clean()`. Its job is to take whatever spreadsheet the user
uploaded and turn it into the exact shape the rest of the pipeline assumes,
doing as much as can be done safely and reporting everything it could not.

The original Stage 1 notebook did this by hand: it assumed the column names of
one specific export, called `sys.exit(1)` if any were missing, and left every
other decision (date formats, amount formats, debit/credit spellings) to
whoever produced the file. This module automates that contract.

DESIGN RULE, inherited from clean.py: columns supplied by the uploaded file
that duplicate something the pipeline derives itself are NEVER trusted. If an
upload arrives with its own `merchant`, `category`, `city`, `governorate`,
`country` or `gateway` column, it is renamed to `supplied_<name>` and ignored.
The Description parser stays the single source of truth for those fields.

Three levels of column requirement:

  hard     PAN, Txn date, Amount, Description, DB/CR
           Nothing can be computed without these. Missing one is a hard stop.
  soft     Posting Date, Currency, Primary Cardholder Auth Method
           Used by individual measures. Synthesised as empty with a warning,
           so a file that lacks them still runs.
  optional Dispute fields, On Stmt?, Alternative PAN
           Reported when present, never required.

Nothing here alters a value the pipeline already understood. On an export that
already matches the reference schema every step below is a no-op, which is what
keeps the demo dataset reproducing byte-identical results.
"""

from __future__ import annotations

import difflib
import re

import numpy as np
import pandas as pd

HARD_REQUIRED = ["PAN", "Txn date", "Amount", "Description", "DB/CR"]
SOFT_REQUIRED = ["Posting Date", "Currency", "Primary Cardholder Auth Method"]
KNOWN_OPTIONAL = [
    "On Stmt?", "In Dispute?", "Date Disputed", "Date Released",
    "Released To", "Alternative PAN",
]

# Columns the pipeline derives from Description. Never taken from the upload.
DERIVED_NOT_SUPPLIED = [
    "merchant", "merchant_raw", "category", "gateway", "city",
    "governorate", "country", "ref_code", "is_international",
    "is_egyptian", "is_outlier", "merchant_status", "category_status",
    "geo_confidence", "txn_month", "txn_quarter", "day_of_week",
]

# Dispute handling is out of scope for merchant insight. Detected, counted,
# then dropped, so the reason appears in the summary rather than silently.
DISPUTE_PATTERN = re.compile(r"dispute|disputed|released", re.IGNORECASE)

# Alias table. Keys are canonical names, values are accepted spellings.
# Matching is done on the normalised form (uppercase, alphanumeric only), so
# "Transaction Date", "transaction_date" and "TRANSACTION DATE" are one entry.
COLUMN_ALIASES: dict[str, list[str]] = {
    "PAN": [
        "PAN", "Card Number", "Card No", "Cardnumber", "Customer ID",
        "CustomerID", "Customer Number", "Cardholder ID", "Card ID",
        "Masked PAN", "Primary Account Number", "Account Number", "Card",
    ],
    "Txn date": [
        "Txn date", "Transaction Date", "Txn Date", "TxnDate", "Trans Date",
        "Date", "Transaction Datetime", "Purchase Date", "Value Date",
        "Trx Date", "Transaction_Date",
    ],
    "Posting Date": [
        "Posting Date", "Post Date", "PostingDate", "Settlement Date",
        "Posted Date", "Booking Date",
    ],
    "Amount": [
        "Amount", "Transaction Amount", "Txn Amount", "Amt", "Value",
        "Transaction Value", "Amount EGP", "Billing Amount", "Trx Amount",
        "Transaction_Amount",
    ],
    "Currency": [
        "Currency", "Currency Code", "Ccy", "Txn Currency",
        "Transaction Currency", "Billing Currency",
    ],
    "DB/CR": [
        "DB/CR", "DBCR", "DB CR", "Debit Credit", "Debit/Credit",
        "Credit Debit Indicator", "Transaction Type", "Txn Type", "Type",
        "DR/CR", "Direction", "Indicator",
    ],
    "Description": [
        "Description", "Transaction Description", "Narrative", "Details",
        "Merchant Description", "Txn Description", "Particulars", "Remarks",
        "Transaction_Description",
    ],
    "Primary Cardholder Auth Method": [
        "Primary Cardholder Auth Method", "Auth Method",
        "Authentication Method", "Authorisation Method",
        "Authorization Method", "Cardholder Auth Method", "auth_method",
    ],
    "Alternative PAN": [
        "Alternative PAN", "Alt PAN", "Secondary PAN", "Supplementary Card",
    ],
    "On Stmt?": ["On Stmt?", "On Statement", "On Stmt", "Statement Flag"],
    "In Dispute?": ["In Dispute?", "In Dispute", "Disputed", "Dispute Flag"],
    "Date Disputed": ["Date Disputed", "Dispute Date", "Disputed On"],
    "Date Released": ["Date Released", "Release Date", "Released On"],
    "Released To": ["Released To", "Release To"],
}

# Accepted spellings for the two debit/credit values. Compared on the
# normalised form of the cell.
DEBIT_TOKENS = {
    "DEBITTRANSACTION", "DEBIT", "DB", "DR", "D", "DEBITS", "WITHDRAWAL",
    "PURCHASE", "DEBITTXN", "DEBITTRX",
}
CREDIT_TOKENS = {
    "CREDITTRANSACTION", "CREDIT", "CR", "C", "CREDITS", "REFUND",
    "REVERSAL", "CREDITTXN", "CREDITTRX",
}
DEBIT_VALUE = "DEBIT TRANSACTION"
CREDIT_VALUE = "CREDIT TRANSACTION"

# Similarity required before a column name is matched by shape rather than by
# the alias table. Strict, because a wrong column mapping corrupts everything
# downstream and is hard to notice.
COLUMN_MATCH_CUTOFF = 0.82

_NON_ALNUM = re.compile(r"[^A-Z0-9]+")
# Currency symbols, thousands separators and stray whitespace inside numbers.
_AMOUNT_STRIP = re.compile(r"[^\d\.\-\(\)]+")


def normalise_header(name) -> str:
    """Reduce a column name to letters and digits, uppercased.

    'Transaction Date', 'transaction_date' and 'TRANSACTION  DATE' all become
    'TRANSACTIONDATE', so casing, spacing and punctuation stop mattering.
    """
    return _NON_ALNUM.sub("", str(name).strip().upper())


def _alias_index() -> dict[str, str]:
    """Normalised alias -> canonical column name."""
    index: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            index.setdefault(normalise_header(alias), canonical)
    return index


ALIAS_INDEX = _alias_index()


def resolve_columns(columns: list[str]) -> dict:
    """Map the uploaded column names onto canonical names.

    Three passes, strongest evidence first: exact canonical name, alias table,
    then fuzzy shape match. A canonical name claimed by more than one source
    column is reported as ambiguous and left unmapped rather than guessed.

    Returns mapping (source -> canonical), ambiguous, unmatched and the method
    used for each resolved column.
    """
    claims: dict[str, list[tuple[str, str]]] = {}
    unmatched: list[str] = []

    canonical_by_norm = {normalise_header(c): c for c in COLUMN_ALIASES}

    for source in columns:
        norm = normalise_header(source)
        if norm in canonical_by_norm:
            claims.setdefault(canonical_by_norm[norm], []).append((source, "exact"))
            continue
        if norm in ALIAS_INDEX:
            claims.setdefault(ALIAS_INDEX[norm], []).append((source, "alias"))
            continue
        close = difflib.get_close_matches(
            norm, list(ALIAS_INDEX), n=1, cutoff=COLUMN_MATCH_CUTOFF
        )
        if close:
            claims.setdefault(ALIAS_INDEX[close[0]], []).append((source, "fuzzy"))
            continue
        unmatched.append(source)

    mapping: dict[str, str] = {}
    method: dict[str, str] = {}
    ambiguous: dict[str, list[str]] = {}

    for canonical, candidates in claims.items():
        # An exact hit always beats an alias hit, which always beats a fuzzy
        # one. Ambiguity only counts within the strongest tier present.
        for tier in ("exact", "alias", "fuzzy"):
            tier_hits = [source for source, how in candidates if how == tier]
            if tier_hits:
                break
        if len(tier_hits) > 1:
            ambiguous[canonical] = tier_hits
            continue
        mapping[tier_hits[0]] = canonical
        method[canonical] = tier

    return {
        "mapping": mapping,
        "method": method,
        "ambiguous": ambiguous,
        "unmatched": unmatched,
        "resolved": sorted(mapping.values()),
    }


def parse_amount(series: pd.Series) -> tuple[pd.Series, int]:
    """Coerce an amount column to float.

    Handles the formats that actually turn up in bank exports: thousands
    separators, a currency symbol or code glued on, and accounting-style
    negatives in parentheses. Returns the parsed series and the number of
    non-empty cells that could not be read.
    """
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float), 0

    text = series.astype(str).str.strip()
    negative = text.str.match(r"^\(.*\)$", na=False)
    stripped = text.str.replace(_AMOUNT_STRIP, "", regex=True)
    stripped = stripped.str.replace(r"[\(\)]", "", regex=True)
    parsed = pd.to_numeric(stripped, errors="coerce")
    parsed = parsed.where(~negative, -parsed)

    had_value = series.notna() & (text != "") & (text.str.lower() != "nan")
    failed = int((had_value & parsed.isna()).sum())
    return parsed.astype(float), failed


def parse_dates(series: pd.Series) -> tuple[pd.Series, int, str]:
    """Coerce a date column to datetime.

    Tries the default (month-first) reading and a day-first reading, and keeps
    whichever parses more cells. Egyptian exports are commonly day-first, so
    picking blind would silently swap days and months on any date below the
    13th. Returns the parsed series, the failure count and the order used.
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return series, int(series.isna().sum() - series.isna().sum()), "native"

    default = pd.to_datetime(series, errors="coerce")
    dayfirst = pd.to_datetime(series, errors="coerce", dayfirst=True)

    had_value = series.notna() & (series.astype(str).str.strip() != "")
    if dayfirst.notna().sum() > default.notna().sum():
        parsed, order = dayfirst, "day-first"
    else:
        parsed, order = default, "month-first"
    return parsed, int((had_value & parsed.isna()).sum()), order


def normalise_debit_credit(series: pd.Series) -> tuple[pd.Series, int, dict]:
    """Map whatever the file calls debit and credit onto the two canonical values.

    Returns the normalised series, the count of cells left unrecognised, and
    the before/after value map for the cleaning summary.
    """
    original = series.astype(str).str.strip()
    norm = original.str.upper().str.replace(_NON_ALNUM, "", regex=True)

    out = pd.Series(pd.NA, index=series.index, dtype=object)
    out[norm.isin(DEBIT_TOKENS)] = DEBIT_VALUE
    out[norm.isin(CREDIT_TOKENS)] = CREDIT_VALUE

    unresolved_mask = out.isna() & series.notna()
    # Anything unrecognised keeps its original text rather than being dropped,
    # so a reviewer can see what it was.
    out[unresolved_mask] = original[unresolved_mask]

    value_map = {}
    for before, after in zip(original, out):
        value_map.setdefault(before, after)

    # If nothing actually changed, hand back the original series untouched so
    # the dtype is preserved. This is what keeps a file that already uses the
    # canonical spellings byte-identical through this phase.
    if not value_map or all(before == after for before, after in value_map.items()):
        return series, 0, value_map
    return out, int(unresolved_mask.sum()), value_map


def standardize(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Turn an arbitrary upload into the schema `clean.clean()` expects.

    Returns (standardised frame, report). The report is a complete account of
    what was found, mapped, parsed, changed and removed, computed entirely
    from the file passed in. Nothing is hard-coded to any one dataset.

    Raises nothing. A file that cannot proceed comes back with
    report['status'] == 'blocked' and report['errors'] populated.
    """
    report: dict = {
        "status": "ok",
        "errors": [],
        "warnings": [],
    }

    df = raw.copy()
    report["rows_in"] = len(df)
    report["columns_in"] = list(df.columns)
    report["column_count_in"] = len(df.columns)

    # --- 1. column names ----------------------------------------------------
    resolution = resolve_columns(list(df.columns))
    report["column_resolution"] = resolution
    report["columns_mapped"] = {
        source: target for source, target in resolution["mapping"].items()
        if source != target
    }
    report["columns_unmatched"] = resolution["unmatched"]
    report["columns_ambiguous"] = resolution["ambiguous"]

    for canonical, sources in resolution["ambiguous"].items():
        report["errors"].append(
            f"'{canonical}' could refer to more than one column in this file "
            f"({', '.join(sources)}). Pick one manually; the pipeline will not guess."
        )

    df = df.rename(columns=resolution["mapping"])

    # --- 2. quarantine columns the pipeline derives itself ------------------
    quarantined = {}
    for column in list(df.columns):
        if column in DERIVED_NOT_SUPPLIED:
            quarantined[column] = f"supplied_{column}"
    if quarantined:
        df = df.rename(columns=quarantined)
        report["warnings"].append(
            f"{len(quarantined)} column(s) supplied by the file duplicate fields the "
            f"pipeline derives from Description ({', '.join(quarantined)}). They were "
            "kept under a 'supplied_' prefix and are not used. Description parsing "
            "remains the source of truth."
        )
    report["columns_quarantined"] = quarantined

    # --- 3. required column validation --------------------------------------
    missing_hard = [c for c in HARD_REQUIRED if c not in df.columns]
    missing_soft = [c for c in SOFT_REQUIRED if c not in df.columns]
    report["missing_hard"] = missing_hard
    report["missing_soft"] = missing_soft

    if missing_hard:
        report["errors"].append(
            "Required column(s) missing and not identifiable from the headers: "
            + ", ".join(missing_hard)
        )
    if report["errors"]:
        report["status"] = "blocked"
        report["rows_out"] = 0
        report["columns_out"] = []
        return df, report

    for column in missing_soft:
        df[column] = pd.NA
        report["warnings"].append(
            f"Optional-but-expected column '{column}' is absent. It was created empty. "
            "Measures that depend on it will be blank."
        )

    # --- 4. exact duplicates, decided on the file as supplied ---------------
    # This must happen BEFORE unused columns are removed. Two rows that are
    # identical across the kept columns but differ in a removed one (a dispute
    # flag, say) are two real transactions, not a duplicate. Deciding after
    # removal would silently delete one of them.
    full_duplicates = int(df.duplicated().sum())
    if full_duplicates:
        df = df[~df.duplicated()].reset_index(drop=True)
    report["duplicates_removed"] = full_duplicates
    report["duplicate_decision_columns"] = len(df.columns)

    # --- 5. dispute and unused columns --------------------------------------
    dispute_columns = [c for c in df.columns if DISPUTE_PATTERN.search(str(c))]
    report["dispute_columns_found"] = dispute_columns

    keep = HARD_REQUIRED + SOFT_REQUIRED + [
        c for c in KNOWN_OPTIONAL if c in df.columns and c not in dispute_columns
    ]
    keep = list(dict.fromkeys(keep))
    dropped = [c for c in df.columns if c not in keep]
    report["columns_removed"] = {
        column: (
            "dispute tracking, out of scope for merchant insight"
            if column in dispute_columns
            else "not used by any downstream stage"
        )
        for column in dropped
    }
    df = df[keep]

    # --- 6. missing values (measured before any parsing) --------------------
    report["missing_values"] = {
        column: int(df[column].isna().sum())
        for column in df.columns
        if df[column].isna().any()
    }
    report["rows_missing_required"] = int(df[HARD_REQUIRED].isna().any(axis=1).sum())

    # --- 7. dates -----------------------------------------------------------
    date_report = {}
    for column in ("Txn date", "Posting Date"):
        parsed, failed, order = parse_dates(df[column])
        df[column] = parsed
        date_report[column] = {
            "unparsed": failed,
            "order": order,
            "min": parsed.min(),
            "max": parsed.max(),
        }
        if failed:
            report["warnings"].append(
                f"{failed:,} value(s) in '{column}' could not be read as a date and are blank."
            )
    report["date_parsing"] = date_report

    # --- 8. amounts ---------------------------------------------------------
    amount_before = df["Amount"].dtype
    parsed_amount, amount_failed = parse_amount(df["Amount"])
    df["Amount"] = parsed_amount
    report["amount_parsing"] = {
        "dtype_before": str(amount_before),
        "dtype_after": str(df["Amount"].dtype),
        "unparsed": amount_failed,
        "negative_values": int((df["Amount"] < 0).sum()),
        "zero_values": int((df["Amount"] == 0).sum()),
        "min": float(df["Amount"].min()) if df["Amount"].notna().any() else None,
        "max": float(df["Amount"].max()) if df["Amount"].notna().any() else None,
    }
    if amount_failed:
        report["warnings"].append(
            f"{amount_failed:,} value(s) in 'Amount' could not be read as a number and are blank."
        )

    # --- 9. debit / credit --------------------------------------------------
    normalised, unresolved, value_map = normalise_debit_credit(df["DB/CR"])
    df["DB/CR"] = normalised
    report["debit_credit"] = {
        "value_map": {k: v for k, v in value_map.items() if k != v},
        "counts": df["DB/CR"].value_counts(dropna=False).to_dict(),
        "unresolved": unresolved,
    }
    if unresolved:
        report["warnings"].append(
            f"{unresolved:,} row(s) have a DB/CR value that is neither debit nor credit. "
            "They were left as-is and will not be counted as debit spend."
        )

    # --- 10. text fields ----------------------------------------------------
    blank_descriptions = int(
        df["Description"].isna().sum()
        + (df["Description"].astype(str).str.strip() == "").sum()
    )
    report["blank_descriptions"] = blank_descriptions
    if blank_descriptions:
        report["warnings"].append(
            f"{blank_descriptions:,} row(s) have no Description. No merchant can be "
            "extracted from them; they resolve to 'unknown'."
        )

    if "Currency" in df.columns and df["Currency"].notna().any():
        currency_counts = df["Currency"].value_counts().to_dict()
        report["currencies"] = currency_counts
        if len(currency_counts) > 1:
            report["warnings"].append(
                f"{len(currency_counts)} currencies present. Every amount is treated as "
                "EGP; no FX conversion is applied."
            )
    else:
        report["currencies"] = {}

    # --- 11. residual duplicate reporting -----------------------------------
    exact = int(df.duplicated().sum())  # after removal; expected 0
    business_key = ["PAN", "Txn date", "Amount", "Description"]
    business = int(df.duplicated(subset=business_key).sum())
    report["duplicates"] = {
        "removed": full_duplicates,
        "decided_on_columns": report["duplicate_decision_columns"],
        "residual_exact": exact,
        "business_key": business,
        "business_key_columns": business_key,
    }
    if business > exact:
        report["warnings"].append(
            f"{business - exact:,} row(s) repeat the same PAN, date, amount and "
            "description but differ elsewhere. They are kept; only fully identical "
            "rows are removed."
        )

    report["rows_out"] = len(df)
    report["columns_out"] = list(df.columns)
    report["column_count_out"] = len(df.columns)
    report["status"] = "warned" if report["warnings"] else "ok"
    return df, report


def cleaning_summary(std_report: dict, clean_report: dict | None = None) -> list[dict]:
    """Flatten both reports into display rows for the Stage Cleaning page.

    Every value is computed from the file that was actually uploaded. Each row
    is {step, finding, detail, level}, where level is ok, info or warn.
    """
    rows: list[dict] = []

    def add(step, finding, detail="", level="ok"):
        rows.append({"step": step, "finding": finding, "detail": detail, "level": level})

    s, c = std_report, clean_report or {}

    add("Rows received", f"{s['rows_in']:,} rows",
        f"{s['column_count_in']} columns in the uploaded file", "info")

    if c:
        removed = s.get("duplicates", {}).get("removed", c["duplicates_removed"])
        add("Rows after cleaning", f"{c['rows_out']:,} rows",
            f"{removed:,} fully duplicate row(s) removed",
            "warn" if removed else "ok")

    mapped = s.get("columns_mapped", {})
    add("Column mapping",
        f"{len(mapped)} column(s) renamed" if mapped else "No renaming needed",
        "; ".join(f"{k} -> {v}" for k, v in mapped.items()) or
        "Headers already match the expected schema",
        "info" if mapped else "ok")

    if s.get("columns_ambiguous"):
        add("Ambiguous columns", f"{len(s['columns_ambiguous'])} unresolved",
            "; ".join(f"{k}: {', '.join(v)}" for k, v in s["columns_ambiguous"].items()),
            "warn")

    if s.get("missing_soft"):
        add("Expected columns absent", ", ".join(s["missing_soft"]),
            "Created empty. Dependent measures will be blank.", "warn")

    removed = s.get("columns_removed", {})
    disputes = s.get("dispute_columns_found", [])
    add("Columns removed",
        f"{len(removed)} removed" if removed else "None removed",
        "; ".join(f"{k} ({v})" for k, v in removed.items()) or "Every column was used",
        "info" if removed else "ok")
    if disputes:
        add("Dispute fields", f"{len(disputes)} found and removed",
            ", ".join(disputes), "info")

    add("Standardised columns", f"{s.get('column_count_out', 0)} columns",
        ", ".join(s.get("columns_out", [])), "info")

    missing = s.get("missing_values", {})
    add("Missing values",
        f"{sum(missing.values()):,} blank cell(s)" if missing else "No blank cells",
        "; ".join(f"{k}: {v:,}" for k, v in missing.items()) or
        "Every cell populated across the standardised columns",
        "warn" if s.get("rows_missing_required") else ("info" if missing else "ok"))

    dup = s.get("duplicates", {})
    add("Duplicates",
        f"{dup.get('removed', 0):,} fully identical row(s) removed, "
        f"{dup.get('business_key', 0):,} repeat on the business key",
        f"Identical is judged across all {dup.get('decided_on_columns', 0)} columns as "
        "supplied, before any are dropped. Business key: "
        + ", ".join(dup.get("business_key_columns", [])),
        "warn" if dup.get("business_key") else "ok")

    for column, detail in s.get("date_parsing", {}).items():
        span = ""
        if pd.notna(detail.get("min")) and pd.notna(detail.get("max")):
            span = f"{detail['min']:%Y-%m-%d} to {detail['max']:%Y-%m-%d}"
        add(f"Date parsing: {column}",
            "All values parsed" if not detail["unparsed"]
            else f"{detail['unparsed']:,} unparsed",
            f"{span} (read as {detail['order']})".strip(),
            "warn" if detail["unparsed"] else "ok")

    amount = s.get("amount_parsing", {})
    add("Amount parsing",
        "All values parsed" if not amount.get("unparsed")
        else f"{amount['unparsed']:,} unparsed",
        f"{amount.get('dtype_before')} -> {amount.get('dtype_after')}; "
        f"{amount.get('negative_values', 0):,} negative, "
        f"{amount.get('zero_values', 0):,} zero",
        "warn" if amount.get("unparsed") else "ok")

    dbcr = s.get("debit_credit", {})
    counts = ", ".join(f"{k}: {v:,}" for k, v in dbcr.get("counts", {}).items())
    recoded = dbcr.get("value_map", {})
    add("Debit/Credit normalisation",
        f"{len(recoded)} value(s) recoded" if recoded else "Already normalised",
        (("; ".join(f"{k} -> {v}" for k, v in recoded.items()) + ". ") if recoded else "")
        + counts,
        "warn" if dbcr.get("unresolved") else "ok")

    if s.get("currencies"):
        add("Currency", f"{len(s['currencies'])} currency value(s)",
            ", ".join(f"{k}: {v:,}" for k, v in s["currencies"].items()),
            "warn" if len(s["currencies"]) > 1 else "ok")

    if c:
        add("Description parsing",
            f"{c['rows_out'] - c['unknown_rows']:,} of {c['rows_out']:,} rows resolved "
            f"to a merchant",
            f"{c['international_rows']:,} international; "
            f"geography resolved on {c['geography_parse_rate']:.1%} of domestic rows",
            "warn" if c["unknown_rows"] else "ok")

        add("Merchant extraction",
            f"{c['known_merchants']} known, {c['new_merchants']} new, "
            f"{c['unknown_merchants']} unresolvable",
            f"{c['known_rows']:,} known rows, {c['new_rows']:,} new rows, "
            f"{c['unknown_rows']:,} unresolvable rows. "
            f"{len(c['auto_corrections'])} name(s) auto-corrected onto the reference list.",
            "warn" if c["unknown_merchants"] else "ok")

        add("Category resolution",
            f"{c['category_mapped']:,} mapped, {c['category_inferred']:,} inferred, "
            f"{c['category_unknown']:,} unknown",
            "Mapped comes from the reference list; inferred comes from keyword rules "
            "and is never presented as mapped.",
            "warn" if c["category_unknown"] else "ok")

        geo = c.get("geo_confidence_counts", {})
        add("Geography extraction",
            ", ".join(f"{k}: {v:,}" for k, v in geo.items()) or "No geography parsed",
            f"{c['low_confidence_rows']:,} row(s) low confidence. "
            f"{len(c['city_candidates'])} possible unrecognised city name(s) detected.",
            "warn" if c["low_confidence_rows"] else "ok")

        add("Outliers", f"{c['outliers_flagged']:,} high-value transactions flagged",
            f"Tukey fence recomputed from this file: above "
            f"{c['outlier_threshold']:,.2f}", "info")

        add("Coverage", f"{c['cardholders']:,} cardholders, {c['merchants_total']} merchants",
            f"{c['months_covered']} month(s), "
            f"{c['date_min']:%Y-%m-%d} to {c['date_max']:%Y-%m-%d}", "info")

    for warning in s.get("warnings", []):
        add("Warning", "Could not be resolved automatically", warning, "warn")
    for error in s.get("errors", []):
        add("Error", "Blocked", error, "warn")

    if not s.get("warnings") and not s.get("errors"):
        add("Unresolved issues", "None", "Nothing required manual intervention.", "ok")

    return rows
