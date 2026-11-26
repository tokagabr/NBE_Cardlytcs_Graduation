import sys, pandas as pd, numpy as np
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
from pipeline.clean import Vocabulary, clean
from pipeline.standardize import standardize, cleaning_summary, resolve_columns
from pipeline import loader
from pipeline.clustering import cluster_merchants
from pipeline.scoring import score_v1
from pipeline.segments import segment_customers

raw = pd.read_excel(str(__import__("pathlib").Path(__file__).resolve().parent.parent / "data") + "/demo.xlsx")
ref_clean,_ = clean(standardize(raw)[0], Vocabulary(), deduplicate=False)
ref_ranks = None

def run(label, df, expect_status=None):
    print("\n" + "="*70); print(label); print("="*70)
    v = loader.validate(df)
    print("validate ->", v["status"], "| auto_mapped:", v["auto_mapped"] or "none",
          "| unmapped:", v["unmapped"], "| ambiguous:", v["ambiguous"])
    if v["status"] == "blocked":
        print("BLOCKED (correct behaviour if intended)")
        return None
    std, s = standardize(df)
    print("std status:", s["status"])
    print("renamed:", s["columns_mapped"])
    if s["status"] == "blocked":
        print("errors:", s["errors"]); return None
    for w in s["warnings"]: print("  warn:", w)
    cdf, rep = clean(std, Vocabulary(), deduplicate=False)
    print(f"rows {rep['rows_out']:,} | merchants known {rep['known_merchants']} new {rep['new_merchants']} unk {rep['unknown_merchants']}")
    return cdf

# --- Case 1: renamed headers, the exact example given
c1 = raw.rename(columns={"PAN":"Customer ID","Txn date":"Transaction Date","Amount":"Transaction Amount"})
out = run("CASE 1  Customer ID / Transaction Date / Transaction Amount", c1)
print("  identical to reference:", out.equals(ref_clean))

# --- Case 2: casing, underscores, extra whitespace
c2 = raw.rename(columns={"PAN":"pan","Txn date":"  TXN_DATE ","Amount":"amount",
                         "DB/CR":"db_cr","Description":"DESCRIPTION",
                         "Posting Date":"posting_date","Currency":"currency"})
out = run("CASE 2  casing / underscores / whitespace", c2)
print("  identical to reference:", out.equals(ref_clean))

# --- Case 3: different vocabulary entirely
c3 = raw.rename(columns={"PAN":"Card Number","Txn date":"Trans Date","Amount":"Txn Amount",
                         "DB/CR":"Debit/Credit","Description":"Narrative",
                         "Posting Date":"Settlement Date","Currency":"Currency Code",
                         "Primary Cardholder Auth Method":"Authentication Method"})
out = run("CASE 3  bank-export vocabulary", c3)
print("  identical to reference:", out.equals(ref_clean))

# --- Case 4: messy VALUES not just headers
c4 = raw.copy()
c4["Amount"] = c4["Amount"].map(lambda v: f"EGP {v:,.2f}")
c4["DB/CR"] = c4["DB/CR"].map({"DEBIT TRANSACTION":"D","CREDIT TRANSACTION":"C"})
c4["Txn date"] = c4["Txn date"].dt.strftime("%d/%m/%Y")
out = run("CASE 4  text amounts, D/C codes, day-first date strings", c4)
print("  amount sum matches:", np.isclose(out["Amount"].sum(), ref_clean["Amount"].sum()))
print("  dbcr counts:", out["DB/CR"].value_counts().to_dict())
print("  dates match:", (out["Txn date"].dt.date == ref_clean["Txn date"].dt.date).all())

# --- Case 5: untrusted supplied merchant/category columns
c5 = raw.copy()
c5["merchant"] = "GARBAGE MERCHANT"
c5["category"] = "Wrong Category"
out = run("CASE 5  file supplies its own merchant/category columns", c5)
print("  merchants ignored, reference still used:", out["merchant"].nunique(), "merchants")
print("  identical to reference:", out.equals(ref_clean))

# --- Case 6: required column genuinely missing -> must block
c6 = raw.drop(columns=["Description"])
run("CASE 6  Description missing (must block)", c6)

# --- Case 7: ambiguous, two columns claim Amount
c7 = raw.copy(); c7["Transaction Amount"] = c7["Amount"]
run("CASE 7  two columns claim Amount (must block)", c7)

# --- Case 8: soft column missing -> warn, still runs
c8 = raw.drop(columns=["Posting Date","Currency"])
out = run("CASE 8  Posting Date + Currency missing (must warn, not block)", c8)
print("  rows through:", len(out))
