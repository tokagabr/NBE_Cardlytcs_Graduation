# Demo script

A run sheet for presenting the prototype. Roughly 12 minutes at a normal pace,
or 6 if you cut the sections marked *optional*.

It assumes nothing has been loaded yet. Every number below will appear on
screen when you follow the steps; none of them are typed into the app.

---

## Before you start

```
cd nbe-prototype
pip install -r requirements.txt
streamlit run app.py
```

Checklist:

- [ ] Both demo files present: `data/demo.xlsx`, `data/demo_new_merchants.xlsx`
- [ ] App opens on the **Load** tab with "No dataset loaded yet"
- [ ] Browser zoom at 100%, window wide enough that the six-cell metric strips
      stay on one row
- [ ] If you will run `verify.py` live, the seven reference CSVs are in
      `outputs/` first. If they are not there, do not run it. Skip Act 5.

Have a second terminal open at the project root if you plan to run anything
from the command line.

---

## Act 1 — Load and Stage cleaning (3 min)

**The point of this act:** the prototype does the cleaning, not a person.

1. **1 Load** in the sidebar. Leave the radio on *Reference dataset*. Click
   **Run demo dataset**.

   > "This is the same dummy export the team worked from. Nothing has been
   > pre-cleaned. Everything from here on is the app."

2. Point at the **Validation** block. It will say all required columns are
   present.

   > "It checks the schema before it computes anything. If a required column
   > were missing it would stop here and say which one, rather than guess."

3. Go to **2 Data Quality** in the sidebar.

   > "This is the part that used to be a notebook someone ran by hand."

   Walk the metric strip left to right: rows received, rows processed,
   columns standardised, merchants resolved, outliers flagged, unresolved
   issues.

4. Point at the table. Call out four rows specifically:

   | Row | What to say |
   |---|---|
   | Columns removed | Dispute tracking columns, detected by pattern and removed with the reason recorded |
   | Date parsing | It reports which reading it used, month-first or day-first, rather than assuming |
   | Debit/Credit normalisation | Shows the split it found |
   | Outliers | The threshold is recomputed from this file, not inherited from the original dataset |

5. Finish on the last row: **Unresolved issues: None**.

   > "Nothing in this file needed a human. On a messier file this line is the
   > one that matters, and every item under it appears as a warning below."

*Optional:* click **Download cleaning report (CSV)** to show it is exportable.

---

## Act 2 — Executive overview and segments (2 min)

6. **3 Executive Overview**.

   > "Seven measures, all translated one-for-one from the team's Power BI
   > file, so the app and the dashboard agree."

   Read the caption under the strip about total spend including credits while
   the merchant rankings are debit only. Say it before anyone asks.

7. **4 Customer Segments**. Show the RFM segmentation and the VIP / Mass /
   Low-Value split.

*Optional:* open a sidebar filter, pick one governorate, and show every screen
reacting. Then clear it. Do not leave a filter on by accident; the rest of the
script assumes no filters.

---

## Act 3 — The new-merchant scenario (4 min) — **the important one**

**The point of this act:** a merchant the system has never seen is treated as a
real merchant, not an error.

8. Go back to **1 Load**. Change the radio to **New merchant scenario**.
   Click **Run demo dataset**.

   > "Same file, plus three merchants that do not exist anywhere in the
   > reference list. This is what happens when NBE onboards someone new."

9. Stay on **1 Load**. The dataset card shows Merchants broken into
   known / new / unresolved, and a gold chip appears in the masthead.

   > "Three separate counts. New and unresolvable are never combined. A
   > merchant being absent from our list does not make it unknown."

   The **New merchants detected** table appears below it.

10. Go to **2 Data Quality**. The "New merchants detected" section now shows
    three cards. Walk them and make the contrast explicit:

    | Merchant | Category | Status | Why it matters |
    |---|---|---|---|
    | NOOR ELECTRONICS | Electronics & Appliances | inferred | Guessed from keywords in the name |
    | SHIFA PHARMACY | Health & Pharmacy | inferred | Same |
    | BARAKA TRADING | Unknown | Unknown | No keyword to go on, so it says so |

    > "The third one is the honest case. The system could not work out a
    > category, so it reports Unknown rather than inventing one. An inferred
    > category is never presented as if it came from the reference list."

    Also point out geography resolved at high confidence for all three.

11. **5 Merchant Clustering**. The new merchants are in the clusters,
    carrying a **New** badge. Use the merchant-status filter in the sidebar to
    show only new merchants, then clear it.

    > "No special formula, no penalty, no exclusion. They cluster like anyone
    > else."

12. **Strategic rankings** tab. Leave it on V1. Find the three merchants in the
    rankings.

    > "They are ranked. A new merchant can be a partnership target on day one."

13. Switch the sidebar **Analysis Method** to V2 Enhanced. Watch the BNPL tab.

    > "Under V2 these three move sharply up the BNPL list, because V2 has a
    > ticket-size term and V1 does not. Which brings us to the next part."

---

## Act 4 — V1 versus V2 (3 min)

14. Stay on **6 Strategic Rankings**. Load the **Reference dataset** again first
    so the numbers match what follows. Sidebar method on **V1 Baseline**.

    Show the BNPL top 6: six supermarkets.

    > "The brief says BNPL should target high-ticket merchants. This returns
    > supermarkets, because the V1 formula is half total spend and half
    > transaction count. There is no ticket-size term in it at all. That is
    > the defect we found."

15. Switch to **V2 Enhanced**. The BNPL top 6 becomes Metro Market, Careem, Pizza Hut,
    Lavazza, H&M, Costa Coffee.

    > "V2 adds average ticket and high-ticket share. The list changes
    > completely."

16. Open **Compare V1 and V2 for BNPL** inside the BNPL tab. Read the movement
    signal cards, then the chart.

    > "BNPL moves about 17 places per merchant on average. Partnership and
    > loyalty move under two. So almost all of the difference between the two
    > versions is the BNPL fix."

17. **7 Methodology**. Open section 6, Validation & Diagnostics.

    **Say this part out loud. Do not skip it.**

    > "V2 is methodologically correct, but I want to be straight about what
    > this dataset can support. Average ticket across all 77 merchants varies
    > by under 8%. High-ticket share varies by about one percentage point. The
    > synthetic generator drew amounts from one global distribution without
    > conditioning on merchant. So 70% of the V2 BNPL weight sits on features
    > that barely vary."
    >
    > "I tested it: resampling 70% of the data and rescoring, the V1 BNPL
    > order reproduces at 0.995 Spearman. V2 reproduces at 0.81. The V2
    > ordering is the right formula on data that cannot support it yet."
    >
    > "That is why V1 stays the default and V2 is a toggle. On real NBE data
    > with real ticket variation, V2 is the one you would want."

    This is the strongest moment in the demo. It shows you validated your own
    correction instead of just asserting it.

---

## Act 5 — Verification (1 min) — **only if `outputs/` is populated**

18. Second terminal:

    ```
    python verify.py
    ```

    > "Every stage is checked against the team's original notebook outputs,
    > column by column. It has to come back clean or the methodology has
    > drifted."

**If the reference CSVs are not in `outputs/`, skip this act entirely.** Do not
run the command to show the error message; it reads as a failure on stage.

---

## Act 6 — Close (30 sec)

19. **7 Methodology**, scroll to the Export centre and press **Prepare exports**.

    > "Every table on every screen exports to CSV, including the cleaning
    > report and the merchant status column, so the outputs are reusable
    > outside the app."

Closing line:

> "Upload a new export, and the cleaning, segmentation, clustering and all four
> rankings rerun end to end. Two scoring versions side by side so the
> methodology choice is visible rather than buried."

---

## If something goes wrong

| Problem | What to do |
|---|---|
| A screen is empty | You opened it before loading. Go to 1 Load, click Run demo dataset. |
| Numbers look wrong | A sidebar filter is still on. The green chips under the breadcrumb name every active filter; clear them in the sidebar. |
| Clustering or rankings are slow | Expected when you open a V1-vs-V2 expander, which scores twice. Give it a few seconds and keep talking. |
| Toggling `learn_geography` hangs | It reruns the whole pipeline, about 11 seconds on the 100k file. Do not toggle it during the demo; there is nothing to show on this data. |
| App will not start | `pip install -r requirements.txt`, then check you are in the `nbe-prototype` directory. |

---

## Questions you should expect

**"Why are there two versions instead of one correct one?"**
Because the team's V1 is what was submitted and what the Power BI dashboard
uses. Replacing it silently would make the app disagree with a delivered
artefact. Showing both makes the correction auditable.

**"Why is the V2 clustering silhouette lower?"**
0.325 to 0.223. V2 removes six correlated size proxies from the feature set.
Lower separation is the expected cost of clustering on behaviour rather than
size. It is a real trade-off, not a bug.

**"Why doesn't jewellery top the V2 BNPL list?"**
Because in this dataset jewellery has low average tickets. Damas is 9,879 EGP,
below the overall mean. The data does not reflect real ticket sizes. Say this
plainly; it is a property of the dummy data, not of the method.

**"What happens if we upload a file with different column names?"**
It maps them. `Customer ID`, `Card Number`, `Transaction Date`, `Trans Date`,
`Transaction Amount` and about a hundred other variants are recognised. If two
columns could both be the same field, it stops and asks rather than guessing.

**"Can it handle a file that is missing a column?"**
Depends which. Five columns are load-bearing and it stops with a named error.
The rest it creates empty, warns about, and carries on; the measures that
depend on them read "Not available" instead of showing a wrong number.

**"How big a file can it handle?"**
Tested at 100,000 rows. Above roughly a million the description parser would
need caching. Not a limitation for a prototype.


---

## Navigation reference (after the UI redesign)

Navigation is the numbered list in the sidebar, not tabs across the top.

| Sidebar item | What it answers |
|---|---|
| 1 Load | Where does the data come from? |
| 2 Data Quality | What happened to this file? |
| 3 Executive Overview | What should an executive understand? |
| 4 Customer Segments | Who are the cardholders? |
| 5 Merchant Clustering | What kind of merchant is each one? |
| 6 Strategic Rankings | Which merchants do we act on? |
| 7 Methodology | What did we build, and why? |

The **Analysis Method** selector (V1 Baseline / V2 Enhanced) sits in the sidebar
and appears only on screens 5, 6 and 7. It is one global control: whatever you
select applies to clustering, rankings and exports together, and the active
method is shown as a chip in the masthead. V1 is the default.

Filters live in the sidebar under Period, Customers and Merchants, collapsed by
default. Active filters appear as green chips under the breadcrumb on every
analysis screen.
