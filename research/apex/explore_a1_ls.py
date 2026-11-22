"""EXPLORATORY: A1 market-neutral version. Each day, within the less-liquid F&O tier, long the 20% biggest gap-downs and
short the 20% biggest gap-ups AT THE OFFICIAL OPEN (auction price, from the daily candle), exit at a 5-min bar close."""
import glob, os, sys, numpy as np, pandas as pd
from engine import ROOT
rank = (ROOT / "data/angel/fno_liquidity_rank.txt").read_text().split(); liquid = set(rank[:70])
rows = []
for f in sorted(glob.glob(str(ROOT / "data/angel/stock_5m/*.csv.gz"))):
    s = os.path.basename(f)[:-7]; a = pd.read_csv(f)
    if len(a) < 5000 or s in liquid: continue
    ts = pd.to_datetime(a.timestamp.str[:19]); a["date"] = ts.dt.normalize(); a["t"] = ts.dt.hour * 60 + ts.dt.minute
    a = a[(a.t >= 555) & (a.t <= 925) & (a.date >= "2025-01-01")]
    g = a.groupby("date"); d = pd.DataFrame({"o5": g.open.first(), "t0": g.t.first(), "l0": g.low.first(), "h0": g.high.first()})
    for nm, tt in (("c5", 555), ("c10", 560), ("c15", 565), ("c30", 580), ("cl", 925)): d[nm] = a[a.t == tt].set_index("date").close
    d = d[d.t0 == 555]
    x = pd.read_csv(ROOT / "data/angel/daily" / f"{s}.csv.gz"); x.index = pd.to_datetime(x.timestamp.str[:10])
    d["o"] = x.open.reindex(d.index); d["pc"] = x.close.shift(1).reindex(d.index); d["sym"] = s
    rows.append(d.reset_index())
j = pd.concat(rows).dropna(subset=["o", "pc", "c5", "cl"])
print("less-liquid stocks:", j.sym.nunique(), "| 5-min first-bar open == official open:", f"{np.isclose(j.o5, j.o, rtol=2e-5).mean():.1%}", "| official open inside first bar's range:", f"{((j.o >= j.l0 * 0.99999) & (j.o <= j.h0 * 1.00001)).mean():.1%}")
j["gap"] = j.o / j.pc - 1
j["rk"] = j.groupby("date").gap.rank(pct=True); j["n"] = j.groupby("date").gap.transform("size")
j = j[j.n >= 15]
def run(q, col, cost, lo="2025-01-01", hi="2026-12-31", entry="o"):
    y = j[(j.date >= lo) & (j.date <= hi)]
    r = (y[col] / y[entry] - 1) * 1e4
    L = r[y.rk <= q].groupby(y.date[y.rk <= q]).mean(); S = r[y.rk > 1 - q].groupby(y.date[y.rk > 1 - q]).mean()
    return ((L - S) / 2).dropna() - cost, L, S
for era, lo, hi in (("before (2025-01..2025-12-07)", "2025-01-01", "2025-12-07"), ("after (2025-12-08..2026-11)", "2025-12-08", "2026-12-31"), ("after pre-open revision (2026-09-07..)", "2026-09-07", "2026-12-31")):
    print(f"\n=== {era}")
    for col in ("c5", "c10", "c15", "c30", "cl"):
        n, L, S = run(.2, col, 8, lo, hi); mg = n.groupby([n.index.year, n.index.month]).sum()
        print(f"  exit {col:3s}: net {n.mean():+6.1f}bp/unit/day (gross {n.mean()+8:+.1f}; long leg {L.mean():+.1f}, short leg {-S.mean():+.1f}) sd {n.std():.0f} t {n.mean()/n.std()*np.sqrt(len(n)):+.1f} win {(n>0).mean():.0%} worst {n.min():.0f}bp months+ {int((mg>0).sum())}/{len(mg)}")
    n12 = run(.2, "c5", 12, lo, hi)[0]; n10 = run(.1, "c5", 8, lo, hi)[0]; n5m = run(.2, "c5", 8, lo, hi, entry="o5")[0]
    print(f"  09:20 exit at 12bp cost: {n12.mean():+.1f}; top/bottom 10% instead of 20%: {n10.mean():+.1f}; entry at first 5-min print instead of official open: {n5m.mean():+.1f}")
n = run(.2, "c5", 8, "2025-12-08")[0]
print("\nafter-era monthly net bp/unit/day:", n.groupby([n.index.year, n.index.month]).mean().round(1).to_dict())
print(f"Rs 4L account, 5x intraday leverage = Rs 20L gross: mean Rs {n.mean()/1e4*20e5:,.0f}/day, sd Rs {n.std()/1e4*20e5:,.0f}, worst day Rs {n.min()/1e4*20e5:,.0f} (paper, assumes auction fills)")
