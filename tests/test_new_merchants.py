import sys, pandas as pd; sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
from pipeline.clean import Vocabulary, clean
from pipeline.standardize import standardize
from pipeline.clustering import cluster_merchants
from pipeline.scoring import score_v1, score_v2
from pipeline.segments import segment_customers

raw = pd.read_excel(str(__import__("pathlib").Path(__file__).resolve().parent.parent / "data") + "/demo_new_merchants.xlsx")
std,_ = standardize(raw); cdf, rep = clean(std, Vocabulary(), deduplicate=False)
NEW = {"NOOR ELECTRONICS","SHIFA PHARMACY","BARAKA TRADING"}

print("1. detected as new:", rep["new_merchants"], "==3 ->", rep["new_merchants"]==3)
print("2. not unknown:    ", rep["unknown_merchants"], "==0 ->", rep["unknown_merchants"]==0)
print("3. not dropped:    ", len(cdf), "==", len(raw), "->", len(cdf)==len(raw))
cust,_ = segment_customers(cdf)
for ver in ("v1","v2"):
    cl,d = cluster_merchants(cdf, cust, version=ver)
    sub = cl[cl.merchant.isin(NEW)][["merchant","cluster_name","merchant_status"]]
    print(f"4. clustering {ver}: {len(sub)}/3 clustered, silhouette {d['silhouette']:.3f}")
    for _,r in sub.iterrows(): print(f"     {r['merchant']:20s} -> {r['cluster_name']} [{r['merchant_status']}]")
    rk = score_v1(cdf,cl) if ver=="v1" else score_v2(cdf,cl)
    n = len(rk["partnership"])
    line = []
    for dl in ("partnership","loyalty","bnpl","potential"):
        rr = rk[dl][rk[dl].merchant.isin(NEW)][["merchant",f"{dl}_rank"]]
        line.append(f"{dl}={sorted(rr[f'{dl}_rank'].tolist())}")
    print(f"5. rankings {ver} (of {n}):", " ".join(line))
sub = cdf[cdf.merchant.isin(NEW)][["merchant","category","category_status","governorate","city","geo_confidence","gateway"]].drop_duplicates(subset=["merchant"])
print("\n6. category/geography resolution:")
print(sub.to_string(index=False))
print("\n   governorates per new merchant:", cdf[cdf.merchant.isin(NEW)].groupby("merchant")["governorate"].nunique().to_dict())
print("\n7. original demo.xlsx untouched:")
import subprocess; print("  ", subprocess.run(["md5sum",str(__import__("pathlib").Path(__file__).resolve().parent.parent / "data") + "/demo.xlsx"],capture_output=True,text=True).stdout.strip())
