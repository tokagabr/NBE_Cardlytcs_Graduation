"""
File loading and schema validation.

Reading is deliberately thin. All the real work of turning an arbitrary upload
into the pipeline's schema lives in `standardize.py`, so that the same logic
runs whether a file arrives through the app, through `verify.py`, or through a
test. This module only picks a reader and exposes the validation verdict the
Load screen needs before it decides whether to ask the user anything.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .clean import OPTIONAL_COLUMNS, REQUIRED_COLUMNS
from .standardize import (
    HARD_REQUIRED,
    SOFT_REQUIRED,
    resolve_columns,
    standardize,
)


def read_any(source, filename: str | None = None) -> pd.DataFrame:
    """Read an uploaded file or a path, choosing the reader by extension."""
    name = filename or getattr(source, "name", str(source))
    suffix = Path(name).suffix.lower()
    if suffix in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(source)
    if suffix in (".csv", ".txt"):
        return pd.read_csv(source, low_memory=False)
    raise ValueError(f"Unsupported file type '{suffix}'. Upload .xlsx or .csv.")


def validate(df: pd.DataFrame) -> dict:
    """Check the uploaded columns against what the pipeline needs.

    Returns a verdict of ok, mappable or blocked.

      ok        every required column is present under a name the pipeline
                already understands, or under a known alias
      mappable  a required column is missing but exactly one source column is
                a plausible match, so the user can confirm it
      blocked   a required column cannot be identified at all, or two columns
                both claim the same role. The app stops rather than guessing.
    """
    present = list(df.columns)
    resolution = resolve_columns(present)
    resolved = set(resolution["resolved"])

    missing = [c for c in HARD_REQUIRED if c not in resolved]
    ambiguous = resolution["ambiguous"]

    # Anything still missing gets one last chance against the leftover columns,
    # offered to the user as a suggestion rather than applied silently.
    import difflib

    leftover = resolution["unmatched"]
    suggestions = {}
    for column in missing:
        close = difflib.get_close_matches(column, leftover, n=1, cutoff=0.6)
        if close:
            suggestions[column] = close[0]

    unmapped = [c for c in missing if c not in suggestions]

    if ambiguous or unmapped:
        status = "blocked"
    elif missing:
        status = "mappable"
    else:
        status = "ok"

    return {
        "status": status,
        "rows": len(df),
        "columns": present,
        "missing": missing,
        "suggestions": suggestions,
        "unmapped": unmapped,
        "ambiguous": ambiguous,
        "auto_mapped": {s: t for s, t in resolution["mapping"].items() if s != t},
        "optional_missing": [
            c for c in SOFT_REQUIRED + OPTIONAL_COLUMNS if c not in resolved
        ],
        "required": HARD_REQUIRED,
        "required_full": REQUIRED_COLUMNS,
    }


def apply_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Rename uploaded columns to the names the pipeline expects."""
    return df.rename(columns={source: target for target, source in mapping.items() if source})


def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Run the full standardisation phase. Returns (standardised frame, report)."""
    return standardize(df)
