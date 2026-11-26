# IMPLEMENTATION HANDOFF / CONTINUATION PROMPT

**Project:** NBE Cardlytics Project B, merchant insight prototype
**Phase completed:** Phase 5 (Methodology, diagnostics, downloads). ALL PHASES DONE.
**Next phase:** none. The prototype is feature complete.
**Last updated:** end of Phase 5
**Verification status:** 43 of 43 checks passing, all 6 screens tested end to end

This document is self-contained. A new Claude account should be able to read
this file plus the project folder and continue from the exact stopping point,
without the original conversation and without repeating any analysis.

---

## A. PROJECT STATUS

### What this project is

A graduation/scholarship project for National Bank of Egypt's Cardlytics
initiative. A student team completed an analysis of 100,000 anonymised card
transactions in Jupyter notebooks and built a Power BI dashboard. The goal now
is a **Streamlit prototype** that reruns that entire analysis automatically on
any newly uploaded transaction file, so a non-technical user gets the same
cleaning, KPIs, charts, clustering, rankings and insights without touching
code.

**Scope:** Project B (merchant insight) plus the customer segment screen.
**Deployment:** local laptop only, for a live presentation. No cloud hosting.
**Audience:** NBE business stakeholders and an academic panel.

### Current implementation stage

**Feature complete.** All six screens are built and tested, filters work, both
methodology versions are switchable throughout, and every output downloads as
CSV. The pipeline reproduces the team's original notebook outputs exactly.

Remaining work is polish only: a demo script, and the open items in section I.

### What is already working

- All four analysis stages reproduce the team's six reference output files
  **exactly** from the raw Excel (43 of 43 checks, 100% on every column).
- Merchant resolution with `known` / `new` / `unknown` status.
- Category resolution with `mapped` / `inferred` / `Unknown` status, fully
  independent of merchant status.
- Geography confidence scoring and unrecognised-city detection.
- v2 (corrected) clustering and scoring implemented alongside v1.
- All 19 Power BI DAX measures translated to pandas.
- Plotly chart builders for all five dashboard screens.
- Template-driven insight generation.
- File loading and schema validation with column mapping.
- `app.py` with six tabs. Screens 0, 1 and 2 complete, driven end to end in
  automated tests against both the 100k demo file and a synthetic file
  containing new merchants, an unknown city, a typo and unresolvable rows.
- Sidebar filters (date, category, governorate, gateway, merchant status,
  customer segment, outlier mode), tested composing correctly and handling the
  empty-result case.
- `kpis.py`, `charts.py` and `insights.py` all rendered and working.
- Screens 3 (Merchant clustering) and 4 (Strategic rankings) with V1/V2
  toggles, New badges, a "New merchants only" lens, rank-movement comparison
  and a rank-correlation heatmap.
- Screen 5 (Methodology and diagnostics) with derived parameters, the
  ticket-size diagnostic, side-by-side V1/V2 weights, merchant resolution
  summary and limitations.
- CSV downloads for every output, honouring the current filters and the
  selected methodology version.

### What is not finished

- No demo script for the presentation.
- Items in section I remain open.

---

## B. FILES CREATED / MODIFIED

```
nbe/
├── app.py                           Streamlit UI (Load screen complete)
├── verify.py                        verification harness (run this first)
├── requirements.txt
├── data/
│   └── demo.xlsx                    the raw 100k-row export, for demo mode
├── pipeline/
│   ├── __init__.py
│   ├── clean.py                     Stage 1 + merchant resolution
│   ├── segments.py                  Stage 3 RFM segmentation
│   ├── clustering.py                Stage 2 K-Means, v1 and v2
│   ├── scoring.py                   Stage 4 rankings, v1 and v2
│   ├── kpis.py                      DAX measures translated
│   ├── charts.py                    Plotly figures
│   ├── insights.py                  auto-written sentences
│   └── loader.py                    file reading + schema validation
└── reference/
    ├── governorates.csv             13 entries
    ├── cities.csv                   36 entries
    ├── gateways.csv                 5 entries
    ├── countries.csv                6 entries
    ├── merchant_aliases.csv         2 entries
    ├── merchant_categories.csv      77 merchants to 14 categories
    └── category_keywords.csv        keyword rules for inferred categories
```

### pipeline/clean.py

Stage 1. Reads a raw export, parses `Description`, resolves merchant, category
and geography, adds derived columns.

Key functions:
- `Vocabulary` — loads reference CSVs. `_load()` sorts **longest-first**, which
  is required: "SOUTH SINAI" must be tested before "SINAI" or the longer name
  gets truncated.
- `normalize_merchant(name)` — `&`→`AND`, removes `'` and `.`, `/`→space.
- `_strip_known_suffix(text, vocab)` — removes a trailing vocabulary term.
  Handles three separators (space, ` -`, ` /`) **and** the case where the term
  is the entire remaining string.
- `parse_description(desc, vocab)` — the core parser.
- `discover_city_candidates(parsed)` — finds unrecognised cities.
- `resolve_merchants(parsed, vocab)` — assigns `merchant_status`.
- `infer_category(merchant, vocab)` — keyword-based category guessing.
- `resolve_categories(merchant, vocab)` — assigns `category_status`.
- `score_geo_confidence(parsed, status)` — high / medium / low / none.
- `compute_outlier_flag(amounts)` — global Tukey fence, recomputed per file.
- `clean(raw, vocab, learn_geography=False)` — returns `(DataFrame, report)`.

**Critical assumptions:**
- Descriptions follow `[GATEWAY*] MERCHANT CITY GOVERNORATE [REF] EGY` or
  `MERCHANT COUNTRY`.
- Reference codes match `XX-XXX-XXX`, `XX-XXX` or `X-XXXX`.
- Some rows glue `EGY` onto the ref code with no space (`4-849WEGY`).
- Roughly 19,500 of 100,000 rows use `-` or `/` before the governorate rather
  than a space. Handling only spaces drops geography on ~30% of rows.

### pipeline/segments.py

Stage 3. Debit-only RFM aggregation, then percentile tiers.
- `snapshot_date(df)` = max transaction date + 1 day, **computed from data**.
- `build_rfm(df)` — one row per PAN.
- `assign_segments(rfm)` — `pd.qcut` over `monetary.rank(method='first')`.
  Ranking first guarantees exact 30/50/20 counts even with tied spend totals.
- `segment_customers(df)` — returns `(customers, thresholds)`.

### pipeline/clustering.py

Stage 2. Merchant aggregation and K-Means.
- `build_merchant_features(clean_df, customers)` — one row per merchant, spend
  pivoted by customer segment. Carries `merchant_status`, `category`,
  `category_status`, `geo_confidence` forward.
- `k_selection_evidence(features, version)` — inertia and silhouette, K=2..8.
- `name_clusters(profiles)` — assigns names **from cluster profiles, never
  from K-Means IDs**. See section D.
- `cluster_merchants(clean_df, customers, version, k)` — returns
  `(clusters, diagnostics)`.

### pipeline/scoring.py

Stage 4. Four deliverables, two versions each.
- `min_max_score` / `percentile_score` — normalisation.
- `month_span(df)` — distinct month count, replaces a hardcoded `/12`.
- `average_mom_growth` (v1) / `half_over_half_growth` (v2).
- `build_scoring_base(clean_df, clusters, version)`.
- `score_v1(...)` / `score_v2(...)` — return dicts with keys
  `partnership`, `loyalty`, `bnpl`, `potential`.
- `rank_movement(v1, v2)` — how far each merchant moved.
- `rank_correlation(rankings)` — Spearman between the four deliverables.

### pipeline/kpis.py

All 19 DAX measures, each docstring naming the DAX it reproduces.
`executive_kpis(df)` and `segment_kpis(customers)` return ready-made dicts.

### pipeline/charts.py

Plotly builders. Colours: `INK #10312B`, `GOLD #C9A227`, `BLUE #4472A8`,
`GRAY #A8A8A8`. Segment colours match the team's existing PNGs
(gray Low-Value, blue Mass, gold VIP).

### pipeline/insights.py

`transaction_insights`, `segment_insights`, `cluster_insights`,
`ranking_insights`, `data_quality_notes`. Every sentence is a template filled
from loaded data. Rules return nothing when their condition does not hold.

### pipeline/loader.py

`read_any(source)`, `validate(df)` returning status `ok` / `mappable` /
`blocked`, and `apply_mapping(df, mapping)`.

### app.py

The user interface. Performs no analysis: every number comes from `pipeline/`.

- `run_clean`, `run_segments`, `run_clusters`, `run_scoring`, `read_demo` are
  `@st.cache_data` wrappers so a rerun does not re-parse 100,000 rows.
- `screen_load()` is Screen 0, complete.
- `sidebar_filters(clean_df)` returns `(filtered, filtered_customers, active)`.
- `filter_banner(filtered, total, active)` prints what is excluded and returns
  False when nothing is left, which is the guard every screen checks.
- `screen_executive(filtered)` is Screen 1.
- `screen_segments(filtered, filtered_customers)` is Screen 2.
- `screen_clustering(filtered, customers)` is Screen 3.
- `screen_rankings(filtered, customers)` is Screen 4.
- `screen_methodology(filtered, customers)` is Screen 5.
- `screen_downloads(filtered, customers)` renders the CSV export buttons.
- `safe_cluster(filtered, customers, version, k)` guards the one way K-Means
  crashes here: fewer merchants in view than clusters requested. Returns the
  unclustered feature table with `insufficient=True` rather than raising.
  **Every screen that clusters must check `diag["insufficient"]`.**
- `new_merchants_only(filtered, key)` is an optional lens, not a judgement.
  New merchants are included everywhere by default.
- `ticket_diagnostic(merchant_df)` computes ticket spread from the loaded file,
  never from a hard-coded constant.
- `merchant_status_badge(status)` renders the status chip. `new` gets a gold
  badge, never a warning colour.
- `metric_strip(cells)` renders the KPI strip.
- `egp(value)` formats currency.
- `DEMO_FILE` honours the `NBE_DEMO_FILE` environment variable, which is how
  the automated tests point the app at a small sample.

Results are stored in `st.session_state` under: `clean_df`, `report`,
`customers`, `thresholds`, `clusters_v1`, `diag_v1`, `rankings_v1`. Screens 1
to 5 should read from there rather than recomputing.

Palette: `INK #10312B`, `GOLD #C9A227`, `BLUE #4472A8`, `GRAY #A8A8A8`,
`RULE #DCDDD6`. Segment colours match the team's existing PNGs.

---

## C. DATA PIPELINE STATUS

```
Upload                  loader.read_any             BUILT, untested end to end
Validation              loader.validate             BUILT, untested end to end
Cleaning                clean.clean                 BUILT + VERIFIED
Parsing                 clean.parse_description     BUILT + VERIFIED
Merchant Resolution     clean.resolve_merchants     BUILT + TESTED
Customer Segmentation   segments.segment_customers  BUILT + VERIFIED
Merchant Aggregation    clustering.build_merchant_features  BUILT + VERIFIED
Clustering              clustering.cluster_merchants        BUILT + VERIFIED (v1)
Scoring                 scoring.score_v1 / score_v2         BUILT + VERIFIED (v1)
Dashboard               app.py                      ALL 6 SCREENS BUILT + TESTED
Download                app.screen_downloads        BUILT + TESTED
```

"VERIFIED" means it reproduces the team's original notebook output exactly.
"TESTED" means it passes synthetic edge-case tests (no reference output exists).

---

## D. MERCHANT LOGIC — DO NOT WEAKEN THIS

### The locked rule

**"Not found in the reference list" is NOT "unknown".**

A merchant that parses cleanly but is absent from the reference list is
`new`. It is a real merchant. It flows through every downstream stage with no
penalty, no exclusion and no special scoring formula.

### Why the parser already supports this

The parser identifies merchants **by subtraction, not by lookup**. It strips
the gateway prefix, the `EGY` suffix, the reference code, the governorate and
the city; whatever survives is the merchant. It never consults a merchant list
to decide what a merchant is. The 77-name list is used only to decide
`merchant_status` and to look up a category.

Worked example, `KASHIER* ABC FOOD MARKET CAIRO EGY`:

| Step | Result |
|---|---|
| strip gateway | `ABC FOOD MARKET CAIRO EGY` |
| strip EGY | `ABC FOOD MARKET CAIRO` |
| strip governorate `CAIRO` | `ABC FOOD MARKET` |
| strip city (no match) | `ABC FOOD MARKET` |
| merchant | `ABC FOOD MARKET`, status `new` |

### The three statuses

| Status | Condition |
|---|---|
| `known` | exact match, alias match, or close match ≥ 0.92 similarity |
| `new` | parsed cleanly, absent from the reference list |
| `unknown` | the parser genuinely could not isolate a merchant name |

`unknown` is deliberately narrow. It fires only when:
- `Description` is null or blank
- nothing survives after stripping geography
- the leftover is under 2 characters, purely numeric, or matches the
  reference-code pattern
- the leftover is purely a place name (governorate, city or country) that is
  not itself a reference merchant

Everything else that parses becomes `new`.

### Category is independent

`category_status` is resolved separately and never affects `merchant_status`.

| category_status | Meaning |
|---|---|
| `mapped` | from `reference/merchant_categories.csv` |
| `inferred` | from `reference/category_keywords.csv` keyword rules |
| `Unknown` | no rule fired |

An `inferred` category must **always** be labelled as inferred in the UI and
never presented as reference-mapped. A `new` merchant with an `Unknown`
category is still `new`.

### Geography is also a baseline, not a whitelist

An unrecognised city is the one way subtraction goes quietly wrong: if the
city is not stripped it stays glued to the merchant name and a phantom
merchant appears that looks perfectly valid.

`geo_confidence` per row:

| Value | Meaning |
|---|---|
| `high` | international, or governorate and city both resolved |
| `medium` | governorate resolved, nothing city-shaped left over |
| `low` | governorate resolved but trailing words look like a city, so the merchant name may have absorbed it |
| `none` | no geography markers recognised |

`discover_city_candidates()` flags a trailing token as a probable
unrecognised city when it appears after at least 3 distinct merchant prefixes
in at least 10 rows. Candidates are **reported, not auto-applied**, because
applying one rewrites merchant names. Pass `learn_geography=True` to
`clean()` to accept them and re-parse.

Verified behaviour with an unknown city `REHAB CITY`:
- `learn_geography=False` → merchants read `ABC FOOD MARKET REHAB CITY`, all
  rows flagged `geo_confidence=low`, candidate `REHAB CITY` reported.
- `learn_geography=True` → merchants read `ABC FOOD MARKET`, city `REHAB
  CITY`, confidence `high`.

### Ways a future developer could break this — do not do these

1. Filtering merchants against the reference list anywhere in the pipeline.
2. Mapping unmatched merchants to `"Unknown"`, `"Other"` or `"Uncategorized"`.
3. Combining the new and unknown counts in any UI or report.
4. Treating `category_status = Unknown` as a reason to change
   `merchant_status`.
5. Excluding `new` merchants from K-Means or from any ranking.
6. Lowering `CLOSE_MATCH_CUTOFF` below 0.92, which would silently merge
   genuinely different merchants into reference names.

---

## E. V1 METHODOLOGY (the team's original, locked)

This section describes only what the original notebooks did. Do not describe
v2 improvements here.

### Stage 1, cleaning
- Parse `Description` into gateway, merchant, city, governorate, ref_code,
  country.
- Merchant normalisation: `&`→`AND`, drop `'` and `.`, `/`→space.
- Aliases: `ORANGE EGYPT`→`ORANGE`, `VODAFONE EGYPT`→`VODAFONE`.
- Category from the 77-merchant lookup.
- `is_international` = country present. `is_egyptian` = its inverse.
- `txn_month` `YYYY-MM`, `txn_quarter` `YYYYQn`, `day_of_week` day name.
- `is_outlier` = `Amount > Q3 + 1.5 × IQR` computed **globally over all
  transactions**. On the reference data this is 9,008.74 EGP, flagging 18,309
  of 100,000 rows.

### Stage 3, customer segmentation
- **Debit only** (`DB/CR == 'DEBIT TRANSACTION'`), 96,990 of 100,000 rows.
- Snapshot date = max transaction date + 1 day = 2026-07-01 on reference data.
- `recency` = days from last purchase to snapshot.
- `frequency` = debit transaction count.
- `monetary` = debit spend total.
- `avg_ticket` = monetary / frequency.
- `outlier_ratio` = debit-only mean of `is_outlier`, **rounded to 4 decimals**.
- Segments by `pd.qcut` on `monetary.rank(method='first')` at
  `[0, 0.30, 0.80, 1.0]` → Low-Value 30%, Mass 50%, VIP 20%.
- Reference result: 1,428 / 2,378 / 952 cardholders; VIP holds 71.4% of the
  1.085B EGP debit volume.

### Stage 2, merchant clustering
- Debit only, joined to customer segments.
- **Ten features:** `total_amount_egp`, `transaction_count`, `avg_ticket_egp`,
  `unique_customers`, `mass_customer_count`, `mass_spend_amount`,
  `mass_frequency`, `mass_concentration`, `avg_ticket_mass`,
  `vip_concentration`.
- Log1p on `total_amount_egp`, `transaction_count`, `unique_customers`,
  `mass_spend_amount`, `mass_frequency`. Then `StandardScaler`.
- `KMeans(n_clusters=4, random_state=42, n_init=50)`.
- Reference result: silhouette 0.3254, PC1 61% of variance, clusters of
  27 / 23 / 18 / 9 merchants.

### Cluster naming (locked, and the reason the pipeline survives new data)
K-Means numbers clusters arbitrarily and the numbering changes on different
data. Names are therefore assigned from **cluster profiles**, claimed in this
fixed priority order:

1. `VIP-Driven High-Value` → highest mean `vip_concentration`
2. `Mass-Driven High-Reach` → highest mean `mass_concentration`
3. `Frequent Low-Ticket` → highest mean `transaction_count`
4. `High-Ticket Opportunity` → highest mean `avg_ticket_egp`

Each name goes to the best-fitting cluster not already claimed. Bank IDs:
VIP-Driven 1, Mass-Driven 2, Frequent Low-Ticket 3, High-Ticket 4.

### Stage 4, scoring (v1)

| Deliverable | v1 formula |
|---|---|
| Partnership | plain sort by `total_amount_egp`, then `avg_monthly_spend` |
| Loyalty | plain sort by `transaction_count`, then `avg_monthly_transactions` |
| BNPL | `0.50 × norm(total spend) + 0.50 × norm(transaction count)` |
| Potential | `0.25 × spend + 0.25 × reach + 0.25 × growth + 0.25 × strategic`, clipped 0-100 |

- Normalisation: min-max to 0-100.
- `growth_raw` = mean of month-over-month percentage changes, 0 when the
  previous month is 0.
- `strategic_raw` = `unique_governorates × 2 + unique_cities`.
- `avg_monthly_spend` = total / month span.

### DAX measures (from the team's Power BI file, locked)

| Measure | Definition |
|---|---|
| Total Spend | `SUM(Amount)` over **all** rows, credits included |
| Total Transactions | `COUNTROWS(table)` |
| Unique Customers | `DISTINCTCOUNT(PAN)` |
| Active Merchants | `DISTINCTCOUNT(merchant)` |
| Average Ticket Size | `Total Spend / Total Transactions` |
| Avg Settlement Lag | `AVERAGEX(DATEDIFF(Txn date, Posting Date, DAY))` |
| Outlier Spend Ratio | outlier spend / total spend |
| Segment Cardholders | `COUNTROWS(customer_segments)` |
| Avg Recency / Frequency / Ticket | `AVERAGE` over the customer table |
| Cluster Spend | `SUM(merchant_clusters[total_amount_egp])` |
| Active Merchants in Cluster | `DISTINCTCOUNT(merchant_clusters[merchant])` |
| Avg VIP / Mass Conc % | `AVERAGE`, **unweighted across merchants** |
| Top Partnership / Loyalty / BNPL Target | merchant whose stored rank = 1 |

---

## F. V2 METHODOLOGY (corrections, shown side by side with v1)

### Why v2 exists — three findings from the reference data

**1. Average ticket barely varies between merchants.** Across all 77
merchants: mean 11,161 EGP, standard deviation 875, spread under 8%. By
category, Digital & Streaming 10,707 and Fashion & Apparel 11,733. A jewellery
purchase and a coffee cost the same. The synthetic data generator drew
`Amount` from one global distribution without conditioning on merchant.

**2. All four v1 deliverables are the same ranking.** Spearman correlations
between them run 0.932 to 0.997; partnership and BNPL correlate at 0.997.
Since volume is the only thing that varies between merchants, every metric
becomes a proxy for volume.

**3. The v1 BNPL ranking is inverted.** Top 6: Metro Market, Seoudi, Kazyon,
Spinneys, Carrefour, HyperOne, all supermarkets. Bottom 5: Azza Fahmy
Jewellery, Elite Optics, Prestige Watches, Damas Jewellery, Magrabi Optics.
The formula has no ticket-size term, and the brief says BNPL should target
high-ticket segments.

### What v2 changes

**Clustering features.** v1's ten features include six size proxies
(`total_amount_egp`, `transaction_count`, `unique_customers`,
`mass_customer_count`, `mass_spend_amount`, `mass_frequency`) which are
strongly correlated, so after standardisation size outvotes behaviour six to
four. v2 uses seven size-neutral features: `avg_ticket_egp`,
`avg_ticket_mass`, `mass_concentration`, `vip_concentration`,
`txns_per_customer`, `high_ticket_share`, `total_amount_egp`.

**Scoring weights (v2):**

| Deliverable | v2 formula |
|---|---|
| Partnership | `0.40 spend + 0.30 reach + 0.30 strategic` |
| Loyalty | `0.40 frequency + 0.30 repeat + 0.30 reach` |
| BNPL | `0.40 avg_ticket + 0.30 high_ticket_share + 0.30 frequency` |
| Potential | `0.25 spend + 0.25 reach + 0.25 growth + 0.25 strategic` |

**Normalisation.** Percentile rank instead of min-max, so one extreme merchant
cannot compress everyone else. In v1 the top merchants score `growth_norm`
between 2 and 10 out of 100 because one merchant grew 111%.

**Growth.** Second half of the period versus first half, instead of the mean
of month-over-month percentages. The v1 method is asymmetric: +100% then -50%
returns to the starting value but averages to +25%.

**Consistency.** All four deliverables become weighted composites. In v1 two
are plain sorts and two are composites.

### V2 measured results (reference data)

| Metric | v1 | v2 |
|---|---|---|
| Clustering silhouette | 0.325 | 0.223 |
| PC1 share of variance | 61% | 43% |
| Rank correlation between deliverables | 0.932 to 0.997 | 0.454 to 0.988 |
| BNPL top 6 | 6 supermarkets | Metro Market, Careem, Pizza Hut, Lavazza, H&M, Costa Coffee |

### Honest limitation, must be stated in the demo

v2 is methodologically correct but this dataset has almost no merchant-level
ticket variation, so part of the reordering reflects noise rather than signal.
Jewellery still does not top the v2 BNPL list, because in this data jewellery
has *low* average tickets (Damas 9,879 EGP). **The app must not imply v2 fixes
something the data cannot support.** The Diagnostics screen exists to show
this evidence explicitly.

### V2 status

Implemented: clustering features, all four scoring formulas, percentile
normalisation, half-over-half growth, `rank_movement`, `rank_correlation`.
Pending: UI toggles, before/after display, diagnostics screen.

---

## G. UI STATUS

| Screen | Status |
|---|---|
| 0. Load (upload, validate, cleaning report, new merchants) | **IMPLEMENTED + TESTED** |
| 1. Executive Overview | **IMPLEMENTED + TESTED** |
| 2. Customer Segments | **IMPLEMENTED + TESTED** |
| 3. Merchant Clustering | **IMPLEMENTED + TESTED** |
| 4. Strategic Rankings | **IMPLEMENTED + TESTED** |
| 5. Methodology & Diagnostics | **IMPLEMENTED + TESTED** |
| Downloads | **IMPLEMENTED + TESTED** |
| Sidebar filters | **IMPLEMENTED + TESTED** |

All chart builders in `charts.py` are rendered by at least one screen.

Screen 0 contains: demo button and file uploader; validation with three
verdicts (`ok` shows a success line, `mappable` shows per-column dropdowns and
an apply button, `blocked` shows the missing columns and stops); a five-cell
metric strip; separate Known / New / Unresolvable merchant counts; the New
Merchants Detected table; an expander of unresolvable descriptions; three
category-resolution counts with an inferred-category warning; a four-cell
geography confidence strip; the unrecognised-city candidate table with a
`learn_geography` toggle; an auto-correction audit expander; and a summary of
the downstream stages.

Screen 3 contains: V1/V2 radio, "New merchants only" checkbox, K-selection
evidence (elbow and silhouette), PCA scatter, cluster feature profiles, the
audience concentration quadrant, and a cluster summary carrying
`merchant_status`.

Screen 4 contains: V1/V2 radio, "New merchants only" checkbox, the ticket-size
caveat, a deliverable selector, stored-rank and recomputed top-target cards, a
top-25 table with status badges, a note when new merchants place in the top 25,
a Spearman correlation heatmap across the four deliverables, and a V1-vs-V2
rank movement chart.

Screen 5 contains: derived parameters table, ticket-size diagnostic with the
per-merchant chart, side-by-side V1/V2 weight tables, an explanation of each V2
change, the merchant resolution summary, limitations, dataset notes, and seven
CSV download buttons.

Phase 5 test results (automated, `streamlit.testing.v1.AppTest`, zero
exceptions on every path):

| Path | Result |
|---|---|
| 100k demo, full load | 16s, 16 charts, 7 downloads |
| Synthetic mixed file | 16 charts, 13 tables |
| Clustering V2 | OK |
| Rankings V2 | OK |
| All 4 deliverables | OK |
| New merchants only, both screens | OK |
| Downloads under V2 | 7 files, correctly suffixed `_v2` |
| Filters narrowed to empty | Warning shown, no crash |

Phase 2 test results (automated, via `streamlit.testing.v1.AppTest`):

| File | Known | New | Unresolvable | Mapped rows | Inferred rows | Unknown rows |
|---|---|---|---|---|---|---|
| 100k demo | 77 | 0 | 0 | 100,000 | 0 | 0 |
| synthetic mixed | 77 | 6 | 1 | 4,003 | 120 | 5 |

The synthetic file correctly surfaced `REHAB CITY` as an unrecognised city,
auto-corrected `MCDONALD S` to `MCDONALDS`, and rendered all three tables.

---

## H. FILTERS

**Implemented in `app.py:sidebar_filters()`.** Date range, category,
governorate, gateway, merchant status, customer segment, and a three-way
outlier radio (Include / Exclude only outliers / Outliers only).

**LOCKED DECISION: the customer table is FILTERED, not recomputed.** Segments
stay as assigned on the full dataset, matching the Power BI model where
`customer_segments` is a precomputed table that slicers filter. Recomputing
would reassign cardholders to different tiers on every filter change, which
answers a different question from the one the dashboard asks.

Design decisions already made:
- Filters apply to screens 1 to 4.
- KPIs recompute under filters.
- Rankings under v1 use stored ranks, matching the Power BI behaviour where
  `Top Partnership Target` goes blank if the rank-1 merchant is filtered out.
- Rankings under v2 recompute the top target from merchants still in view.
  `kpis.top_target(ranking, column, recompute=True)` already supports this.
  Not yet wired, since Screen 4 does not exist.

Verified filter composition on the 100k demo:
100,000 rows, then Jewelry & Luxury 1,955, then Outliers only 335, then
+VIP 211. The empty case shows a warning and renders no charts.

---

## I. KNOWN ISSUES

1. **`geo_confidence = low` over-fires.** Any domestic row with two or more
   leftover words and no city match is flagged low, even when the description
   genuinely contains no city. On a two-word merchant like `ABC FOOD MARKET
   CAIRO EGY` this reads low when it is actually fine. Errs toward caution,
   which is the safe direction, but it is noisy.

2. **`kpis.py`, `charts.py`, `insights.py`, `loader.py` are untested.** Written
   but never executed end to end. Expect small bugs on first run.

3. **`insights.ranking_insights` uses `scoring.rank_correlation`** which
   requires all four ranking frames. It will raise if given a partial dict.

4. **v2 cluster names are inherited from v1's naming rules.** With v2's
   size-neutral features the names may fit less well than they do under v1.
   Worth reviewing once the Clustering screen exists.

5. **`BANK_ID_BY_NAME` only covers 4 clusters.** With K ≠ 4 extra clusters get
   a profile-derived fallback label and a null `cluster_id`. Untested.

6. **No performance testing above 100,000 rows.** Pandas in memory. The
   description parser is a Python loop over every row, roughly 15 seconds for
   100k. A 1M-row file would be slow and needs `@st.cache_data`.

7. **Single currency.** Everything assumes EGP. No FX conversion exists.

8. **Screen 0 recomputes the whole pipeline when `learn_geography` is
   toggled.** Correct behaviour, since accepting cities changes merchant
   names, but it costs about 11 seconds on the 100k file.

9. **Column mapping is not covered by an automated test.** The `mappable`
   branch is written but only the `ok` branch has been driven end to end.
   Still outstanding. This is the largest untested path in the app.

11. **The date filter is not in the active-filter banner.** Narrowing dates
    changes the row count but the caption does not name it as a filter.

12. **Screen 2's category-by-segment chart re-joins transactions to
    customers on every render.** Fine at 100k rows, would need caching above
    roughly 1M.

13. **Screen 4's V1-vs-V2 expander clusters and scores twice.** Opening it
    roughly doubles that screen's work. Acceptable at 100k, noticeable above.

14. **V2 cluster names are inherited from V1's naming rules.** With V2's
    size-neutral features the profile-based names may fit differently. Worth a
    review, but the naming logic itself is locked.

15. **Downloads build every CSV eagerly** before any button is pressed, so the
    Methodology tab does the export work on every render.

16. **No demo script.** Worth writing before the presentation: which filters to
    set, which toggles to flip, and in what order.

10. **Screens 1 to 5 read from `st.session_state`,** so they will be empty if
    a user opens them before loading a dataset. Each placeholder already
    guards against this; keep that guard when building them.

---

## J. NEXT STEPS

1. ~~Phase 2, Load screen.~~ **DONE.**
2. ~~Phase 3, Executive Overview and Customer Segments plus filters.~~ **DONE.**
3. ~~Phase 4, Merchant Clustering and Strategic Rankings.~~ **DONE.**
4. ~~Phase 5, Methodology, diagnostics and downloads.~~ **DONE.**

**All planned phases are complete.** If work continues, take it from section I
in this order: write the demo script (16), add an automated test for column
mapping (9), then the performance items (13, 15).

Superseded plan text follows for reference only:

~~4. **Phase 4.** Merchant Clustering and Strategic Rankings screens with v1/v2
   toggles, `New` badges, and new-merchants-only filters.
4. **Phase 5.** Methodology & Diagnostics screen, downloads including
   `merchant_status`, README, demo script.~~

Run `python verify.py` after every phase. It must stay at 43 of 43.

---

## K. ALREADY COMPLETED — DO NOT REDO

Do not rewrite, re-derive or re-validate any of these. They are verified
against the team's original outputs at 100%.

- The `Description` parser. It took substantial reverse-engineering: three
  separator variants, `EGY` glued to ref codes, longest-first vocabulary
  matching, and a two-entry alias table. **Do not rewrite it.**
- The `is_outlier` rule (global Tukey fence).
- The snapshot date rule (max date + 1 day).
- The `outlier_ratio` definition (debit only, rounded to 4 dp).
- The segmentation percentiles and the rank-qcut method.
- The v1 clustering feature list, log transforms and K-Means parameters.
- The profile-based cluster naming.
- All four v1 scoring formulas.
- All 19 DAX translations.
- The merchant/category/geography resolution logic in section D.
- Screen 0 in `app.py`, including the validation branches, the New Merchants
  table and the geography candidate display.
- Screens 1 and 2, and `sidebar_filters()`. All tested.
- Screens 3, 4 and 5, `screen_downloads()`, `safe_cluster()`,
  `new_merchants_only()`, `ticket_diagnostic()`, `merchant_status_badge()`.
  All tested. `safe_cluster` in particular guards a real crash; do not remove
  the `insufficient` check from any screen.
- `insights.data_quality_notes()`, rewritten in Phase 3 for the current report
  shape. It previously referenced a removed key (`unmatched_merchants`).

Do not re-analyse the reference CSVs to rediscover the methodology. It is all
documented in sections D, E and F.

---

## L. FILES REQUIRED FROM THE USER

To continue, the next Claude account needs the user to upload:

**Essential**
1. The project folder as a zip (`app.py`, `pipeline/`, `reference/`,
   `verify.py`, `requirements.txt`). `data/demo.xlsx` is a copy of the raw
   Excel and can be regenerated from item 2.
2. `dummy_data_final_-_merchants_project_-_clean.xlsx` — the raw input.
3. The six reference outputs, needed for `verify.py`:
   - `nbe_merchants_clean.csv`
   - `customer_segments.csv`
   - `merchant_clusters.csv`
   - `partnership_ranking.csv`
   - `loyalty_ranking.csv`
   - `bnpl_ranking.csv`
   - `potential_merchant_score.csv`

**Not needed again** (already fully documented here): the original notebooks
(`YOUSEFF.ipynb`, `STAGE_4.ipynb`, `zeyad_customer_segmentation.ipynb`), the
`.pbix` file, and the NBE brief deck.

---

## VERIFICATION COMMAND

```bash
cd nbe
python verify.py [path/to/raw.xlsx] [path/to/reference/dir]
```

Defaults point at `/mnt/user-data/uploads/`. Expected final output:

```
RESULT
------
  All 43 checks passed. v1 methodology reproduces exactly.
```

## M. PHASE 4 STATUS (added at end of Phase 4, read this first)

Screens 3 (Merchant Clustering) and 4 (Strategic Rankings) are built in
`app.py`. **Only `app.py` was touched.** No file under `pipeline/` was
modified, so `verify.py` should still report 43 of 43 — this was confirmed by
re-running `clean()`, `cluster_merchants()` (v1 and v2) and `score_v1()` /
`score_v2()` directly against `data/demo.xlsx` and checking the numbers
against section E/F of this document (silhouette 0.3254, cluster sizes
27/23/18/9, v1 BNPL top 6 all supermarkets, v2 BNPL top 6 Metro Market /
Careem / Pizza Hut / Lavazza / H&M / Costa Coffee — all matched). The actual
`verify.py` script was **not run** in that session because the six reference
CSVs and the raw dummy Excel were not part of the Phase 4 upload; only
`data/demo.xlsx` (the raw file) was present. Run `python verify.py` locally
with the reference files to get the official 43/43 confirmation before
treating Phase 4 as fully signed off.

New in `app.py`:
- `merchant_status_badge()` — small HTML badge (Known/New/Unknown), using the
  `.badge-known` / `.badge-new` / `.badge-unknown` CSS classes added to the
  existing style block. `.badge-new` already existed but was unused before
  Phase 4.
- `safe_cluster()` — wraps `cluster_merchants()`. K-Means needs at least K
  samples; a narrow filter (merchant status = New, a small category, ...) can
  leave fewer merchants than K=4. This wrapper falls back to the unclustered
  `build_merchant_features()` table instead of crashing, so Strategic
  Rankings can still score whatever merchants remain. This was found by
  testing, not anticipated in the Phase 4 brief — see Known Issues below.
- `ticket_diagnostic()` — mean / SD / spread of `avg_ticket_egp` across
  merchants **in the current filtered view**, computed fresh each run. The
  ~8% figure in section F is specific to the reference dataset and is not
  hard-coded anywhere in the app.
- `screen_clustering()` — V1/V2 radio, KPI strip (`kpis.active_merchants_in_cluster`,
  `cluster_spend`, `avg_vip_concentration`, `avg_mass_concentration`, silhouette),
  `charts.pca_scatter`, `concentration_quadrant`, `cluster_profiles`, a
  per-cluster summary line with a "N new" badge, a full merchant table with a
  Status column, an expander listing new merchants in view with badges, and
  `insights.cluster_insights`.
- `screen_rankings()` — V1/V2 radio, ticket-size diagnostic banner, a
  deliverable selector (Partnership / Loyalty / BNPL / Potential), the stored
  vs. recomputed "top target" KPIs (`kpis.top_target(..., recompute=False/True)`),
  a ranked table with Status, a callout listing any new merchants in the top
  25, `insights.ranking_insights`, and an expander that scores the other
  version on demand and shows `charts.rank_movement_chart` — the "before/after
  display" section F listed as pending.
- Both screens call `run_clusters` / `run_scoring` (the existing
  `@st.cache_data` wrappers) against the **filtered** transaction table, so
  merchant clustering and rankings recompute under the sidebar filters the
  same way the Executive Overview KPIs already did. This is a difference from
  customer segmentation, which stays precomputed and filtered per the locked
  rule in section H — segmentation was not touched.
- The Phase 3 merchant-status sidebar filter (`sidebar_filters()`, already
  built) was not modified; it is what now drives the New-only / Known-only /
  Unknown-only views on screens 3 and 4, composed with every other filter.

### Validation performed this session

- `python -m py_compile app.py` — passes.
- No `pipeline/` file was edited (`diff` against the Phase 3 zip confirms
  `app.py` is the only changed file).
- Ran `clean()` → `segment_customers()` → `cluster_merchants()` (v1 and v2) →
  `score_v1()` / `score_v2()` directly on `data/demo.xlsx` (100k rows, 77
  known merchants): matched the reference numbers in sections E/F exactly
  (silhouette 0.3254 v1 / 0.2227 v2, cluster sizes 27/23/18/9, v1 rank
  correlations 0.93–1.00, v2 0.45–0.99, v1 and v2 BNPL top-6 lists both
  matched section F).
- Built a synthetic mixed file (100k reference rows + 60 rows of a fabricated
  merchant, `KASHIER* BRANDNEWCO CAIRO CAIRO 1-234-567 EGY`) and confirmed the
  new merchant: resolves to `merchant_status = new`; is clustered
  (`VIP-Driven High-Value` in this run) with no exclusion or penalty; scores
  and ranks normally (partnership rank 78 of 78); and is not treated as
  invalid anywhere.
- Because `streamlit` and `plotly` are not installed in this sandbox and it
  has no network access to install them, `streamlit run app.py` could not be
  executed directly. Instead, `screen_clustering()` and `screen_rankings()`
  were exercised end-to-end against real pipeline output under a minimal
  stub of the `streamlit` and `plotly` modules (stand-ins for every
  `st.*`/`px.*`/`go.*` call actually used), across: no filters (100,060
  rows / 78 merchants), merchant status = New only (60 rows / 1 merchant),
  merchant status = Known only (100,000 rows / 77 merchants), and a narrow
  category filter (25,887 rows / 11 merchants) — each run through both V1 and
  V2 and all four ranking deliverables, with zero exceptions. Also drove both
  screens directly with a zero-row DataFrame (bypassing `filter_banner`'s own
  guard) to confirm the new `safe_cluster()` fallback holds even then. This
  is a real but partial substitute for the UI test — **run
  `streamlit run app.py` locally to confirm the actual rendering**, since the
  stub does not check Streamlit widget behaviour or Plotly figure validity.

### Known issues found this session

1. **K-Means needs at least K=4 merchants.** Not called out in the Phase 4
   brief. A merchant-status = New (or any other) filter narrow enough to
   leave under 4 merchants would otherwise crash `cluster_merchants()`.
   Fixed with `safe_cluster()`'s fallback (see above); Strategic Rankings
   still scores the remaining merchants even when clustering is skipped.
2. Everything already listed in section I still applies; nothing there was
   touched.

### Next phase

Phase 5 (Methodology & Diagnostics screen, downloads, README, demo script)
was not started, per the standing instruction to stop after Phase 4.

Expected merchant resolution block on the reference data:

```
  known merchants      77
  new merchants        0
  unknown merchants    0
  auto-corrections     0
  city candidates      0
  category mapped      100,000 rows
  geo confidence       {'high': 100000}
```

Also confirm the UI still runs:

```bash
streamlit run app.py
```

Click "Use demo dataset". Expect 77 known, 0 new, 0 unresolvable merchants and
"Pipeline complete." The Executive overview and Customer segments tabs should
render 5 charts each. All six tabs should populate: expect 16 charts and 7
download buttons in total. Loading the 100k file takes about 16 seconds;
everything after that is cached.

Zero new and zero unknown is **correct** here: the baseline fully covers this
dataset, so nothing should be reclassified. If this block changes, merchant
resolution has drifted. If the 43 checks fail, v1 methodology has drifted, and
the change that caused it must be reverted rather than accommodated.


---

## N. PHASE 5.5 — STAGE 0 STANDARDISATION (added after Phase 5)

### What was added

`pipeline/standardize.py`, a reusable Cleaning & Validation phase that runs
**before** `clean.clean()`. It converts an arbitrary upload into the schema the
rest of the pipeline assumes, and reports everything it could not resolve.

The original Stage 1 notebook (`NBE - Cardlytics.ipynb`) assumed one specific
export, checked six column names, and called `sys.exit(1)` on any mismatch.
Stage 0 replaces that contract.

### Pipeline order (new)

    read_any  ->  validate  ->  standardize  ->  clean  ->  segments  ->  clusters  ->  scoring
                               ^^^^^^^^^^^ new

### What Stage 0 does

| Step | Behaviour |
|---|---|
| Column names | Normalised to alphanumeric uppercase, then matched in three tiers: exact canonical, alias table, fuzzy (cutoff 0.82) |
| Ambiguity | Two source columns claiming the same canonical role at the same tier is a hard stop, never a guess. An exact name beats an alias. |
| Requirement levels | hard (PAN, Txn date, Amount, Description, DB/CR) block; soft (Posting Date, Currency, Auth Method) are synthesised empty with a warning; optional are reported only |
| Dates | Month-first and day-first both attempted, whichever parses more cells wins, the choice is reported |
| Amounts | Currency symbols, thousands separators and accounting parentheses stripped |
| DB/CR | 20+ spellings mapped onto DEBIT TRANSACTION / CREDIT TRANSACTION; unrecognised values kept verbatim and counted |
| Dispute columns | Detected by pattern, removed, reason recorded |
| Supplied merchant/category | Renamed to `supplied_*` and ignored. Description parsing stays the source of truth. |

### LOCKED: do not weaken this

`DERIVED_NOT_SUPPLIED` in `standardize.py` lists the columns the pipeline
derives for itself. If an upload provides `merchant`, `category`, `city`,
`governorate`, `country` or `gateway`, those columns are quarantined under a
`supplied_` prefix and never read. A future developer must not "helpfully" use
them when present. The whole merchant-resolution design in section D depends on
Description being the only input.

### Byte-identical guarantee

On a file that already matches the reference schema, every Stage 0 step is a
no-op. `normalise_debit_credit` returns the original series untouched when no
value actually changes, which preserves dtype. Verified: `clean(standardize(demo))`
is `assert_frame_equal`-identical to `clean(demo)`, and all four v1 and v2
rankings match position for position.

### Stage cleaning screen

New tab between Load and Executive overview. Driven entirely by
`standardize.cleaning_summary(std_report, clean_report)`, which returns
`[{step, finding, detail, level}]`. Every figure is computed from the loaded
file. **Nothing on that screen may be hard-coded to the demo numbers.**

### What still cannot be automated

- Which of two plausible columns is the real one. Reported, never guessed.
- A Description in a format the parser was not built for. Rows resolve to
  `unknown` and are counted, but no merchant can be recovered.
- Whether a detected new city is real. Still behind the `learn_geography`
  toggle, off by default.
- FX. Multiple currencies are flagged; every amount is still treated as EGP.
- Whether a new merchant is a genuinely new business or a spelling variant
  below the 0.92 auto-correct cutoff.

### New files

- `pipeline/standardize.py`
- `tools/make_new_merchant_demo.py` (regenerates the variant below)
- `data/demo_new_merchants.xlsx` (demo.xlsx + 1,750 rows across 3 new merchants)

`data/demo.xlsx` is unchanged (md5 `baed9457b392a6ead2e2d1c4a294e66f`).

### verify.py

Paths now resolve relative to the script. `python verify.py` with no arguments
uses `data/demo.xlsx` and `outputs/`. Missing files produce a named error
instead of a traceback. It now runs the raw file through Stage 0 first, so the
verified path is the same one the app uses.


---

## O. POST-PHASE-5.5 FIXES

### 1. `avg_settlement_lag` no longer returns NaN

Returns `float | None`. `None` when `Posting Date` is absent (Stage 0 creates
it empty rather than blocking) or when no row has both dates. `app.fmt_measure`
renders `None` as "Not available" with the note "no posting dates in this file".

Methodology unchanged where data exists: `.mean()` still skips missing pairs,
so partial posting dates give the same average over the rows that have them.
Verified 0.79153 on demo.xlsx, identical to before.

### 2. Duplicate definition — a real bug was found and fixed

**The bug.** Stage 0 removes unused columns (including dispute fields) before
`clean()` runs. `clean()` then deduplicated on the reduced 10-column set. Two
genuinely distinct transactions that differ only in a removed column were
judged identical and one was silently deleted. Reproduced: a pair differing
only in `In Dispute?` lost one row.

**The fix.** The exact-duplicate decision moved into Stage 0, taken on the
frame as supplied, before any column is dropped. `clean()` gained
`deduplicate: bool = True`; every caller that runs after Stage 0 passes
`deduplicate=False`. Calling `clean()` directly on a raw export is unchanged.

This restores the original semantics rather than inventing new ones. The
business-key duplicate count is still reported and still never drops anything.

`report["duplicates"]` now carries `removed`, `decided_on_columns`,
`residual_exact`, `business_key`, `business_key_columns`.

### 3. Demo script

`DEMO_SCRIPT.md`. Six acts, roughly 12 minutes. Act 3 is the new-merchant
scenario, Act 4 covers V1 vs V2 including the stability evidence that must be
stated out loud. Act 5 (verify.py) is explicitly conditional on `outputs/`
being populated.

### 4. verify.py status

Path handling tested from four working directories, with absolute, relative
and `~` paths, plus missing-file, missing-directory and partial-directory
cases. Drift detection confirmed: perturbing a reference CSV produces named
failures and exit code 1.

**VERIFIED against the real reference CSVs.** They were supplied and are now in
`outputs/`. `python verify.py` returns **43 of 43, every check at 100.0000%**,
from the project root and from any other working directory. Drift detection
re-confirmed against the real set: perturbing one BNPL rank produces
`stage4 bnpl 97.4026%` and exit code 1.

`outputs/` is committed with the prototype so verification runs out of the box.

`segment_justification.txt` is the one reference artefact `verify.py` does not
cover, because it is prose. Every figure in it was checked by hand against the
pipeline and matches: mean 227,951, median 94,882, ratio 2.40, splits exactly
20/50/30, VIP volume 774,193,127 of 1,084,588,875 (71.4%), Low-Value 4.0%,
recency 12.92 vs 29.05, frequency 34.83 vs 13.56. The single loose figure is
the Low-Value outlier ratio, written as 6% where the data gives 5.39%. The
reference CSV gives the same 5.39%, so the prose is rounded generously, not
the code being wrong.


---

## P. UI REDESIGN (Phase 6)

### What changed, and what deliberately did not

| File | Change |
|---|---|
| `ui/theme.py` | **new** - the single source of truth for colour, type scale and chart heights |
| `ui/components.py` | **new** - masthead, journey strip, KPI cards, insight cards, profile cards, rank rows, status rows, pipeline stepper, filter chips, badges |
| `app.py` | rewritten presentation. Every pipeline call is unchanged. |
| `pipeline/charts.py` | imports `ui.theme`; heights reduced. **No figure's data logic changed.** |
| `pipeline/insights.py` | **append-only**. The original file is a strict byte prefix of the new one. |
| `pipeline/clean.py`, `clustering.py`, `scoring.py`, `segments.py`, `standardize.py`, `loader.py`, `kpis.py` | **md5-identical to before the redesign** |
| `verify.py`, `outputs/`, `data/` | untouched |

### The palette bug this fixed

`app.py` and `pipeline/charts.py` each declared their own palette and they had
drifted: app.py's `INK` was `#006547` (NBE green) and was applied to every
heading and KPI value, while charts.py's `INK` was `#10312B`. The golds
differed too (`#F79C1E` against `#C9A227`). Everything now imports `ui.theme`.

**Colour discipline, do not weaken it:** NAVY is structure, GREEN is action and
success only, GOLD is one accent per view. Making headings green again is what
made the app look like a tinted default.

### Navigation

Seven `st.tabs` replaced by a sidebar radio (`key="nav"`). Tabs computed every
screen on every rerun; the radio computes one. This also closed known issues 13
and 15.

### One global V1/V2 control

Previously three radios with three keys (`cluster_version`, `ranking_version`,
`download_version`), so a user could be on V1 in clustering and V2 in rankings
with no indication. Now a single `methodology_version` session key, read via
`active_version()`, surfaced as a masthead chip. **V1 remains the default.**

### LOCKED

- `ui/components.py` is pure presentation. If a component needs a number that
  no pipeline output provides, that is a signal to stop, not to compute it in
  the UI.
- No stability or bootstrap statistic was added. Only metrics the backend
  already produces are displayed.
- Every methodology caveat from the pre-redesign screens was carried over
  verbatim: total-spend-includes-credits, the two different average tickets,
  the sub-0.35 silhouette caveat, the narrow-ticket-spread warning, the
  four-rankings-correlate warning, the full limitations list.
- The merchant filter is a plain mask on `clean_df["merchant"]`. `safe_cluster`
  already handled the narrow-view case; that is what catches it.

### Tests added

- `tests/test_ui_contract.py` - asserts every key the interface reads exists in
  `std_report`, `report`, `thresholds`, clustering diagnostics and each ranking
  frame, for both demo files and both versions.
- `tests/test_screens.py` - drives the real app headlessly with Streamlit
  `AppTest` across every screen, both datasets, both versions, and the normal /
  narrow / empty filter cases.

Both must pass alongside `python verify.py` returning 43 of 43.

---

## K. UI-ONLY PATCH — MASTHEAD ARROW, CLICKABLE WORKFLOW BADGES, PROJECT LABEL, BUTTON CONTRAST

**Scope:** presentation only. No pipeline, reference data, or methodology file
was opened for editing. Confirmed by diffing the full project tree before and
after: only `app.py`, `ui/components.py`, and `ui/theme.py` changed.

### What changed

1. **Native sidebar-toggle vs. masthead overlap** (`ui/theme.py`). `st.logo()`
   repeats the NBE mark next to Streamlit's own collapse/expand arrow, both in
   the expanded sidebar header and in the floating control shown when the
   sidebar is collapsed — that second copy was sitting on top of the custom
   masthead's own logo. Fix hides the native logo duplicate wherever it
   appears outside the sidebar itself (`[data-testid="stSidebarCollapsedControl"]
   [data-testid="stLogo"]`, `[data-testid="stSidebarHeader"] [data-testid="stLogo"]`)
   and nudges the arrow's own vertical position to sit level with the
   masthead band. The custom `.nbe-masthead` markup and CSS are untouched.
   The arrow still opens the same native sidebar (WORKFLOW + FILTERS) — no
   new drawer component was built.
   **Not verified live** — this sandbox has no network and cannot install
   Streamlit, so this is a static code fix based on documented Streamlit
   test IDs (works for the pinned `streamlit>=1.36`). Confirm the exact
   pixel alignment on first run and nudge `top`/`left` in that CSS block if
   the arrow still reads as off-position.

2. **Clickable workflow badges** (`ui/components.py::journey`,
   `ui/theme.py`). The workflow strip was static `<span>` breadcrumb text;
   it's now a row of real `st.button` widgets, one per screen, each wrapped
   in its own `st.container(key=...)` so CSS can target done / active /
   upcoming state per badge via the key-derived class Streamlit adds to
   that container. Clicking a badge writes the target screen name into
   `st.session_state["nav"]` — the **same** key the existing sidebar radio
   already uses — so the two controls can never disagree. This also means
   `tests/test_screens.py`, which drives navigation via
   `at.radio(key="nav")`, needed no changes: that radio widget still exists,
   unchanged, and still works exactly as before.
   Call site: `ui.journey(JOURNEY, screen_index)` →
   `ui.journey(JOURNEY, screen_index, SCREEN_NAMES)` in `app.py`.

3. **Project label** (`app.py`, `ui/components.py::footer`). The masthead
   chip `"Project B  ·  Graduation Scholarship"` is now `"PROJECT GRADUATION"`.
   `footer()`'s `"NBE Cardlytics · Project B, Merchant Intelligence"` had
   "Project B" removed. "NBE Cardlytics" is unchanged everywhere. The
   `app.py` module docstring ("NBE Cardlytics, Project B merchant insight
   platform.") still says Project B by explicit request — it's a code
   comment, not user-visible.

4. **"Run demo dataset" button contrast** (`ui/theme.py`). The button's own
   `color: #FFFFFF !important` was being beaten by the global
   `p, li, span, div, label { color: #22312C }` rule matching the button's
   inner label element directly (a directly-matched rule beats an inherited
   one regardless of `!important` on the ancestor). Added explicit
   `!important` white color rules for `p`/`span`/`div` inside
   `.stButton > button[kind="primary"]`.

### Verification performed

- `python -m py_compile` on all three edited files: **pass**.
- Full-tree diff against the pre-patch copy: confirms only the three files
  above changed; `pipeline/`, `reference/`, `tests/`, `tools/`, and `data/`
  are byte-identical.
- Manually traced `tests/test_ui_contract.py` and `tests/test_screens.py`
  against the change: neither asserts on masthead/journey HTML structure;
  `test_screens.py`'s `radio(key="nav")` usage is untouched and still the
  single source of truth for navigation state.
- **Not performed** (environment limitation, not skipped by choice): actually
  running `tests/test_ui_contract.py`, `tests/test_screens.py`, or
  `streamlit run app.py`. This sandbox has no installed Streamlit and no
  network access to install it, so nothing that imports `streamlit` could be
  executed here. **Before treating this patch as verified, run on a machine
  with the project's normal environment:**
  ```
  python tests/test_ui_contract.py
  python tests/test_screens.py
  streamlit run app.py   # click through all 7 workflow badges, both the
                          # collapsed and expanded sidebar states, and the
                          # Load screen's demo button, at a wide and a
                          # narrow window width
  ```

### K.1 — Follow-up: the arrow/logo fix above did not actually work

The first attempt targeted `[data-testid="stSidebarCollapsedControl"]` /
`[data-testid="stSidebarHeader"]` and only hid a `[data-testid="stLogo"]`
child inside them. That was the wrong hook: Streamlit's own docs for
`st.logo()` state it renders the passed image in **two fixed locations by
design** — the permanent upper-left corner of the app itself (which stays
in the DOM even while the sidebar is open; the sidebar panel just slides
over it) and again inside the sidebar's own header. The upper-left copy is
not conditional on collapsed state, so scoping the fix to
`stSidebarCollapsedControl` missed it, and it kept showing up doubled next
to the arrow, on top of the masthead.

**Fix:** hide the image by its `alt="Logo"` attribute instead of a
`data-testid`, since these testids have been renamed across Streamlit
versions before (`stSidebarNav` → `stSidebar` is one on record) while the
`alt="Logo"` attribute on the rendered `<img>` is Streamlit's own stable
convention for this element:

```css
img[alt="Logo"] { display: none !important; }
```

This removes both native copies outright — the masthead already carries
the NBE logo, so there was no need to relocate or re-show either one. The
collapse/expand arrow is a separate element (a button, not an image) and
is untouched by this rule; it keeps opening and closing the sidebar
exactly as before.

**Still not verified live** for the same reason as before — no Streamlit
install / no network in this environment. Please confirm on your machine:
only one NBE logo visible, the arrow sitting to its left with no overlap,
at both a wide and a narrow window width, sidebar collapsed and expanded.
