# NBE Cardlytics: Merchant Insight Prototype

Reruns the full Project B analysis on any uploaded transaction export:
cleaning, customer segmentation, merchant clustering, scoring and rankings.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501. Click "Run demo dataset", or upload your own
`.xlsx` / `.csv`. First load of the 100k demo file takes about 16 seconds;
everything after that is cached.

**Windows, one click:** double-click `Run_NBE_Cardlytics.bat` in the project
folder. It creates a `venv`, installs `requirements.txt`, starts the app and
opens the browser. The first run needs internet and takes a few minutes; later
runs start in seconds. It needs Python 3.9 or newer on the PATH. Close the
black window to stop the app.

## Check the analysis is intact

```bash
python verify.py
```

Reproduces all six original notebook outputs from the raw Excel.
Expected: `All 43 checks passed.`

## Screens

| Screen | What it shows |
|---|---|
| Load | Animated hero with the upload box, demo picker, validation, cleaning report, new merchants, unrecognised cities |
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
| `ui/` | Theme (`theme.py`), reusable components (`components.py`) and the animated landing hero (`hero.py`). |
| `.streamlit/config.toml` | Theme colours and app settings, including `toolbarMode = "minimal"`. |
| `Run_NBE_Cardlytics.bat` | One-click Windows launcher. |
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

## Appearance and devices

- **Light theme only.** The palette is fixed, and the app menu (which holds the
  Dark/Light switch) is hidden through `toolbarMode = "minimal"`. A real dark
  theme would mean redesigning every colour, so it is not supported.
- **Phones and narrow windows.** The sidebar starts collapsed (open it with the
  `»` button), the workflow strip at the top becomes a single row you swipe
  sideways, and side-by-side blocks stack.
- The Load screen keeps the hero visible at all times, including after a run, so
  you can switch between the reference and new-merchant demos without scrolling.

## Deploying (Streamlit Community Cloud)

1. Push the project to GitHub. `.gitignore` already excludes `venv/` and
   `__pycache__/`.
2. In Streamlit Community Cloud, create an app from the repo, branch `main`,
   main file `app.py`. Dependencies come from `requirements.txt`.
3. Every push to `main` redeploys. If the app looks stale, use **Manage app**
   then **Reboot app**, and hard-refresh the page.

The Fork button, GitHub icon and Manage app button on the hosted app belong to
Streamlit Community Cloud, not to this project.

## Team

Saleh, Zeyad, Yousef, Toka and Aya. The names are listed at the foot of every
page (`ui.team_footer(...)` at the end of `app.py`).
