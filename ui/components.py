"""
Reusable interface components.

Everything that draws a repeated visual pattern lives here so that `app.py`
reads as a sequence of screens rather than a wall of inline HTML, and so that
changing a card style is one edit rather than twenty.

Every function in this module is pure presentation. None of them compute a
metric, derive a threshold, or decide anything about the analysis: they take
values that the pipeline already produced and render them. If a component
needs a number that does not exist in a pipeline output, that is a signal to
stop, not to calculate it here.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

import pandas as pd
import streamlit as st

from . import scenes, theme


# --- formatting -------------------------------------------------------------

def egp(value: float | None) -> str:
    """Compact EGP. Carried over unchanged from the original app.py helper."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "n/a"
    if abs(value) >= 1_000_000_000:
        return f"EGP {value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"EGP {value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"EGP {value / 1_000:.0f}K"
    return f"EGP {value:,.0f}"


def fmt_measure(value, pattern: str, unavailable: str = "Not available") -> str:
    """Render a measure the loaded file may not be able to supply.

    A measure returns None when its input column is absent or entirely empty.
    That is a real state and is labelled as such, never shown as nan or as a
    misleading zero.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return unavailable
    return pattern.format(value)


def _esc(value) -> str:
    return html.escape(str(value))


def _render(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


# --- masthead and navigation ------------------------------------------------

def _logo_img(path: Path | None, css_class: str, alt: str) -> str:
    """Inline a logo as a base64 data URI.

    Embedding the bytes directly (rather than a bare file path, which the
    browser cannot resolve, or a separate st.image call, which cannot share
    a flex row with the surrounding markup) is what lets the two brand marks
    sit on one line, vertically centred, at a controlled height regardless
    of each PNG's native size.
    """
    if path is None or not Path(path).exists():
        return ""
    data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
    return f'<img class="{css_class}" src="data:image/png;base64,{data}" alt="{_esc(alt)}">'


def masthead(
    logo_path: Path | None,
    chips: list[tuple[str, str]],
    partner_logo_path: Path | None = None,
) -> None:
    """Application header.

    `chips` is [(label, style)] where style is '', 'gold', 'green' or 'idle'.
    `logo_path` (NBE) sits beside the wordmark; `partner_logo_path` (the
    Digital Egypt mark) sits on the opposite side, sized to match — a small
    co-brand mark, not a second headline logo.
    """
    chip_html = "".join(
        f'<span class="nbe-chip {style}">{_esc(label)}</span>' for label, style in chips
    )
    nbe_logo_html = _logo_img(logo_path, "nbe-masthead-logo", "National Bank of Egypt")
    partner_logo_html = _logo_img(
        partner_logo_path, "nbe-masthead-logo", "Digital Egypt Builders Initiative"
    )
    partner_block = (
        f'<div class="nbe-masthead-divider"></div>{partner_logo_html}'
        if partner_logo_html else ""
    )
    _render(
        f"""
        <div class="nbe-masthead">
          {nbe_logo_html}
          <div class="nbe-masthead-divider"></div>
          <div class="nbe-masthead-text">
            <div class="nbe-wordmark">NBE CARDLYTICS</div>
            <div class="nbe-tagline">
              Merchant Intelligence Platform &nbsp;·&nbsp; Customer &amp; Merchant Analytics
            </div>
          </div>
          <div class="nbe-chipset">{chip_html}</div>
          {partner_block}
        </div>
        """
    )


def journey(steps: list[str], current_index: int, nav_values: list[str],
            nav_key: str = "nav") -> None:
    """The workflow strip: badges that double as navigation.

    Steps before the current one read as done. Clicking a badge jumps
    straight to that screen by writing into the same `st.session_state`
    key the sidebar radio uses (`nav_key`, default "nav"), so the two
    controls can never disagree and anything driving navigation through
    that key (including the sidebar radio itself) keeps working unchanged.
    """
    def _go(value: str) -> None:
        st.session_state[nav_key] = value

    with st.container(key="nbe-journey-row"):
        columns = st.columns(len(steps), gap="small")
        for index, (label, column) in enumerate(zip(steps, columns)):
            if index < current_index:
                state = "done"
            elif index == current_index:
                state = "active"
            else:
                state = "upcoming"
            with column:
                with st.container(key=f"nbe-journey-{state}-{index}"):
                    st.button(
                        label,
                        key=f"nbe-journey-btn-{index}",
                        on_click=_go,
                        args=(nav_values[index],),
                        use_container_width=True,
                    )


def section(title: str, note: str = "") -> None:
    note_html = f'<span class="nbe-section-note">{_esc(note)}</span>' if note else ""
    _render(
        f'<div class="nbe-section">'
        f'<span class="nbe-section-title">{_esc(title)}</span>{note_html}</div>'
    )


def _current_step() -> int | None:
    """1-based position in the workflow, read from the navigation state."""
    value = str(st.session_state.get("nav", "")).strip()
    head = value.split(" ")[0]
    return int(head) if head.isdigit() else None


def page_title(title: str, subtitle: str = "") -> None:
    """Page banner: the screen's title, what it answers, and where it sits in
    the seven-step workflow."""
    step = _current_step()
    progress = ""
    if step:
        bars = "".join(
            f'<i class="{"on" if n <= step else ""}"></i>' for n in range(1, 8)
        )
        progress = (
            f'<div class="nbe-banner-step"><span class="nbe-banner-bars">{bars}</span>'
            f"Step {step} of 7</div>"
        )
    sub = f"<p>{_esc(subtitle)}</p>" if subtitle else ""
    _render(
        f'<div class="nbe-banner"><div class="nbe-banner-text">{progress}'
        f"<h1>{_esc(title)}</h1>{sub}</div>{scenes.scene(step)}</div>"
    )


def note(text: str) -> None:
    """A caption. Used for every methodology caveat carried over from the
    original screens, so none of them are lost to the redesign."""
    _render(f'<div class="nbe-note">{_esc(text)}</div>')


# --- KPI cards --------------------------------------------------------------

def kpis(cells: list[tuple]) -> None:
    """cells: (label, value, note, style) where style is '', 'accent',
    'good' or 'warn'. Replaces the old metric_strip with the same signature."""
    parts = ['<div class="nbe-kpis">']
    for label, value, sub, style in cells:
        parts.append(
            f'<div class="nbe-kpi {style}">'
            f'<div class="nbe-kpi-label">{_esc(label)}</div>'
            f'<div class="nbe-kpi-value">{_esc(value)}</div>'
            f'<div class="nbe-kpi-note">{_esc(sub)}</div></div>'
        )
    parts.append("</div>")
    _render("".join(parts))


# --- badges -----------------------------------------------------------------

BADGE_CLASS = {"known": "badge-known", "new": "badge-new", "unknown": "badge-unknown"}
STATUS_WORD = {"known": "Known", "new": "New", "unknown": "Unresolved"}


def merchant_badge(status: str) -> str:
    """HTML for a merchant_status badge.

    'new' gets the gold accent, never a warning colour: a merchant absent from
    the reference list is a real merchant, not a problem.
    """
    key = str(status)
    return (
        f'<span class="badge {BADGE_CLASS.get(key, "badge-known")}">'
        f'{_esc(STATUS_WORD.get(key, key.title()))}</span>'
    )


# --- insight cards ----------------------------------------------------------

def insight(headline: str, body: str = "", kicker: str = "Key insight",
            style: str = "") -> None:
    """One dynamically computed insight.

    `headline` and `body` must always come from a pipeline output. Nothing in
    this function invents a claim.
    """
    body_html = f'<div class="nbe-insight-body">{body}</div>' if body else ""
    _render(
        f'<div class="nbe-insight {style}">'
        f'<div class="nbe-insight-kicker">{_esc(kicker)}</div>'
        f'<div class="nbe-insight-headline">{_esc(headline)}</div>'
        f"{body_html}</div>"
    )


def insight_list(lines: list[str], kicker: str = "What the data shows",
                 style: str = "") -> None:
    """Render the existing insights.py sentences as cards rather than bullets.

    The text is unchanged; only its presentation is.
    """
    for line in lines:
        insight(line, kicker=kicker, style=style)


# --- profile cards ----------------------------------------------------------

def profile_card(title: str, subtitle: str, metrics: list[tuple[str, str]],
                 accent: str | None = None, badge_html: str = "") -> None:
    """A segment, cluster, or any other named profile with its key figures."""
    border = f"border-left-color:{accent};--ac:{accent};" if accent else ""
    metric_html = "".join(
        f'<div class="nbe-metric"><div class="nbe-metric-k">{_esc(k)}</div>'
        f'<div class="nbe-metric-v">{_esc(v)}</div></div>'
        for k, v in metrics
    )
    _render(
        f'<div class="nbe-card" style="{border}">'
        f'<div class="nbe-card-title">{_esc(title)} {badge_html}</div>'
        f'<div class="nbe-card-sub">{_esc(subtitle)}</div>'
        f'<div class="nbe-card-metrics">{metric_html}</div></div>'
    )


def rank_row(rank: int, name: str, meta: str, score_label: str,
             score_value: str, badge_html: str = "") -> None:
    """One row of a strategic ranking."""
    top = "top" if rank <= 3 else ""
    _render(
        f'<div class="nbe-rank">'
        f'<div class="nbe-rank-no {top}">{rank}</div>'
        f'<div class="nbe-rank-main">'
        f'<div class="nbe-rank-name">{_esc(name)} {badge_html}</div>'
        f'<div class="nbe-rank-meta">{_esc(meta)}</div></div>'
        f'<div class="nbe-rank-score">'
        f'<div class="nbe-metric-k">{_esc(score_label)}</div>'
        f'<div class="nbe-metric-v">{_esc(score_value)}</div></div></div>'
    )


# --- cleaning status rows ---------------------------------------------------

def status_row(step: str, finding: str, detail: str, level: str) -> None:
    _render(
        f'<div class="nbe-status {_esc(level)}">'
        f'<div class="nbe-status-step">{_esc(step)}</div>'
        f'<div class="nbe-status-body">'
        f'<div class="nbe-status-finding">{_esc(finding)}</div>'
        f'<div class="nbe-status-detail">{_esc(detail)}</div></div></div>'
    )


# --- pipeline stepper -------------------------------------------------------

def pipeline_stepper(steps: list[tuple[str, str, bool]]) -> None:
    """steps: (name, note, done)."""
    parts = ['<div class="nbe-pipe">']
    for name, sub, done in steps:
        parts.append(
            f'<div class="nbe-pipe-step {"done" if done else ""}">'
            f'<div class="nbe-pipe-name">{_esc(name)}</div>'
            f'<div class="nbe-pipe-note">{_esc(sub)}</div></div>'
        )
    parts.append("</div>")
    _render("".join(parts))


# --- filter chips -----------------------------------------------------------

def filter_chips(active: dict, shown: int, total: int) -> None:
    parts = [
        f'<div class="nbe-filters">'
        f'<span class="nbe-filter-chip count">{shown:,} of {total:,} transactions</span>'
    ]
    for key, value in active.items():
        label = key.replace("_", " ").title()
        rendered = ", ".join(map(str, value)) if isinstance(value, list) else str(value)
        if len(rendered) > 42:
            rendered = rendered[:39] + "…"
        parts.append(f'<span class="nbe-filter-chip">{_esc(label)}: {_esc(rendered)}</span>')
    parts.append("</div>")
    _render("".join(parts))


# --- tables -----------------------------------------------------------------

def table(frame: pd.DataFrame, height: int | None = None) -> None:
    st.dataframe(frame, width="stretch", hide_index=True,
                 **({"height": height} if height else {}))


def footer() -> None:
    _render(
        '<div class="nbe-foot">NBE Cardlytics · Merchant Intelligence<br>'
        "Prototype for graduation review. No authentication, no persistence, "
        "single currency (EGP).</div>"
    )


def team_footer(names: list[str]) -> None:
    """Closing strip at the very end of every page: the team members."""
    dot = '<span style="color:#00704A;margin:0 10px">&bull;</span>'
    people = dot.join(
        f'<span style="font-weight:800;color:#0B2A3B">{_esc(n)}</span>' for n in names
    )
    _render(
        '<div style="margin:56px 0 12px;padding-top:18px;text-align:center;'
        'border-top:1px solid rgba(11,42,59,.12)">'
        '<div style="font-size:11px;font-weight:800;letter-spacing:.14em;'
        'color:#5C6660;margin-bottom:8px">TEAM MEMBERS</div>'
        f'<div style="font-size:16px">{people}</div></div>'
    )
