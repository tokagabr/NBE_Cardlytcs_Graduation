"""
Design tokens for the NBE Cardlytics interface.

THIS IS THE SINGLE SOURCE OF TRUTH FOR COLOUR. Before this file existed,
`app.py` and `pipeline/charts.py` each declared their own palette and the two
had drifted: app.py used #006547 for every heading while charts.py used
#10312B, and the two golds differed as well. Everything now imports from here.

Palette discipline, which is what keeps the result restrained rather than
"green everywhere":

    NAVY    structure. Headings, KPI values, body text, chart ink.
    GREEN   action and affirmation only. Primary buttons, active nav,
            completed pipeline steps, "passed" status. Never decoration.
    GOLD    one accent per view. The `new` merchant badge, a single
            highlighted KPI, section rules. Never a fill for large areas.
    AMBER / RED   warning and issue states, nothing else.

The greens and golds are NBE's own brand values, carried over from the
original app.py constants and their Pantone references.
"""

from __future__ import annotations

# --- core palette -----------------------------------------------------------

NAVY = "#0B2A3B"        # headings, primary text, chart ink
NAVY_DEEP = "#071E2B"    # masthead background
NAVY_SOFT = "#2C4C5E"    # secondary headings

GREEN = "#00704A"        # NBE Leaf Green, Pantone 342 C. Actions and success.
GREEN_LIGHT = "#E6F0EC"  # success surface
GREEN_DARK = "#005C3C"   # hover / pressed

GOLD = "#F9A61A"         # NBE Gold/Orange, Pantone 1375 C. Single accent.
GOLD_LIGHT = "#FDF2E0"   # accent surface
GOLD_DEEP = "#8A5508"    # text on gold

AMBER = "#B4813F"        # warning
AMBER_LIGHT = "#FAF2E6"
RED = "#B4553F"          # issue
RED_LIGHT = "#F9ECE8"

BLUE = "#3A63B8"         # Mass segment, carried from the team's deck
GRAY = "#A8A8A8"         # Low-Value segment, carried from the team's deck
TEAL = "#12A06A"         # fourth cluster colour, carried over

SURFACE = "#FFFFFF"
CANVAS = "#EEF4F0"
RULE = "#E3E6E4"
RULE_STRONG = "#CBD2CE"
MUTED = "#5C6660"
MUTED_LIGHT = "#8A938D"

# Segment and cluster colours keep the values already used in the team's
# written report, so the app and the deck stay readable side by side.
SEGMENT_COLORS = {"Low-Value": GRAY, "Mass": BLUE, "VIP": GOLD}
CLUSTER_COLORS = {
    "VIP-Driven High-Value": GOLD,
    "Mass-Driven High-Reach": BLUE,
    "Frequent Low-Ticket": TEAL,
    "High-Ticket Opportunity": NAVY,
}

STATUS_COLORS = {
    "ok": GREEN,
    "info": NAVY_SOFT,
    "warn": AMBER,
    "issue": RED,
}

# --- chart sizing -----------------------------------------------------------
# Tuned for a 1366x768 laptop. The previous fixed heights totalled 6,620px
# across 16 figures, which made the Executive screen roughly four screens tall.

CHART_SM = 260
CHART_MD = 300
CHART_LG = 360
CHART_XL = 420

# --- elevation ---------------------------------------------------------------
# Two-layer shadows (a tight contact shadow plus a soft ambient one) read as
# considerably more "designed" than a single flat drop-shadow, at the same
# visual weight. Kept as named tokens so every card, chip and control pulls
# from the same three depths rather than each carrying its own one-off value.

SHADOW_XS = "0 1px 2px rgba(11,42,59,0.06)"
SHADOW_SM = "0 1px 2px rgba(11,42,59,0.04), 0 4px 10px rgba(11,42,59,0.06)"
SHADOW_MD = "0 2px 4px rgba(11,42,59,0.05), 0 10px 24px rgba(11,42,59,0.08)"
SHADOW_LIFT = "0 4px 10px rgba(11,42,59,0.07), 0 16px 32px rgba(11,42,59,0.10)"


def css() -> str:
    """Global stylesheet. Injected once by app.py.

    Every rule that carries the app's own text/background pairing carries
    `!important`. Streamlit's own theme (light or dark, laptop-dependent)
    otherwise wins ties against a plain class selector, which is what was
    producing navy-on-navy and white-on-white text in some widgets.
    """
    return f"""
<style>
  /* ---------- type ---------- */
  /* Plus Jakarta Sans for headings/numbers gives the financial-analytics
     "display" feel the brief asks for; Inter stays on body copy because it
     is the more neutral, more legible workhorse at small caption sizes.
     Both are loaded once, at the weights actually used, nothing else. */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;650;700&family=Plus+Jakarta+Sans:wght@600;700;750;800&display=swap');

  html, body, .stApp, [class*="css"] {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }}

  /* ---------- canvas ---------- */
  .stApp {{
      background:
        radial-gradient(1100px 520px at 12% -8%, rgba(0,101,71,0.05), transparent 60%),
        radial-gradient(900px 460px at 100% 0%, rgba(247,156,30,0.045), transparent 55%),
        {CANVAS} !important;
  }}
  .block-container {{
      padding-top: 1.15rem; padding-bottom: 2.75rem;
      max-width: 1500px;
  }}
  header[data-testid="stHeader"] {{ background: transparent; height: 0; }}

  /* ---------- native sidebar toggle vs. custom masthead ---------- */
  /* st.logo() is documented to always render the passed image in TWO
     places: the permanent upper-left corner of the app itself (which
     stays in the DOM even while the sidebar is open — Streamlit's sidebar
     panel just slides over it) and again inside the sidebar's own header.
     That first copy is what was duplicating the NBE mark next to the
     collapse/expand arrow, on top of our own masthead. The masthead
     already carries the NBE logo, so both native copies are hidden
     outright rather than relocated. `data-testid` names for this control
     have changed across Streamlit releases before (e.g. stSidebarNav ->
     stSidebar), so the hook used here is the `alt="Logo"` attribute
     Streamlit sets on the image itself, which is the more stable target.
     The arrow/toggle button is a separate element and is untouched — it
     keeps opening and closing the sidebar exactly as before. */
  img[alt="Logo"] {{
      display: none !important;
  }}

  h1, h2, h3, h4 {{
      color: {NAVY} !important; letter-spacing: -0.015em;
      font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
  }}
  h1 {{ font-size: 1.72rem; font-weight: 750; }}
  h2 {{ font-size: 1.22rem; font-weight: 700; }}
  h3 {{ font-size: 1.03rem; font-weight: 700; margin-bottom: 0.35rem; }}
  p, li, span, div, label {{ color: #22312C; }}
  .stMarkdown, .stMarkdown p {{ color: #22312C !important; }}

  /* ---------- masthead ---------- */
  /* Light surface, not a dark navy band: this is the bank's own pattern
     (white ground, green/gold accents) and it is what lets both partner
     marks render legibly, since neither logo file is drawn for a dark
     background. The 3px top rule is now a green-to-gold gradient rather
     than a flat fill -- a small, restrained way to put both brand colours
     in the same place without ever filling a large area with either. */
  .nbe-masthead {{
      background: {SURFACE}; border-radius: 14px; padding: 0.85rem 1.5rem;
      display: flex; align-items: center; gap: 1.1rem;
      margin-bottom: 0.5rem;
      border: 1px solid {RULE};
      border-top: 3px solid transparent;
      border-image: linear-gradient(90deg, {GREEN} 0%, {GREEN} 55%, {GOLD} 100%) 1;
      box-shadow: {SHADOW_SM};
      position: relative;
  }}
  .nbe-masthead-logo {{ height: 36px; width: auto; flex: 0 0 auto; display: block; }}
  .nbe-masthead-divider {{ width: 1px; align-self: stretch; background: {RULE};
                            flex: 0 0 auto; margin: 0.15rem 0; }}
  .nbe-masthead-text {{ flex: 1; min-width: 0; }}
  .nbe-wordmark {{
      color: {NAVY} !important; font-size: 1.14rem; font-weight: 750;
      letter-spacing: 0.055em; line-height: 1.15;
      font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .nbe-tagline {{
      color: {MUTED} !important; font-size: 0.76rem; margin-top: 0.2rem;
      letter-spacing: 0.01em;
  }}
  .nbe-chipset {{ display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap;
                  justify-content: flex-end; flex: 0 0 auto; }}
  .nbe-chip {{
      font-size: 0.68rem; font-weight: 650; padding: 0.28rem 0.7rem 0.28rem 0.6rem;
      border-radius: 20px; white-space: nowrap;
      background: {CANVAS} !important; color: {NAVY_SOFT} !important;
      border: 1px solid {RULE_STRONG};
      display: inline-flex; align-items: center; gap: 0.35rem;
  }}
  .nbe-chip::before {{
      content: ""; width: 6px; height: 6px; border-radius: 50%;
      background: {MUTED_LIGHT}; flex: 0 0 auto;
  }}
  .nbe-chip.gold {{ background: {GOLD_LIGHT} !important; color: {GOLD_DEEP} !important;
                     border-color: {GOLD}; }}
  .nbe-chip.gold::before {{ background: {GOLD}; }}
  .nbe-chip.green {{ background: {GREEN} !important; color: #FFFFFF !important;
                      border-color: {GREEN}; box-shadow: 0 2px 6px rgba(0,101,71,0.25); }}
  .nbe-chip.green::before {{ background: #FFFFFF; }}
  .nbe-chip.idle {{ color: {MUTED_LIGHT} !important; background: {SURFACE} !important; }}

  /* ---------- workflow badges (clickable breadcrumb) ---------- */
  /* Same visual language as the old static breadcrumb (upcoming/done/active
     colours, gold underline on the active step), rendered as real buttons
     so the badges double as navigation. Each badge sits in its own
     st.container(key=...), which is what lets these rules target one
     button at a time via the key-derived class Streamlit adds to that
     container div. */
  div[class*="st-key-nbe-journey-row"] {{
      padding: 0.45rem 0 0.5rem 0; border-bottom: 1px solid {RULE};
      margin-bottom: 0.6rem;
  }}
  div[class*="st-key-nbe-journey-"] div[data-testid="stButton"] > button {{
      background: transparent !important; border: 1px solid transparent !important;
      border-radius: 4px; box-shadow: none !important;
      font-size: 0.675rem !important; font-weight: 600 !important;
      letter-spacing: 0.005em; padding: 0.25rem 0.35rem !important;
      white-space: normal !important; line-height: 1.28 !important;
      overflow-wrap: break-word; word-break: break-word;
      min-height: 2.3rem; display: flex; align-items: center; justify-content: center;
      text-align: center;
  }}
  div[class*="st-key-nbe-journey-upcoming"] div[data-testid="stButton"] > button {{
      color: {MUTED_LIGHT} !important;
  }}
  div[class*="st-key-nbe-journey-done"] div[data-testid="stButton"] > button {{
      color: {GREEN} !important;
  }}
  div[class*="st-key-nbe-journey-active"] div[data-testid="stButton"] > button {{
      color: {NAVY} !important; font-weight: 700 !important;
      border-bottom: 2px solid {GOLD} !important; border-radius: 0;
  }}
  div[class*="st-key-nbe-journey-"] div[data-testid="stButton"] > button:hover {{
      color: {NAVY} !important; background: {CANVAS} !important;
  }}

  /* ---------- section heading ---------- */
  /* The small gold tick replaces a plain flat rule as the section marker --
     it is the "one accent per view" the palette calls for, used here to
     anchor visual hierarchy rather than as decoration. */
  .nbe-section {{
      display: flex; align-items: baseline; gap: 0.65rem;
      margin: 1.6rem 0 0.6rem 0; padding-bottom: 0.35rem;
      border-bottom: 1px solid {RULE};
  }}
  .nbe-section::before {{
      content: ""; display: inline-block; width: 4px; height: 14px;
      background: {GOLD}; border-radius: 2px; flex: 0 0 auto;
      transform: translateY(1px);
  }}
  .nbe-section-title {{
      font-size: 0.96rem; font-weight: 700; color: {NAVY} !important;
      letter-spacing: 0.003em; font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .nbe-section-note {{ font-size: 0.74rem; color: {MUTED} !important; }}

  /* ---------- KPI cards ---------- */
  .nbe-kpis {{ display: flex; gap: 0.75rem; margin: 0.25rem 0 0.6rem 0;
               flex-wrap: wrap; }}
  .nbe-kpi {{
      flex: 1 1 0; min-width: 138px;
      background: linear-gradient(180deg, #FFFFFF 0%, #FCFDFC 100%) !important;
      border: 1px solid {RULE};
      border-radius: 12px; padding: 0.85rem 0.95rem 0.85rem 0.95rem;
      box-shadow: {SHADOW_SM};
      position: relative; overflow: hidden;
      transition: transform 160ms ease, box-shadow 160ms ease;
  }}
  .nbe-kpi::before {{
      content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, {NAVY} 0%, {NAVY_SOFT} 100%);
  }}
  .nbe-kpi:hover {{ transform: translateY(-2px); box-shadow: {SHADOW_MD}; }}
  .nbe-kpi.accent::before {{ background: linear-gradient(90deg, {GOLD} 0%, #FFC46B 100%); }}
  .nbe-kpi.good::before {{ background: linear-gradient(90deg, {GREEN} 0%, {TEAL} 100%); }}
  .nbe-kpi.warn::before {{ background: linear-gradient(90deg, {AMBER} 0%, {RED} 100%); }}
  .nbe-kpi-label {{
      font-size: 0.665rem; color: {MUTED} !important; text-transform: uppercase;
      letter-spacing: 0.06em; font-weight: 700; line-height: 1.3;
  }}
  .nbe-kpi-value {{
      font-size: 1.62rem; font-weight: 750; color: {NAVY} !important;
      line-height: 1.2; margin-top: 0.3rem;
      font-variant-numeric: tabular-nums;
      font-family: 'Plus Jakarta Sans', sans-serif; letter-spacing: -0.01em;
  }}
  .nbe-kpi-note {{ font-size: 0.69rem; color: {MUTED_LIGHT} !important; margin-top: 0.2rem;
                   line-height: 1.35; }}

  /* ---------- badges ---------- */
  .badge {{
      display: inline-block; padding: 0.1rem 0.46rem; border-radius: 5px;
      font-size: 0.65rem; font-weight: 700; margin-right: 0.3rem;
      letter-spacing: 0.03em; text-transform: uppercase; vertical-align: 1px;
  }}
  .badge-new {{ background: linear-gradient(135deg, {GOLD} 0%, #E8890F 100%) !important;
                color: #FFFFFF !important; box-shadow: 0 1px 4px rgba(247,156,30,0.35); }}
  .badge-known {{ background: #EDEFEE !important; color: {MUTED} !important;
                   border: 1px solid {RULE}; }}
  .badge-unknown {{ background: {RED_LIGHT} !important; color: {RED} !important;
                     border: 1px solid {RED}; }}

  /* ---------- insight cards ---------- */
  .nbe-insight {{
      background: {SURFACE} !important; border: 1px solid {RULE};
      border-left: 3px solid {NAVY_SOFT};
      border-radius: 10px; padding: 0.8rem 0.95rem; margin-bottom: 0.6rem;
      box-shadow: {SHADOW_XS};
      transition: box-shadow 160ms ease, transform 160ms ease;
  }}
  .nbe-insight:hover {{ box-shadow: {SHADOW_SM}; transform: translateY(-1px); }}
  .nbe-insight.accent {{ border-left-color: {GOLD}; }}
  .nbe-insight.good {{ border-left-color: {GREEN}; }}
  .nbe-insight.warn {{ border-left-color: {AMBER}; }}
  .nbe-insight-kicker {{
      display: inline-block; font-size: 0.62rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.07em;
      color: {MUTED} !important; background: {CANVAS}; border-radius: 4px;
      padding: 0.12rem 0.4rem; margin-bottom: 0.35rem;
  }}
  .nbe-insight-headline {{
      font-size: 0.86rem; font-weight: 650; color: {NAVY} !important; line-height: 1.44;
      font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .nbe-insight-body {{
      font-size: 0.76rem; color: {MUTED} !important; line-height: 1.5; margin-top: 0.32rem;
  }}
  .nbe-insight-body b {{ color: {NAVY_SOFT} !important; }}

  /* ---------- profile cards (segment / cluster / ranking) ---------- */
  .nbe-card {{
      background: {SURFACE} !important; border: 1px solid {RULE};
      border-radius: 11px; padding: 0.85rem 1rem; height: 100%;
      border-left: 3px solid {RULE_STRONG};
      box-shadow: {SHADOW_XS};
      transition: box-shadow 160ms ease, transform 160ms ease;
  }}
  .nbe-card:hover {{ box-shadow: {SHADOW_SM}; transform: translateY(-1px); }}
  .nbe-card-title {{
      font-size: 0.9rem; font-weight: 700; color: {NAVY} !important; line-height: 1.28;
      font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .nbe-card-sub {{ font-size: 0.71rem; color: {MUTED} !important; margin-top: 0.2rem;
                   line-height: 1.45; }}
  .nbe-card-metrics {{
      display: flex; flex-wrap: wrap; gap: 0.15rem 0.9rem; margin-top: 0.55rem;
      padding-top: 0.5rem; border-top: 1px solid {RULE};
  }}
  .nbe-metric {{ min-width: 74px; }}
  .nbe-metric-k {{ font-size: 0.615rem; color: {MUTED_LIGHT} !important;
                   text-transform: uppercase; letter-spacing: 0.045em; }}
  .nbe-metric-v {{ font-size: 0.83rem; font-weight: 650; color: {NAVY} !important;
                   font-variant-numeric: tabular-nums; }}

  /* ---------- ranking rows ---------- */
  .nbe-rank {{
      display: flex; align-items: center; gap: 0.8rem;
      background: {SURFACE} !important; border: 1px solid {RULE};
      border-radius: 10px; padding: 0.6rem 0.9rem; margin-bottom: 0.4rem;
      box-shadow: {SHADOW_XS};
      transition: box-shadow 160ms ease, transform 160ms ease, border-color 160ms ease;
  }}
  .nbe-rank:hover {{ box-shadow: {SHADOW_SM}; transform: translateY(-1px); border-color: {RULE_STRONG}; }}
  .nbe-rank-no {{
      font-size: 1.05rem; font-weight: 750; color: {NAVY} !important;
      min-width: 2.3rem; text-align: center;
      border-right: 1px solid {RULE}; padding-right: 0.6rem;
      font-variant-numeric: tabular-nums;
      font-family: 'Plus Jakarta Sans', sans-serif;
  }}
  .nbe-rank-no.top {{ color: {GOLD_DEEP} !important; position: relative; }}
  .nbe-rank-main {{ flex: 1; min-width: 0; }}
  .nbe-rank-name {{ font-size: 0.85rem; font-weight: 650; color: {NAVY} !important; }}
  .nbe-rank-meta {{ font-size: 0.69rem; color: {MUTED} !important; margin-top: 0.12rem; }}
  .nbe-rank-score {{ text-align: right; min-width: 84px; }}

  /* ---------- status rows (cleaning) ---------- */
  .nbe-status {{
      display: flex; gap: 0.75rem; align-items: flex-start;
      padding: 0.55rem 0.8rem; border-left: 3px solid {RULE};
      background: {SURFACE} !important; border-top: 1px solid {RULE};
      border-right: 1px solid {RULE}; border-bottom: 1px solid {RULE};
      margin-bottom: 0.32rem; border-radius: 10px;
      box-shadow: {SHADOW_XS};
  }}
  .nbe-status.ok {{ border-left-color: {GREEN}; }}
  .nbe-status.info {{ border-left-color: {NAVY_SOFT}; }}
  .nbe-status.warn {{ border-left-color: {AMBER}; background: {AMBER_LIGHT} !important; }}
  .nbe-status-step {{ font-size: 0.76rem; font-weight: 650; color: {NAVY} !important;
                      min-width: 178px; }}
  .nbe-status-body {{ flex: 1; min-width: 0; }}
  .nbe-status-finding {{ font-size: 0.76rem; color: {NAVY} !important; font-weight: 550; }}
  .nbe-status-detail {{ font-size: 0.695rem; color: {MUTED} !important; margin-top: 0.12rem;
                        line-height: 1.48; }}

  /* ---------- pipeline stepper ---------- */
  .nbe-pipe {{ display: flex; align-items: stretch; gap: 0.5rem;
               margin: 0.55rem 0 0.45rem 0; }}
  .nbe-pipe-step {{
      flex: 1; text-align: center; padding: 0.65rem 0.35rem;
      background: {SURFACE} !important; border: 1px solid {RULE};
      border-radius: 10px; position: relative;
      box-shadow: {SHADOW_XS};
  }}
  .nbe-pipe-step.done {{
      background: linear-gradient(180deg, {GREEN_LIGHT} 0%, #EEF6F2 100%) !important;
      border-color: #C9DFD6;
  }}
  .nbe-pipe-name {{ font-size: 0.72rem; font-weight: 650; color: {MUTED_LIGHT} !important;
                    letter-spacing: 0.03em; }}
  .nbe-pipe-step.done .nbe-pipe-name {{ color: {GREEN_DARK} !important; }}
  .nbe-pipe-note {{ font-size: 0.635rem; color: {MUTED_LIGHT} !important; margin-top: 0.14rem; }}

  /* ---------- filter chips ---------- */
  .nbe-filters {{ display: flex; gap: 0.35rem; flex-wrap: wrap;
                  align-items: center; margin-bottom: 0.6rem; }}
  .nbe-filter-chip {{
      font-size: 0.68rem; padding: 0.2rem 0.6rem; border-radius: 20px;
      background: {GREEN_LIGHT} !important; color: {GREEN_DARK} !important;
      border: 1px solid #C9DFD6; font-weight: 650;
  }}
  .nbe-filter-chip.count {{ background: {SURFACE} !important; color: {MUTED} !important;
                            border-color: {RULE}; font-weight: 600; box-shadow: {SHADOW_XS}; }}

  /* ---------- sidebar ---------- */
  section[data-testid="stSidebar"] {{
      background: {SURFACE} !important; border-right: 1px solid {RULE};
  }}
  section[data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}
  section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span,
  section[data-testid="stSidebar"] label {{ color: {NAVY} !important; }}
  .nbe-navhead {{
      font-size: 0.63rem; font-weight: 700; color: {MUTED_LIGHT} !important;
      text-transform: uppercase; letter-spacing: 0.1em;
      margin: 1rem 0 0.3rem 0; padding-top: 0.5rem;
      border-top: 1px solid {RULE};
  }}
  .nbe-navhead:first-child {{ border-top: none; padding-top: 0; margin-top: 0.2rem; }}

  /* The workflow radio IS the page switcher. It gets its own clearly
     clickable row, a visible hover state, and — the important part — a
     visible SELECTED state, so it is obvious a click changed the page even
     before the main content below has re-rendered. */
  section[data-testid="stSidebar"] div[role="radiogroup"] {{
      gap: 0.15rem; display: flex; flex-direction: column;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label {{
      padding: 0.55rem 0.65rem; border-radius: 8px; margin-bottom: 0;
      border-left: 3px solid transparent;
      cursor: pointer; transition: background 130ms ease, border-color 130ms ease;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {{
      background: {CANVAS} !important;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {{
      background: linear-gradient(90deg, {GREEN_LIGHT} 0%, #EEF6F2 100%) !important;
      border-left-color: {GREEN};
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {{
      color: {GREEN_DARK} !important; font-weight: 700;
  }}
  section[data-testid="stSidebar"] div[role="radiogroup"] p {{
      font-size: 0.8rem; color: {NAVY} !important; margin: 0;
  }}
  /* Radio captions (used on the demo-source and method pickers) render as a
     second, smaller paragraph under the label. Left at the same size and
     weight as the label above, the two lines read as one crowded block; this
     keeps the caption visibly secondary so the two don't blur together. */
  section[data-testid="stSidebar"] div[role="radiogroup"] > label > div {{
      display: flex; flex-direction: column; gap: 0.1rem;
  }}
  section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
  section[data-testid="stSidebar"] div[role="radiogroup"] label small {{
      font-size: 0.68rem !important; color: {MUTED_LIGHT} !important;
      font-weight: 400 !important; line-height: 1.35;
  }}

  /* ---------- controls ---------- */
  .stButton > button[kind="primary"] {{
      background: {GREEN} !important; border-color: {GREEN}; border-radius: 8px;
      font-weight: 650; color: #FFFFFF !important;
      box-shadow: 0 2px 8px rgba(0,101,71,0.28);
      transition: transform 130ms ease, box-shadow 130ms ease, background 130ms ease;
  }}
  /* The label inside a button is its own <p>/<span>, which the global
     `p, li, span, div, label {{ color: ... }}` rule above matches directly
     (not merely inherits into) — a same-specificity, later, non-!important
     rule still beats an inherited !important value. Without this, the
     button background stayed green but the text rendered in body-text
     navy instead of white. */
  .stButton > button[kind="primary"] p,
  .stButton > button[kind="primary"] span,
  .stButton > button[kind="primary"] div {{
      color: #FFFFFF !important;
  }}
  .stButton > button[kind="primary"]:hover {{
      background: {GREEN_DARK} !important; border-color: {GREEN_DARK};
      transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,101,71,0.34);
  }}
  .stButton > button[kind="primary"]:active {{ transform: translateY(0); }}
  .stButton > button[kind="secondary"] {{
      border-radius: 8px; border-color: {RULE_STRONG}; color: {NAVY} !important;
      font-weight: 600; transition: border-color 130ms ease, background 130ms ease;
  }}
  .stButton > button[kind="secondary"]:hover {{
      border-color: {NAVY_SOFT}; background: {CANVAS} !important;
  }}
  .stDownloadButton > button {{ border-radius: 8px; border-color: {RULE_STRONG};
                                color: {NAVY} !important; font-weight: 550;
                                font-size: 0.78rem; transition: border-color 130ms ease; }}
  .stDownloadButton > button:hover {{ border-color: {GREEN}; color: {GREEN_DARK} !important; }}

  /* ---------- upload dropzone ---------- */
  /* A modern data platform reads its upload area at a glance: what goes in,
     what happens next. Streamlit's own dropzone is restyled to sit on the
     same card language as the rest of the app rather than its default grey
     box, with a clearer hover affordance. */
  [data-testid="stFileUploaderDropzone"] {{
      background: {CANVAS} !important;
      border: 1.5px dashed {RULE_STRONG} !important;
      border-radius: 12px !important;
      transition: border-color 160ms ease, background 160ms ease;
  }}
  [data-testid="stFileUploaderDropzone"]:hover {{
      border-color: {GREEN} !important;
      background: {GREEN_LIGHT} !important;
  }}
  [data-testid="stFileUploaderDropzone"] button {{
      border-radius: 7px !important; border-color: {RULE_STRONG} !important;
      font-weight: 600 !important;
  }}
  [data-testid="stFileUploaderDropzoneInstructions"] span,
  [data-testid="stFileUploaderDropzoneInstructions"] small {{
      color: {NAVY} !important;
  }}
  [data-testid="stFileUploaderFile"] {{
      background: {SURFACE} !important; border: 1px solid {RULE};
      border-radius: 8px; box-shadow: {SHADOW_XS};
  }}

  /* ---------- alerts ---------- */
  /* Streamlit's default alert colours (a saturated blue/red/orange) sit
     outside the NBE palette entirely. Restyled onto the same card system --
     rounded corners, a left accent bar, the house status colours -- so an
     upload error or a validation warning reads as part of this product
     rather than a generic framework message. */
  div[data-testid="stAlert"] {{
      border-radius: 10px !important; border: 1px solid {RULE} !important;
      box-shadow: {SHADOW_XS}; overflow: hidden;
  }}
  /* The border-left below sits on the same flex box that already holds the
     icon and text; without extra padding here, that border lands flush
     against the icon with no gap. Padding is added on all four sides so
     the border reads as a card edge rather than crowding the content. */
  div[data-testid="stAlertContentInfo"],
  div[data-testid="stAlertContentSuccess"],
  div[data-testid="stAlertContentWarning"],
  div[data-testid="stAlertContentError"] {{
      padding: 0.75rem 1rem 0.75rem 0.85rem !important;
  }}
  div[data-testid="stAlertContentInfo"] {{
      background: #EEF3F6 !important; border-left: 3px solid {NAVY_SOFT} !important;
  }}
  div[data-testid="stAlertContentSuccess"] {{
      background: {GREEN_LIGHT} !important; border-left: 3px solid {GREEN} !important;
  }}
  div[data-testid="stAlertContentWarning"] {{
      background: {AMBER_LIGHT} !important; border-left: 3px solid {AMBER} !important;
  }}
  div[data-testid="stAlertContentError"] {{
      background: {RED_LIGHT} !important; border-left: 3px solid {RED} !important;
  }}
  div[data-testid="stAlert"] p {{ color: {NAVY} !important; font-size: 0.83rem; }}

  div[data-testid="stDataFrame"] {{ border: 1px solid {RULE}; border-radius: 10px;
                                    box-shadow: {SHADOW_XS}; overflow: hidden; }}
  .stTabs [data-baseweb="tab-list"] {{ gap: 0.2rem; border-bottom: 1px solid {RULE}; }}
  .stTabs [data-baseweb="tab"] {{
      font-size: 0.8rem; font-weight: 600; color: {MUTED} !important;
      padding: 0.45rem 0.9rem; transition: color 130ms ease;
  }}
  .stTabs [aria-selected="true"] {{ color: {NAVY} !important; }}
  .stTabs [data-baseweb="tab-highlight"] {{ background-color: {GOLD} !important; height: 2.5px !important; }}
  div[data-testid="stExpander"] {{ border: 1px solid {RULE}; border-radius: 10px;
                                   background: {SURFACE} !important; box-shadow: {SHADOW_XS}; }}
  div[data-testid="stExpander"] summary {{ font-size: 0.79rem; font-weight: 600;
                                           color: {NAVY} !important; }}
  .stRadio [role="radiogroup"] {{ gap: 0.4rem; }}
  .nbe-foot {{ font-size: 0.66rem; color: {MUTED_LIGHT} !important; line-height: 1.5;
               border-top: 1px solid {RULE}; padding-top: 0.5rem;
               margin-top: 1rem; }}
  .nbe-note {{ font-size: 0.72rem; color: {MUTED} !important; line-height: 1.5;
               margin: 0.15rem 0 0.5rem 0; }}

  /* ---------- responsive ---------- */
  /* Every side-by-side layout in the app -- KPI rows, chart pairs, the
     upload/demo split -- is built on st.columns(), which renders as a single
     `stHorizontalBlock` flex row regardless of screen width. Wrapping that
     one element on narrow viewports stacks every such layout at once: KPI
     cards go full width, chart pairs stack vertically instead of
     compressing, and nothing clips or overlaps, without touching a single
     st.columns() call in app.py. */
  @media (max-width: 900px) {{
      .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
      div[data-testid="stHorizontalBlock"] {{
          flex-direction: column !important;
      }}
      div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
          width: 100% !important; flex: 1 1 100% !important;
      }}
      .nbe-masthead {{ flex-wrap: wrap; padding: 0.75rem 1rem; }}
      .nbe-chipset {{ justify-content: flex-start; width: 100%; }}
      .nbe-kpi {{ min-width: 100%; }}
      h1 {{ font-size: 1.4rem; }}
  }}
  /* The journey strip is itself an `stHorizontalBlock` (one column per
     step); it is exempt from the stack-everything rule above; a workflow
     strip is a poor place for a scrolling breadcrumb but reads worse the
     other way. */
  @media (max-width: 900px) {{
      div[class*="st-key-nbe-journey-row"] div[data-testid="stHorizontalBlock"] {{
          flex-direction: row !important; overflow-x: auto;
      }}
      div[class*="st-key-nbe-journey-row"] div[data-testid="stColumn"] {{
          width: auto !important; flex: 0 0 auto !important; min-width: 92px;
      }}
  }}
</style>
"""


CSS_V2 = """
<style>
  /* Presentation layer v2. Appended AFTER css(), so it wins on equal
     specificity. Pure restyle: no markup, data or logic is touched.
     To go back to the previous look, remove the css_v2() call in app.py. */
  @import url('https://fonts.googleapis.com/css2?family=Urbanist:wght@400;500;600;700;800&display=swap');
  :root{--n:#00704A;--n2:#12A06A;--ink:#0B2A3B;--gold:#F9A61A;--blue:#3A63B8;
        --ln:rgba(11,42,59,.1);--sh:0 14px 38px rgba(11,42,59,.08)}
  html, body, .stApp, [class*="css"]{font-family:'Urbanist','Inter',sans-serif !important}
  h1,h2,h3,h4,.nbe-wordmark,.nbe-kpi-value,.nbe-card-title,.nbe-section-title,
  .nbe-rank-score,.nbe-insight-headline{font-family:'Urbanist','Inter',sans-serif !important}
  .stApp{background:linear-gradient(135deg,#EEF4F0,#F6F0E6) fixed !important}
  .block-container{max-width:1500px;padding-top:1.4rem}
  h1{font-size:2.3rem !important;font-weight:800 !important;letter-spacing:-.03em !important}
  @keyframes nbeUp{from{opacity:0;transform:translateY(22px)}}
  @keyframes nbeFade{from{opacity:0}}

  /* masthead */
  .nbe-masthead{border:1px solid var(--ln) !important;border-image:none !important;
      border-radius:26px !important;box-shadow:var(--sh) !important;
      padding:.9rem 1.5rem !important;animation:nbeFade .6s ease}
  .nbe-wordmark{font-weight:800 !important;letter-spacing:.04em !important}
  .nbe-chip{border-radius:999px !important;font-weight:700 !important;transition:transform .25s}
  .nbe-chip:hover{transform:translateY(-2px)}
  .nbe-chip.green{background:linear-gradient(135deg,var(--n2),var(--n)) !important}

  /* workflow badges become a pill nav */
  div[class*="st-key-nbe-journey-row"]{background:#fff;border-radius:999px;padding:6px 10px !important;
      box-shadow:var(--sh);border:1px solid var(--ln) !important;margin-bottom:1.3rem !important}
  div[class*="st-key-nbe-journey-"] div[data-testid="stButton"] > button{
      border-radius:999px !important;
      transition:transform .25s,background .25s,color .25s,box-shadow .25s}
  div[class*="st-key-nbe-journey-"] div[data-testid="stButton"] > button:hover{
      transform:translateY(-2px);background:rgba(11,42,59,.05) !important}
  div[class*="st-key-nbe-journey-active"] div[data-testid="stButton"] > button{
      background:var(--n) !important;border:0 !important;border-radius:999px !important;
      box-shadow:0 8px 18px -6px var(--n) !important}
  div[class*="st-key-nbe-journey-active"] div[data-testid="stButton"] > button *{color:#fff !important}

  /* section headings */
  .nbe-section{border-bottom:0 !important;margin-top:2rem !important}
  .nbe-section-title{font-size:1.25rem !important;font-weight:800 !important;letter-spacing:-.01em !important}
  .nbe-section::before{width:10px !important;height:10px !important;border-radius:50% !important;
      background:linear-gradient(135deg,var(--n2),var(--gold)) !important;transform:none !important}

  /* KPI cards */
  .nbe-kpi{border-radius:22px !important;border:1px solid var(--ln) !important;
      box-shadow:var(--sh) !important;
      transition:transform .35s,box-shadow .35s,border-color .35s;
      animation:nbeUp .7s cubic-bezier(.2,.7,.2,1) backwards}
  .nbe-kpi:nth-child(2){animation-delay:.06s}.nbe-kpi:nth-child(3){animation-delay:.12s}
  .nbe-kpi:nth-child(4){animation-delay:.18s}.nbe-kpi:nth-child(5){animation-delay:.24s}
  .nbe-kpi:nth-child(6){animation-delay:.3s}.nbe-kpi:nth-child(7){animation-delay:.36s}
  .nbe-kpi:hover{transform:translateY(-6px);border-color:var(--n) !important;
      box-shadow:0 22px 40px -18px var(--n) !important}
  .nbe-kpi-value{font-weight:800 !important;font-size:1.9rem !important;letter-spacing:-.03em !important}

  /* cards, insights, rankings, status, pipeline */
  .nbe-card,.nbe-insight,.nbe-status,.nbe-pipe-step{border-radius:20px !important;
      box-shadow:var(--sh) !important;transition:transform .35s,box-shadow .35s,border-color .35s}
  .nbe-card:hover,.nbe-insight:hover,.nbe-status:hover{transform:translateY(-4px);
      box-shadow:0 22px 40px -20px var(--n) !important}
  .nbe-rank{border-radius:18px !important;transition:transform .3s,border-color .3s,box-shadow .3s}
  .nbe-rank:hover{transform:translateX(8px);border-color:var(--n) !important;box-shadow:var(--sh)}
  .nbe-card-title{font-weight:800 !important}

  /* buttons */
  .stButton > button[kind="primary"]{border-radius:18px !important;border:0 !important;
      background:linear-gradient(135deg,var(--n2),var(--n)) !important;font-weight:800 !important;
      min-height:3rem;box-shadow:0 14px 28px -12px var(--n) !important;
      transition:transform .3s,box-shadow .3s}
  .stButton > button[kind="primary"]:hover{transform:translateY(-3px) scale(1.01);
      box-shadow:0 20px 34px -12px var(--n) !important}
  .stButton > button[kind="secondary"]{border-radius:18px !important;font-weight:700 !important;
      transition:transform .25s,border-color .25s,box-shadow .25s}
  .stButton > button[kind="secondary"]:hover{transform:translateY(-2px);border-color:var(--n) !important}

  /* tabs as pills */
  .stTabs [data-baseweb="tab-list"]{background:#fff;border-radius:999px;padding:6px;gap:2px;
      border:1px solid var(--ln) !important;box-shadow:var(--sh);width:fit-content}
  .stTabs [data-baseweb="tab"]{border-radius:999px !important;padding:.5rem 1.1rem !important;
      font-weight:700 !important;height:auto !important;transition:background .25s,transform .25s}
  .stTabs [data-baseweb="tab"]:hover{background:rgba(11,42,59,.06);transform:translateY(-1px)}
  .stTabs [aria-selected="true"]{background:var(--n) !important;color:#fff !important}
  .stTabs [aria-selected="true"] *{color:#fff !important}
  .stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none !important}

  /* sidebar */
  section[data-testid="stSidebar"]{background:rgba(255,255,255,.72) !important;
      backdrop-filter:blur(8px);border-right:1px solid var(--ln)}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label{border-radius:999px !important;
      transition:transform .25s,background .25s}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover{
      transform:translateX(4px);background:rgba(11,42,59,.05) !important}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked){
      background:var(--n) !important}
  section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) *{color:#fff !important}

  /* charts, tables, expanders, uploader */
  div[data-testid="stPlotlyChart"]{background:#fff;border:1px solid var(--ln);border-radius:22px;
      padding:.5rem .6rem;box-shadow:var(--sh);transition:box-shadow .35s}
  div[data-testid="stPlotlyChart"]:hover{box-shadow:0 24px 44px -20px var(--n)}
  div[data-testid="stDataFrame"]{border-radius:18px !important;overflow:hidden;box-shadow:var(--sh)}
  div[data-testid="stExpander"]{border-radius:18px !important;background:#fff;box-shadow:var(--sh);
      transition:border-color .25s}
  div[data-testid="stExpander"]:hover{border-color:var(--n) !important}
  [data-testid="stFileUploaderDropzone"]{border-radius:22px !important;
      border:2px dashed var(--n2) !important;background:rgba(18,160,106,.05) !important;
      transition:background .25s,transform .25s}
  [data-testid="stFileUploaderDropzone"]:hover{background:rgba(18,160,106,.1) !important;
      transform:translateY(-2px)}

  @media (prefers-reduced-motion:reduce){*{animation:none !important;transition:none !important}}
</style>
"""


def css_v2() -> str:
    """Restyle layer. Inject right after css()."""
    return CSS_V2


CSS_V3 = """
<style>
  /* Presentation layer v3: carries the landing-page look into every screen.
     Appended AFTER css() and css_v2(). Pure restyle, no data or logic.
     Selectors use roles and data-testid so they hold across Streamlit
     versions. Remove the css_v3() call in app.py to go back to v2. */
  :root{--n:#00704A;--n2:#12A06A;--nd:#00452E;--ink:#0B2A3B;--mut:#5B6E68;
        --gold:#F9A61A;--blue:#3A63B8;--ln:rgba(11,42,59,.09);
        --sh:0 1px 2px rgba(11,42,59,.04),0 16px 36px -16px rgba(11,42,59,.16);
        --sh-up:0 2px 4px rgba(11,42,59,.05),0 26px 46px -18px rgba(0,112,74,.35)}

  /* ----- frame ----- */
  [data-testid="stAppDeployButton"],.stAppDeployButton{display:none !important}
  header[data-testid="stHeader"]{background:transparent !important}
  .block-container{max-width:1440px;padding-top:2.6rem !important;padding-bottom:4rem}
  .stApp{background:
      radial-gradient(900px 420px at 8% -6%,rgba(18,160,106,.10),transparent 60%),
      radial-gradient(820px 420px at 100% 4%,rgba(249,166,26,.10),transparent 60%),
      linear-gradient(135deg,#EEF4F0,#F6F0E6) fixed !important}
  .stApp p,.stApp li,.stApp label{font-size:1rem}
  ::selection{background:rgba(18,160,106,.28)}
  :focus-visible{outline:3px solid rgba(18,160,106,.55) !important;outline-offset:2px}

  /* ----- page banner: the one bold element on each screen ----- */
  .nbe-banner{position:relative;overflow:hidden;display:flex;align-items:center;
      justify-content:space-between;gap:2rem;min-height:150px;
      padding:1.7rem 2.2rem;margin:.2rem 0 1.6rem;border-radius:30px;color:#fff;
      background:radial-gradient(520px 260px at 92% 110%,rgba(249,166,26,.30),transparent 70%),
                 linear-gradient(118deg,#003A28 0%,#00704A 58%,#0F8F61 100%);
      box-shadow:0 30px 56px -28px rgba(0,80,52,.75),inset 0 1px 0 rgba(255,255,255,.18)}
  .nbe-banner-text{position:relative;z-index:1;max-width:min(62ch,100%)}
  .stApp .nbe-banner h1,.stApp .nbe-banner h1 *{color:#fff !important;margin:.5rem 0 .45rem !important;padding:0 !important;
      font-size:2.45rem !important;line-height:1.05 !important;letter-spacing:-.035em !important}
  .stApp .nbe-banner p{color:#D3EBDF !important;font-size:1.05rem !important;line-height:1.5;margin:0}
  .nbe-banner-step{display:inline-flex;align-items:center;gap:.7rem;color:#BFE6D3;
      font-size:.9rem;font-weight:700}
  .nbe-banner-bars{display:inline-flex;gap:4px}
  .nbe-banner-bars i{display:block;width:18px;height:5px;border-radius:5px;background:rgba(255,255,255,.22)}
  .nbe-banner-bars i.on{background:var(--gold)}
  .nbe-banner-art{flex:0 0 auto;width:min(380px,40%);height:auto;max-height:150px}
  @media (max-width:900px){.nbe-banner-art{display:none}.nbe-banner h1{font-size:1.9rem !important}}

  /* ----- section headings ----- */
  .nbe-section{display:flex !important;align-items:baseline;gap:.8rem;flex-wrap:wrap;
      margin:2.4rem 0 1rem !important;padding:0 !important;border:0 !important}
  .nbe-section::before{content:"";align-self:center;flex:0 0 auto;width:6px !important;height:24px !important;
      border-radius:6px !important;transform:none !important;
      background:linear-gradient(180deg,var(--n2),var(--n)) !important}
  .nbe-section-title{font-size:1.4rem !important;font-weight:800 !important;
      letter-spacing:-.02em !important;color:var(--ink) !important}
  .nbe-section-note{font-size:.92rem !important;color:var(--mut) !important;font-weight:500}
  .nbe-note{font-size:.9rem !important;color:var(--mut) !important;line-height:1.55;margin:.35rem 0}

  /* ----- KPI cards ----- */
  .nbe-kpis{display:grid !important;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
      gap:1rem !important;margin:.2rem 0 .9rem !important}
  /* seven cards read best as four over three */
  .nbe-kpis:has(.nbe-kpi:nth-child(7):last-child){display:flex !important;flex-wrap:wrap}
  .nbe-kpis:has(.nbe-kpi:nth-child(7):last-child) .nbe-kpi{flex:1 1 calc(25% - 1rem) !important;min-width:150px !important}
  .nbe-kpi{container-type:inline-size;flex:none !important;min-width:0 !important;
      padding:1.1rem 1.2rem 1.05rem 1.15rem !important;border-radius:22px !important;
      background:#fff !important;border:1px solid var(--ln) !important;box-shadow:var(--sh) !important}
  .nbe-kpi{--k:var(--n);border-left:6px solid var(--k) !important;padding-left:1.15rem !important}
  .nbe-kpi::before{display:none !important}
  .nbe-kpi.accent{--k:var(--gold)}
  .nbe-kpi.good{--k:var(--n2)}
  .nbe-kpi.warn{--k:#D9822B}
  .nbe-kpi:hover{transform:translateY(-4px) !important;box-shadow:var(--sh-up) !important;
      border-color:rgba(0,112,74,.35) !important}
  .nbe-kpi-label{text-transform:none !important;letter-spacing:0 !important;
      font-size:.92rem !important;font-weight:700 !important;color:var(--mut) !important}
  /* six-across rows: keep values level when a label wraps to two lines */
  .nbe-kpis:has(.nbe-kpi:nth-child(6)) .nbe-kpi-label{min-height:2.7em}
  .nbe-kpi-value{font-size:clamp(1.25rem,15cqw,1.95rem) !important;font-weight:800 !important;
      line-height:1.15 !important;margin-top:.45rem !important;white-space:nowrap;
      overflow:hidden;text-overflow:ellipsis;letter-spacing:-.03em !important}
  .nbe-kpi-note{font-size:.84rem !important;color:#7A857F !important;margin-top:.4rem !important}

  /* ----- profile cards (segments, clusters) ----- */
  .nbe-card{--ac:var(--n);padding:1.25rem 1.4rem 1.2rem !important;border-radius:24px !important;
      background:linear-gradient(180deg,#fff 0%,color-mix(in srgb,var(--ac) 4%,#fff) 100%) !important;
      border:1px solid var(--ln) !important;border-left:6px solid var(--ac) !important;
      box-shadow:var(--sh) !important;margin-bottom:1rem}
  .nbe-card:hover{transform:translateY(-4px) !important;box-shadow:var(--sh-up) !important}
  .nbe-card-title{font-size:1.2rem !important;font-weight:800 !important;letter-spacing:-.02em;
      color:var(--ink) !important}
  .nbe-card-sub{font-size:.92rem !important;line-height:1.5 !important;color:var(--mut) !important;
      margin-top:.3rem !important}
  .nbe-card-metrics{display:grid !important;grid-template-columns:repeat(auto-fill,minmax(112px,1fr));
      gap:.9rem 1.1rem !important;margin-top:1rem !important;padding-top:1rem !important;
      border-top:1px dashed rgba(11,42,59,.16) !important}
  .nbe-metric{min-width:0 !important}
  .nbe-metric-k{font-size:.8rem !important;text-transform:none !important;letter-spacing:0 !important;
      font-weight:600 !important;color:#7A857F !important}
  .nbe-metric-v{font-size:1.06rem !important;font-weight:800 !important;margin-top:.1rem;
      letter-spacing:-.01em;color:var(--ink) !important;font-variant-numeric:tabular-nums}

  /* ----- insights ----- */
  .nbe-insight{padding:1.1rem 1.35rem !important;margin:.55rem 0 !important;border-radius:22px !important;
      background:linear-gradient(135deg,#fff 0%,#F1F8F4 100%) !important;
      border:1px solid var(--ln) !important;border-left:6px solid var(--n2) !important;
      box-shadow:var(--sh) !important}
  .nbe-insight.accent{border-left-color:var(--gold) !important;
      background:linear-gradient(135deg,#fff 0%,#FFF6E6 100%) !important}
  .nbe-insight.warn{border-left-color:#D9822B !important;
      background:linear-gradient(135deg,#fff 0%,#FDF0E6 100%) !important}
  .nbe-insight-kicker{display:inline-block;text-transform:none !important;letter-spacing:0 !important;
      font-size:.8rem !important;font-weight:800 !important;color:var(--n) !important;
      background:rgba(0,112,74,.1);padding:.15rem .6rem;border-radius:999px;margin-bottom:.5rem}
  .nbe-insight.accent .nbe-insight-kicker{color:#8A5508 !important;background:rgba(249,166,26,.2)}
  .nbe-insight.warn .nbe-insight-kicker{color:#9A4F10 !important;background:rgba(217,130,43,.18)}
  .nbe-insight-headline{font-size:1.08rem !important;font-weight:700 !important;line-height:1.45 !important;
      color:var(--ink) !important}
  .nbe-insight-body{font-size:.95rem !important;line-height:1.6 !important;color:var(--mut) !important;margin-top:.3rem}

  /* ----- rankings ----- */
  .nbe-rank{display:flex !important;align-items:center;gap:1.1rem !important;padding:.85rem 1.2rem !important;
      margin-bottom:.65rem !important;border-radius:20px !important;background:#fff !important;
      border:1px solid var(--ln) !important;box-shadow:var(--sh) !important}
  .nbe-rank:hover{transform:translateX(6px) !important;border-color:rgba(0,112,74,.4) !important}
  .nbe-rank-no{flex:0 0 auto;display:grid !important;place-items:center;width:44px !important;height:44px !important;
      border-radius:50% !important;font-size:1.1rem !important;font-weight:800 !important;
      color:var(--n) !important;background:rgba(0,112,74,.09) !important;border:0 !important}
  .nbe-rank-no.top{color:#5A3600 !important;
      background:linear-gradient(135deg,#FFE0A3,#F9A61A) !important;box-shadow:0 8px 16px -8px #F9A61A}
  .nbe-rank-no.top::before,.nbe-rank-no.top::after{display:none !important}
  .nbe-rank-name{font-size:1.06rem !important;font-weight:800 !important;letter-spacing:-.01em;color:var(--ink) !important}
  .nbe-rank-meta{font-size:.88rem !important;color:var(--mut) !important;margin-top:.15rem !important}
  .nbe-rank-score{min-width:120px !important}
  .nbe-rank-score .nbe-metric-v{font-size:1.2rem !important;color:var(--n) !important}

  /* ----- data quality ----- */
  .nbe-status{display:grid !important;grid-template-columns:12px minmax(150px,230px) 1fr;column-gap:1rem;
      align-items:start !important;padding:.95rem 1.2rem !important;margin-bottom:.55rem !important;
      border-radius:20px !important;background:#fff !important;border:1px solid var(--ln) !important;
      box-shadow:var(--sh) !important}
  .nbe-status::before{content:"";width:12px;height:12px;border-radius:50%;margin-top:.32rem;
      background:var(--n2);box-shadow:0 0 0 5px rgba(18,160,106,.16)}
  .nbe-status.info::before{background:var(--blue);box-shadow:0 0 0 5px rgba(58,99,184,.15)}
  .nbe-status.warn::before{background:#E08A1E;box-shadow:0 0 0 5px rgba(224,138,30,.2)}
  .nbe-status.warn{background:linear-gradient(135deg,#fff,#FFF6E8) !important}
  .nbe-status-step{min-width:0 !important;font-size:.98rem !important;font-weight:800 !important;color:var(--ink) !important}
  .nbe-status-finding{font-size:.98rem !important;font-weight:700 !important;color:var(--ink) !important}
  .nbe-status-detail{font-size:.88rem !important;line-height:1.55 !important;color:var(--mut) !important;margin-top:.2rem !important}
  @media (max-width:760px){.nbe-status{grid-template-columns:12px 1fr}.nbe-status-body{grid-column:2}}

  .nbe-pipe{gap:.7rem !important}
  .nbe-pipe-step{padding:.9rem .6rem !important;border-radius:20px !important;background:#fff !important}
  .nbe-pipe-step.done{background:linear-gradient(135deg,var(--n2),var(--n)) !important;border-color:transparent !important}
  .nbe-pipe-step.done .nbe-pipe-name,.nbe-pipe-step.done .nbe-pipe-note{color:#fff !important}
  .nbe-pipe-name{font-size:.92rem !important;letter-spacing:0 !important;font-weight:800 !important}
  .nbe-pipe-note{font-size:.8rem !important}

  /* ----- chips and badges ----- */
  .nbe-filter-chip{font-size:.82rem !important;padding:.3rem .8rem !important;border-radius:999px !important}
  .nbe-chip{font-size:.78rem !important}
  .badge{text-transform:none !important;letter-spacing:0 !important;font-size:.74rem !important;
      padding:.12rem .6rem !important;border-radius:999px !important}

  /* ----- tabs ----- */
  [role="tablist"]{background:#fff;border-radius:999px;padding:6px !important;gap:4px !important;
      border:1px solid var(--ln) !important;box-shadow:var(--sh);width:fit-content;max-width:100%;
      overflow-x:auto;margin-bottom:.4rem}
  [role="tab"]{border-radius:999px !important;padding:.55rem 1.3rem !important;height:auto !important;
      font-weight:700 !important;color:var(--mut) !important;white-space:nowrap;
      transition:background .25s,color .25s}
  [role="tab"] *{font-weight:700 !important}
  [role="tab"]:hover{background:rgba(0,112,74,.08) !important;color:var(--n) !important}
  [role="tab"][aria-selected="true"]{background:linear-gradient(135deg,var(--n2),var(--n)) !important;
      color:#fff !important;box-shadow:0 10px 20px -10px var(--n)}
  [role="tab"][aria-selected="true"] *{color:#fff !important}
  [role="tablist"] [data-baseweb="tab-highlight"],[role="tablist"] [data-baseweb="tab-border"],
  [data-baseweb="tab-border"]{display:none !important}
  [role="tab"] > div:empty,[role="tab"] > div[data-rac]:not([data-testid]){display:none !important}
  [role="tabpanel"]{padding-top:.9rem !important}

  /* ----- expanders ----- */
  [data-testid="stExpander"]{border:1px solid var(--ln) !important;border-radius:20px !important;
      background:#fff !important;box-shadow:var(--sh) !important;overflow:hidden;margin:.55rem 0}
  [data-testid="stExpander"] details,[data-testid="stExpander"] summary{border:0 !important;background:transparent !important}
  [data-testid="stExpander"] summary{padding:.8rem 1.2rem !important;font-weight:800 !important}
  [data-testid="stExpander"] summary p{font-size:1.02rem !important;font-weight:800 !important}
  [data-testid="stExpander"] summary:hover{background:rgba(0,112,74,.05) !important}
  [data-testid="stExpanderDetails"]{padding:.4rem 1.3rem 1.2rem !important}
  [data-testid="stExpander"] [data-testid="stExpander"]{box-shadow:none !important;background:#F6FAF8 !important}

  /* ----- alerts ----- */
  div[data-testid="stAlert"]{border:0 !important;background:transparent !important;padding:0 !important;
      border-radius:20px !important;overflow:hidden;box-shadow:var(--sh) !important}
  div[data-testid="stAlert"] [data-testid="stAlertContainer"]{background:transparent !important;border:0 !important;
      padding:0 !important;box-shadow:none !important;border-radius:20px !important}
  div[data-testid="stAlertContentInfo"],div[data-testid="stAlertContentSuccess"],
  div[data-testid="stAlertContentWarning"],div[data-testid="stAlertContentError"]{
      padding:1rem 1.3rem 1rem 1.1rem !important;border-radius:20px !important;
      border:1px solid var(--ln) !important}
  div[data-testid="stAlertContentInfo"]{background:linear-gradient(135deg,#fff,#EAF1FA) !important;
      border-left:6px solid var(--blue) !important}
  div[data-testid="stAlertContentSuccess"]{background:linear-gradient(135deg,#fff,#E8F6EF) !important;
      border-left:6px solid var(--n2) !important}
  div[data-testid="stAlertContentWarning"]{background:linear-gradient(135deg,#fff,#FFF4DE) !important;
      border-left:6px solid var(--gold) !important}
  div[data-testid="stAlertContentError"]{background:linear-gradient(135deg,#fff,#FDECE8) !important;
      border-left:6px solid #D2543B !important}
  div[data-testid="stAlert"] p{font-size:.98rem !important;line-height:1.55}

  /* ----- charts and tables ----- */
  div[data-testid="stPlotlyChart"]{border-radius:24px !important;padding:.7rem .8rem .4rem !important;
      border:1px solid var(--ln) !important;box-shadow:var(--sh) !important}
  div[data-testid="stPlotlyChart"]:hover{box-shadow:var(--sh-up) !important}
  div[data-testid="stDataFrame"]{border:1px solid var(--ln) !important;border-radius:20px !important;
      overflow:hidden;box-shadow:var(--sh) !important;background:#fff}
  [data-testid="stTable"] table{border-radius:16px;overflow:hidden}
  code{background:rgba(0,112,74,.08) !important;color:var(--nd) !important;border-radius:8px;padding:.1rem .4rem}
  pre code{background:transparent !important}
  [data-testid="stCode"],pre{border-radius:18px !important}

  /* ----- inputs ----- */
  [data-baseweb="select"] > div,[data-baseweb="input"] > div,[data-baseweb="base-input"],
  [data-testid="stDateInputField"]{border-radius:14px !important;background:#fff !important;
      border:1px solid var(--ln) !important;min-height:2.7rem}
  [data-baseweb="select"] > div:focus-within,[data-baseweb="input"] > div:focus-within{
      border-color:var(--n2) !important;box-shadow:0 0 0 3px rgba(18,160,106,.18)}
  [data-baseweb="tag"]{background:linear-gradient(135deg,var(--n2),var(--n)) !important;border-radius:999px !important;
      color:#fff !important;font-weight:700}
  [data-baseweb="tag"] *{color:#fff !important}
  [data-testid="stWidgetLabel"] p{font-weight:700 !important;font-size:.95rem !important;color:var(--ink) !important}
  [data-testid="stCheckbox"] label p{font-weight:600}
  [data-testid="stSlider"] [role="slider"]{background:var(--n) !important;box-shadow:0 0 0 6px rgba(18,160,106,.2)}
  [data-testid="stFileUploaderDropzone"]{border-radius:24px !important;padding:1.4rem !important}

  /* ----- buttons ----- */
  .stButton > button,[data-testid="stDownloadButton"] > button,[data-testid="stBaseButton-secondary"]{
      border-radius:16px !important;font-weight:700 !important;border:1px solid var(--ln) !important;
      background:#fff !important;color:var(--ink) !important;box-shadow:var(--sh);
      transition:transform .25s,border-color .25s,box-shadow .25s}
  .stButton > button:hover,[data-testid="stDownloadButton"] > button:hover{
      transform:translateY(-2px);border-color:var(--n) !important;color:var(--n) !important}
  .stButton > button[kind="primary"],[data-testid="stBaseButton-primary"]{color:#fff !important}
  /* journey strip keeps its own pill treatment from v2 */
  div[class*="st-key-nbe-journey-"] .stButton > button{box-shadow:none;border:0 !important;background:transparent !important}
  div[class*="st-key-nbe-journey-active"] .stButton > button{background:linear-gradient(135deg,var(--n2),var(--n)) !important}
  div[class*="st-key-nbe-journey-done"] .stButton > button{color:var(--n) !important}

  /* ----- sidebar ----- */
  section[data-testid="stSidebar"]{background:linear-gradient(180deg,rgba(255,255,255,.92),rgba(246,251,248,.9)) !important}
  .nbe-navhead{font-size:.82rem !important;font-weight:800 !important;letter-spacing:.02em !important;
      text-transform:none !important;color:var(--n) !important;border-top:0 !important;
      margin:1.3rem 0 .5rem !important;padding:0 .3rem !important}
  section[data-testid="stSidebar"] [role="radiogroup"]{gap:.2rem}
  section[data-testid="stSidebar"] [role="radiogroup"] label{padding:.5rem .8rem !important;
      border-radius:14px !important;transition:background .2s,transform .2s}
  section[data-testid="stSidebar"] [role="radiogroup"] label p{font-size:.98rem !important;font-weight:600}
  section[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:rgba(0,112,74,.07) !important;transform:translateX(3px)}
  section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){
      background:rgba(0,112,74,.12) !important}
  section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{font-weight:800;color:var(--n) !important}
  /* workflow list: solid pills, no radio circles */
  section[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] label:has(input:checked){
      background:linear-gradient(135deg,var(--n2),var(--n)) !important;box-shadow:0 12px 22px -12px var(--n)}
  section[data-testid="stSidebar"] .st-key-nav [role="radiogroup"] label:has(input:checked) *{color:#fff !important}
  /* Selected option in any sidebar radio (Analysis method): ONE rule sets both
     the background and the text, with the widget key in the selector, so the
     result no longer depends on which earlier rule happens to win. */
  section[data-testid="stSidebar"] .st-key-methodology_label [role="radiogroup"] label:has(input:checked),
  section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){
      background:linear-gradient(135deg,var(--n2),var(--n)) !important;
      box-shadow:0 10px 18px -12px var(--n)}
  section[data-testid="stSidebar"] .st-key-methodology_label [role="radiogroup"] label:has(input:checked) *,
  section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p,
  section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) *{
      color:#fff !important;font-weight:800}
  /* the radio dot of the selected option: white ring and fill on the green pill */
  section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) div:has(+ [data-testid="stMarkdownContainer"]),
  section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) div:has(+ [data-testid="stMarkdownContainer"]) *{
      border-color:#fff !important;background-color:#fff !important}
  section[data-testid="stSidebar"] .st-key-nav label div:has(+ [data-testid="stMarkdownContainer"]){display:none !important}
  section[data-testid="stSidebar"] [data-testid="stExpander"]{box-shadow:none !important;border-radius:16px !important}
  section[data-testid="stSidebar"] [data-testid="stExpander"] summary{padding:.6rem .9rem !important}
  section[data-testid="stSidebar"] [data-testid="stExpander"] summary p{font-size:.96rem !important}
  .nbe-foot{font-size:.78rem !important;line-height:1.55 !important;color:#7A857F !important}

  /* ----- banner scenes (see ui/scenes.py) -----
     Elements are drawn finished; each keyframe set only adds the "before"
     frame. One loop is 8s. Reduced motion removes the animation and leaves
     the finished picture. */
  .nbe-banner-art *{transform-box:fill-box;transform-origin:center}
  .nbe-banner-art [class^="a-"]{animation-duration:8s;animation-iteration-count:infinite;
      animation-timing-function:ease-in-out;animation-delay:var(--d,0s)}
  .a-barx{transform-origin:0 50% !important;animation-name:aBarX}
  .a-bar{transform-origin:50% 100% !important;animation-name:aBar}
  .a-draw{stroke-dasharray:1;animation-name:aDraw}
  .a-pop{animation-name:aPop}
  .a-fly{animation-name:aFly;animation-timing-function:cubic-bezier(.3,.1,.3,1) !important}
  .a-fix{animation-name:aFix}
  .a-gone{animation-name:aGone}
  .a-gather{animation-name:aGather}
  .a-scan{animation-name:aScan;animation-timing-function:linear !important;opacity:0}
  .a-node{animation-name:aNode}
  .a-travel{animation-name:aTravel;animation-timing-function:linear !important}
  @keyframes aBarX{0%,4%{transform:scaleX(0)}24%,74%{transform:scaleX(1)}84%,100%{transform:scaleX(0)}}
  @keyframes aBar{0%,4%{transform:scaleY(0)}24%,86%{transform:scaleY(1)}96%,100%{transform:scaleY(0)}}
  @keyframes aDraw{0%,16%{stroke-dashoffset:1}50%,86%{stroke-dashoffset:0}96%,100%{stroke-dashoffset:1}}
  @keyframes aPop{0%,40%{transform:scale(0);opacity:0}48%{transform:scale(1.25);opacity:1}54%,86%{transform:scale(1);opacity:1}
      94%,100%{transform:scale(0);opacity:0}}
  @keyframes aFly{0%{transform:translate(var(--sx),0);opacity:0}8%{opacity:.95}34%{transform:translate(0,0);opacity:.95}
      40%,100%{transform:translate(16px,0);opacity:0}}
  @keyframes aFix{0%,30%{transform:translate(var(--bx),var(--by));fill:#FF8A6B}38%,90%{transform:translate(0,0);fill:#7FE8B8}
      98%,100%{transform:translate(var(--bx),var(--by));fill:#FF8A6B}}
  @keyframes aGone{0%,32%{opacity:1;transform:scale(1)}40%,94%{opacity:0;transform:scale(0)}100%{opacity:1;transform:scale(1)}}
  @keyframes aGather{0%,6%{transform:translate(var(--sx),var(--sy));fill:#C7DDD2}
      44%,86%{transform:translate(0,0);fill:var(--c)}96%,100%{transform:translate(var(--sx),var(--sy));fill:#C7DDD2}}
  @keyframes aScan{0%,5%{transform:translateX(0);opacity:0}7%{opacity:1}55%{transform:translateX(330px);opacity:1}
      59%,100%{transform:translateX(330px);opacity:0}}
  @keyframes aNode{0%{opacity:.12}4%,86%{opacity:1}96%,100%{opacity:.12}}
  @keyframes aTravel{0%,3%{transform:translateX(0);opacity:0}7%{opacity:1}66%{transform:translateX(272px);opacity:1}
      70%,100%{transform:translateX(272px);opacity:0}}

  /* ----- masthead polish ----- */
  .nbe-tagline{font-size:.86rem !important}
  div[class*="st-key-nbe-journey-"] .stButton > button p{font-size:.92rem !important;font-weight:700}

  @media (max-width:760px){
    .block-container{padding-left:1rem !important;padding-right:1rem !important}
    .nbe-banner{padding:1.3rem 1.3rem;border-radius:24px}
  }
  @media (prefers-reduced-motion:reduce){*{animation:none !important;transition:none !important}}

  /* Always light. Stops browser "force dark" and keeps the colours the app
     was designed with, so text never lands dark-on-dark. */
  html{color-scheme:only light !important}

  /* Phones and narrow windows */
  @media (max-width:900px){
    .block-container{padding:4.6rem .8rem 3rem !important}
    section[data-testid="stSidebar"]{max-width:86vw}
    div[data-testid="stDataFrame"],div[data-testid="stTable"],.stPlotlyChart{
        max-width:100%;overflow-x:auto}
    iframe{max-width:100%}
    h1{font-size:1.5rem !important}
    h2{font-size:1.25rem !important}
    div[class*="st-key-nbe-journey-row"]{max-width:100%;overflow-x:auto}
  }

  /* Selected workflow tab on hover: keep the green pill and white text.
     The generic hover rule made the background light while the text stayed
     white, so the label vanished when the mouse was over it. */
  div[class*="st-key-nbe-journey-active"] div[data-testid="stButton"] > button:hover,
  div[class*="st-key-nbe-journey-active"] .stButton > button:hover{
      background:linear-gradient(135deg,var(--n2),var(--n)) !important;transform:none}
  div[class*="st-key-nbe-journey-active"] div[data-testid="stButton"] > button:hover *,
  div[class*="st-key-nbe-journey-active"] .stButton > button:hover *{color:#fff !important}

  /* Workflow strip on phones: one scrollable row instead of a wrapped blob. */
  @media (max-width:900px){
    div[class*="st-key-nbe-journey-row"]{border-radius:22px !important;padding:6px !important;
        overflow-x:auto;-webkit-overflow-scrolling:touch}
    div[class*="st-key-nbe-journey-row"] div[data-testid="stHorizontalBlock"]{
        flex-wrap:nowrap !important;flex-direction:row !important;gap:.25rem !important;
        overflow-x:auto;scrollbar-width:none}
    div[class*="st-key-nbe-journey-row"] div[data-testid="stColumn"]{
        flex:0 0 auto !important;width:auto !important;min-width:max-content !important}
    div[class*="st-key-nbe-journey-"] div[data-testid="stButton"] > button{
        white-space:nowrap !important;padding:.5rem .95rem !important}
    div[class*="st-key-nbe-journey-"] div[data-testid="stButton"] > button p{
        white-space:nowrap !important;font-size:.86rem !important}
  }
</style>
"""


def css_v3() -> str:
    """Whole-app restyle layer. Inject right after css_v2()."""
    return CSS_V3
