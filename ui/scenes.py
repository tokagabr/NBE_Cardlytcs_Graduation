"""
Animated banner scenes: one small picture per workflow step.

Frontend only. Nothing here reads or computes data; each scene is a fixed
illustration of what that step does, drawn as inline SVG and animated with
CSS (keyframes live in ui.theme.CSS_V3). Every element is drawn in its
finished state, and the animation only adds the "before" frame, so with
reduced motion switched on the page shows the finished picture.

  1 Load         rows flow into a table and fill it
  2 Data quality a scan line passes over the grid, strays snap into place,
                 duplicates disappear
  3 Overview     monthly bars grow and a trend line is drawn
  4 Segments     scattered cardholders sort into Low-Value, Mass and VIP
  5 Clustering   points are scanned, then gather into four groups
  6 Rankings     bars rank themselves and the top merchant is picked
  7 Methodology  a pulse walks the five stages of the method
"""

from __future__ import annotations

import random

LOOP = 8.0  # seconds per animation loop; must match the keyframes in theme.py

MINT, GOLD, SKY, WHITE = "#7FE8B8", "#F9A61A", "#8FB1FF", "#FFFFFF"
STRAY = "#FF8A6B"
DEEP = "#00452E"


def _svg(body: str) -> str:
    return (
        '<svg class="nbe-banner-art" viewBox="0 0 360 150" aria-hidden="true" '
        'preserveAspectRatio="xMaxYMid meet">'
        '<defs><linearGradient id="nbeScan" x1="0" x2="1">'
        f'<stop offset="0" stop-color="{GOLD}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{GOLD}" stop-opacity=".6"/></linearGradient></defs>'
        f"{body}</svg>"
    )


def _dot(cx, cy, r, fill, cls="", style="", opacity=None) -> str:
    op = f' fill-opacity="{opacity}"' if opacity is not None else ""
    st = f' style="{style}"' if style else ""
    return (f'<circle class="{cls}" cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}"{op}{st}/>')


def _scan_line() -> str:
    """The gold sweep from the landing hero, drawn as a trail plus a line."""
    return (
        '<g class="a-scan">'
        '<rect x="-12" y="6" width="32" height="138" fill="url(#nbeScan)"/>'
        f'<rect x="19" y="6" width="2" height="138" fill="{GOLD}"/></g>'
    )


def _scan_time(x: float) -> float:
    """Seconds into the loop at which the scan line reaches x (see aScan)."""
    return (0.06 + 0.5 * (x - 20) / 330) * LOOP


def _scatter(rnd: random.Random, cx: float, cy: float) -> tuple[float, float]:
    """Offset that places a point somewhere random on the canvas."""
    return rnd.uniform(14, 346) - cx, rnd.uniform(14, 136) - cy


# --- 1  Load ----------------------------------------------------------------

def _load() -> str:
    rnd = random.Random(3)
    out = [
        '<rect x="196" y="18" width="146" height="114" rx="18" fill="#fff" fill-opacity=".12" '
        'stroke="#fff" stroke-opacity=".4"/>',
        '<rect x="212" y="33" width="54" height="8" rx="4" fill="#fff" fill-opacity=".65"/>',
    ]
    widths = [70, 52, 84, 60, 76]
    for i, w in enumerate(widths):
        y = 55 + i * 15
        out.append(f'<rect x="212" y="{y}" width="30" height="7" rx="3.5" fill="#fff" fill-opacity=".3"/>')
        out.append(
            f'<rect class="a-barx" style="--d:{3.3 + i * 0.2:.2f}s" x="250" y="{y}" '
            f'width="{w}" height="7" rx="3.5" fill="{MINT}"/>'
        )
    for i in range(18):
        out.append(_dot(
            rnd.uniform(150, 190), rnd.uniform(24, 128), rnd.uniform(2.4, 4.4),
            WHITE if i % 3 else MINT, "a-fly",
            f"--sx:-{rnd.uniform(110, 170):.0f}px;--d:{i * 0.11:.2f}s;opacity:0",
        ))
    out.append(f'<circle class="a-pop" style="--d:2.2s" cx="326" cy="33" r="11" fill="{MINT}"/>')
    out.append(
        f'<path class="a-pop" style="--d:2.2s" d="M321 33l4 4 8-8" stroke="{DEEP}" stroke-width="2.6" '
        'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    return _svg("".join(out))


# --- 2  Data quality --------------------------------------------------------

def _quality() -> str:
    rnd = random.Random(8)
    cols, rows = 7, 4
    strays = {(1, 1), (3, 0), (4, 2), (5, 3), (2, 3), (6, 1)}
    out = [_scan_line()]
    for j in range(rows):
        for i in range(cols):
            cx, cy = 46 + i * 45, 30 + j * 30
            if (i, j) in strays:
                bx, by = rnd.choice([-1, 1]) * rnd.uniform(9, 15), rnd.choice([-1, 1]) * rnd.uniform(8, 12)
                delay = _scan_time(cx) - 0.33 * LOOP
                out.append(_dot(cx, cy, 6, MINT, "a-fix",
                                f"--bx:{bx:.0f}px;--by:{by:.0f}px;--d:{delay:.2f}s"))
            else:
                out.append(_dot(cx, cy, 5, WHITE, "", "", 0.82))
    # duplicate rows: visible until the scan reaches them, then gone
    for i, j in [(0, 0), (2, 1), (5, 2), (3, 3)]:
        cx, cy = 46 + i * 45 + 22, 30 + j * 30 + 15
        delay = _scan_time(cx) - 0.34 * LOOP
        out.append(_dot(cx, cy, 5, STRAY, "a-gone", f"--d:{delay:.2f}s;opacity:0"))
    return _svg("".join(out))


# --- 3  Executive overview --------------------------------------------------

def _overview() -> str:
    heights = [46, 60, 54, 70, 64, 84, 76, 92, 74, 100]
    out = ['<rect x="30" y="129" width="306" height="2" rx="1" fill="#fff" fill-opacity=".3"/>']
    pts = []
    for i, h in enumerate(heights):
        x = 36 + i * 30
        top = 128 - h
        fill = GOLD if i == len(heights) - 1 else WHITE
        op = "1" if i == len(heights) - 1 else ".85"
        out.append(
            f'<rect class="a-bar" style="--d:{i * 0.09:.2f}s" x="{x}" y="{top}" width="20" height="{h}" '
            f'rx="6" fill="{fill}" fill-opacity="{op}"/>'
        )
        pts.append((x + 10, top - 14 - (i % 3) * 2))
    path = "M" + " L".join(f"{x} {y}" for x, y in pts)
    out.append(f'<path class="a-draw" pathLength="1" d="{path}" fill="none" stroke="{MINT}" '
               'stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>')
    lx, ly = pts[-1]
    out.append(f'<circle class="a-pop" cx="{lx}" cy="{ly}" r="6" fill="{MINT}" stroke="#fff" stroke-width="2"/>')
    return _svg("".join(out))


# --- 4  Customer segments ---------------------------------------------------

def _gather(rnd, cx, cy, r, fill, delay) -> str:
    sx, sy = _scatter(rnd, cx, cy)
    return _dot(cx, cy, r, fill, "a-gather", f"--sx:{sx:.0f}px;--sy:{sy:.0f}px;--c:{fill};--d:{delay:.2f}s")


def _segments() -> str:
    rnd = random.Random(21)
    out = []
    tiers = [  # centre x, columns, count, colour, label
        (70, 6, 18, "#C9D3CE", "Low-Value"),
        (180, 4, 12, SKY, "Mass"),
        (290, 3, 6, GOLD, "VIP"),
    ]
    k = 0
    for cx, cols, count, colour, label in tiers:
        rows = -(-count // cols)
        for n in range(count):
            col, row = n % cols, n // cols
            x = cx + (col - (cols - 1) / 2) * 13
            y = 112 - row * 13
            out.append(_gather(rnd, x, y, 5.2, colour, (k % 6) * 0.07))
            k += 1
        out.append(
            f'<text x="{cx}" y="140" text-anchor="middle" font-size="12" font-weight="800" '
            f'fill="#fff" fill-opacity=".85">{label}</text>'
        )
    return _svg("".join(out))


# --- 5  Merchant clustering -------------------------------------------------

def _clustering() -> str:
    rnd = random.Random(11)
    groups = [(70, 44, MINT), (262, 40, GOLD), (92, 106, WHITE), (246, 104, SKY)]
    out = []
    k = 0
    for gx, gy, colour in groups:
        for _ in range(15):
            x = min(max(gx + rnd.gauss(0, 17), 12), 348)
            y = min(max(gy + rnd.gauss(0, 12), 12), 138)
            out.append(_gather(rnd, x, y, 2.6 + rnd.random() * 3.4, colour, (k % 8) * 0.06))
            k += 1
    out.append(_scan_line())
    return _svg("".join(out))


# --- 6  Strategic rankings --------------------------------------------------

def _rankings() -> str:
    widths = [214, 184, 158, 132, 106]
    out = []
    for i, w in enumerate(widths):
        y = 16 + i * 26
        top = i == 0
        out.append(
            f'<rect class="a-barx" style="--d:{i * 0.16:.2f}s" x="68" y="{y}" width="{w}" height="16" '
            f'rx="8" fill="{GOLD if top else WHITE}" fill-opacity="{1 if top else .7}"/>'
        )
        out.append(f'<circle cx="40" cy="{y + 8}" r="11" fill="{WHITE}" fill-opacity="{1 if top else .85}"/>')
        out.append(
            f'<text x="40" y="{y + 12.5}" text-anchor="middle" font-size="12" font-weight="800" '
            f'fill="{DEEP}">{i + 1}</text>'
        )
    out.append(f'<rect class="a-pop" style="--d:-1.5s" x="290" y="14" width="62" height="20" rx="10" fill="{MINT}"/>')
    out.append(
        f'<text class="a-pop" style="--d:-1.5s" x="321" y="28" text-anchor="middle" font-size="11" '
        f'font-weight="800" fill="{DEEP}">Top pick</text>'
    )
    return _svg("".join(out))


# --- 7  Methodology ---------------------------------------------------------

def _method() -> str:
    labels = ["Prepare", "Segment", "Cluster", "Score", "Compare"]
    xs = [44 + i * 68 for i in range(5)]
    out = ['<rect x="44" y="60" width="272" height="3" rx="1.5" fill="#fff" fill-opacity=".3"/>']
    for i, (x, label) in enumerate(zip(xs, labels)):
        delay = (0.06 + 0.6 * i / 4) * LOOP
        out.append(f'<circle cx="{x}" cy="61.5" r="16" fill="none" stroke="#fff" stroke-opacity=".65" stroke-width="2.5"/>')
        out.append(f'<circle class="a-node" style="--d:{delay:.2f}s" cx="{x}" cy="61.5" r="11" fill="{MINT}"/>')
        out.append(
            f'<text x="{x}" y="100" text-anchor="middle" font-size="12" font-weight="800" '
            f'fill="#fff" fill-opacity=".85">{label}</text>'
        )
    out.append(f'<circle class="a-travel" cx="44" cy="61.5" r="6.5" fill="{GOLD}" style="opacity:0"/>')
    return _svg("".join(out))


_BUILDERS = {1: _load, 2: _quality, 3: _overview, 4: _segments, 5: _clustering, 6: _rankings, 7: _method}
_CACHE: dict[int, str] = {}


def scene(step: int | None) -> str:
    """SVG for a workflow step (1 to 7); the clustering scene for anything else."""
    key = step if step in _BUILDERS else 5
    if key not in _CACHE:
        _CACHE[key] = _BUILDERS[key]()
    return _CACHE[key]
