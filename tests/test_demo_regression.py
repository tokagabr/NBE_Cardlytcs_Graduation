import sys, pandas as pd, numpy as np
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
from pipeline.clean import Vocabulary, clean
from pipeline.standardize import standardize, cleaning_summary
from pipeline.clustering import cluster_merchants
from pipeline.scoring import score_v1, score_v2
from pipeline.segments import segment_customers

raw = pd.read_excel(str(__import__("pathlib").Path(__file__).resolve().parent.parent / "data") + "/demo.xlsx")

# OLD path
old_clean, old_rep = clean(raw, Vocabulary())
# NEW path
std, srep = standardize(raw)
new_clean, new_rep = clean(std, Vocabulary(), deduplicate=False)

print("std status:", srep["status"])
print("cols in/out:", srep["column_count_in"], "->", srep["column_count_out"])
print("removed:", srep["columns_removed"])
print("dispute found:", srep["dispute_columns_found"])
print("mapped:", srep["columns_mapped"])
print("warnings:", srep["warnings"])

print("\nshape equal:", old_clean.shape == new_clean.shape, old_clean.shape, new_clean.shape)
print("columns equal:", list(old_clean.columns) == list(new_clean.columns))
try:
    pd.testing.assert_frame_equal(old_clean, new_clean)
    print("CLEAN FRAME IDENTICAL: YES")
except AssertionError as e:
    print("CLEAN FRAME DIFF:", str(e)[:500])

for k in old_rep:
    a,b = old_rep[k], new_rep[k]
    if isinstance(a, pd.DataFrame):
        same = a.equals(b)
    else:
        same = (a==b) if not isinstance(a,float) else np.isclose(a,b)
    if not same: print("REPORT DIFF", k, a, b)
print("report keys identical: done")

# downstream
c1,_=segment_customers(old_clean); c2,_=segment_customers(new_clean)
print("segments identical:", c1.equals(c2))
cl1,d1=cluster_merchants(old_clean,c1,version="v1"); cl2,d2=cluster_merchants(new_clean,c2,version="v1")
print("silhouette:", round(d1['silhouette'],6), round(d2['silhouette'],6))
r1=score_v1(old_clean,cl1); r2=score_v1(new_clean,cl2)
for d in ("partnership","loyalty","bnpl","potential"):
    a=r1[d][["merchant",f"{d}_rank"]].sort_values("merchant").reset_index(drop=True)
    b=r2[d][["merchant",f"{d}_rank"]].sort_values("merchant").reset_index(drop=True)
    print(f"  v1 {d} ranks identical:", a.equals(b))
r1=score_v2(old_clean,cl1); r2=score_v2(new_clean,cl2)
for d in ("partnership","loyalty","bnpl","potential"):
    a=r1[d][["merchant",f"{d}_rank"]].sort_values("merchant").reset_index(drop=True)
    b=r2[d][["merchant",f"{d}_rank"]].sort_values("merchant").reset_index(drop=True)
    print(f"  v2 {d} ranks identical:", a.equals(b))

print("\n--- CLEANING SUMMARY ---")
for r in cleaning_summary(srep, new_rep):
    print(f"[{r['level']:4s}] {r['step']:28s} | {r['finding']}")
    if r['detail']: print(f"{'':37s}| {r['detail'][:150]}")
