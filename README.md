# NBE Cardlytics: Merchant Insight Prototype

Reruns the full Project B analysis on any uploaded transaction export:
cleaning, customer segmentation, merchant clustering, scoring and rankings.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501. Click "Use demo dataset", or upload your own
`.xlsx` / `.csv`. First load of the 100k demo file takes about 16 seconds;
everything after that is cached.

## Check the analysis is intact

```bash
python verify.py
```

Reproduces all six original notebook outputs from the raw Excel.
Expected: `All 43 checks passed.`

## Screens

| Screen | What it shows |
|---|---|
| Load | Upload, validation, cleaning report, new merchants, unrecognised cities |
| Executive overview | 7 KPIs and 5 charts across spend, geography, gateways and time |
| Customer segments | RFM distributions and VIP / Mass / Low-Value behaviour |
| Merchant clustering | K selection, PCA scatter, cluster profiles, concentration quadrant |
| Strategic rankings | Partnership, loyalty, BNPL and potential, with V1/V2 comparison |
| Methodology | Derived parameters, ticket diagnostic, V1 vs V2 weights, limitations, downloads |

## V1 and V2

**V1** reproduces the team's original analysis exactly and is the reference.
**V2** is a correction shown beside it, never in place of it. Both are
switchable on the clustering, rankings and download screens.

The Methodology screen explains every V2 change and, importantly, shows the
ticket-size diagnostic: if average ticket barely varies between merchants, no
scoring formula can make the four deliverables genuinely different. That is a
property of the data, not of the formulas.

## Merchant handling

A merchant absent from `reference/merchant_categories.csv` is **new**, not
unknown. New merchants flow through clustering, scoring and every ranking with
no penalty. `unknown` is reserved for descriptions where no merchant name could
be isolated at all. See section D of `HANDOFF.md`.

## Layout

| Path | Purpose |
|---|---|
| `app.py` | Streamlit interface. Contains no analysis logic. |
| `pipeline/` | All analysis. Testable without the UI. |
| `reference/` | Editable vocabularies: merchants, categories, cities, keywords. |
| `data/demo.xlsx` | The 100k-row demo export. |
| `verify.py` | Verification harness. |
| `HANDOFF.md` | Full project state, methodology and continuation notes. |


## Verification

The seven reference CSVs ship in `outputs/`, so this runs as-is:

```
python verify.py                       # defaults to data/demo.xlsx and outputs/
python verify.py data/demo.xlsx outputs
```

Paths resolve relative to the script, so it runs from any working directory.

## Demo datasets

| File | Purpose |
|---|---|
| `data/demo.xlsx` | Reference dataset. Never modify. All verification runs against this. |
| `data/demo_new_merchants.xlsx` | Same data plus three merchants absent from the reference list, for demonstrating new-merchant detection. Regenerate with `python tools/make_new_merchant_demo.py`. |
