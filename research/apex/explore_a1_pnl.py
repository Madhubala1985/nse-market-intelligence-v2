"""EXPLORATORY: A1 day-by-day paper P&L on 5-min data (less-liquid F&O tier), plus a closing-auction (CAS) check."""
import glob, os, numpy as np, pandas as pd
from engine import ROOT
rank = (ROOT / "data/angel/fno_liquidity_rank.txt").read_text().split()
liquid = set(rank[:70])
rows = []
for f in sorted(glob.glob(str(ROOT / "data/angel/stock_5m/*.csv.gz"))):
    s = os.path.basename(f)[:-7]; a = pd.read_csv(f)
    if len(a) < 5000: continue
    ts = pd.to_datetime(a.timestamp.str[:19]); a["date"] = ts.dt.normalize(); a["t"] = ts.dt.hour * 60 + ts.dt.minute
    a = a[(a.t >= 555) & (a.t <= 925) & (a.date >= "2025-01-01")]
    g = a.groupby("date")
    d = pd.DataFrame({"o": g.open.first(), "t0": g.t.first()})
    for nm, tt in (("c5", 555), ("c10", 560), ("c15", 565), ("c30", 580), ("cl", 925)): d[nm] = a[a.t == tt].set_index("date").close
    d = d[d.t0 == 555]; d["prev"] = d.cl.shift(1); d["sym"] = s; d["liquid"] = s in liquid
    dd = ROOT / "data/angel/daily" / f"{s}.csv.gz"
    if dd.exists():
        x = pd.read_csv(dd); x.index = pd.to_datetime(x.timestamp.str[:10]); d["dclose"] = x.close.reindex(d.index); d["dopen"] = x.open.reindex(d.index)
    rows.append(d.reset_index())
j = pd.concat(rows).dropna(subset=["prev", "c5", "cl"]).reset_index(drop=True)
j["gap"] = j.o / j.prev - 1
print("stocks:", j.groupby("liquid").sym.nunique().to_dict(), "(False = less-liquid tier)")
COST = 8e-4
for era, lo, hi in (("2025-01..2025-12-07 (before F&O pre-open)", "2025-01-01", "2025-12-07"), ("2025-12-08..2026-11 (after)", "2025-12-08", "2026-12-31"), ("2026-09-07.. (after pre-open revision)", "2026-09-07", "2026-12-31")):
    x = j[(~j.liquid) & (j.date >= lo) & (j.date <= hi) & (j.gap.abs() > 0.0075)].copy()
    x["side"] = -np.sign(x.gap)
    print(f"\n=== less-liquid tier, {era}: {len(x)} events on {x.date.nunique()} days")
    for nm, col in (("exit 09:20", "c5"), ("exit 09:25", "c10"), ("exit 09:30", "c15"), ("exit 09:45", "c30"), ("exit 15:30", "cl")):
        x["r"] = x.side * (x[col] / x.o - 1) - COST
        day = x.groupby("date").r.agg(["mean", "size"])
        expo = (day["size"].clip(upper=5) / 5)                 # each position = 20% of capital-notional, max 5
        dr = (day["mean"] * expo).reindex(pd.DatetimeIndex(sorted(j[(j.date >= lo) & (j.date <= hi)].date.unique()))).fillna(0)
        print(f"  {nm}: per-event net {x.r.mean()*1e4:+6.1f}bp (gross {x.r.mean()*1e4+8:+.1f}), win {(x.r>0).mean():.0%}; long side {x[x.side>0].r.mean()*1e4:+.1f} / short side {x[x.side<0].r.mean()*1e4:+.1f}; "
              f"daily on notional: mean {dr.mean()*1e4:+.1f}bp sd {dr.std()*1e4:.0f}bp Sharpe {dr.mean()/dr.std()*np.sqrt(250):+.1f} worst day {dr.min()*1e4:.0f}bp, months+ {int((dr.groupby([dr.index.year, dr.index.month]).sum()>0).sum())}/{dr.groupby([dr.index.year, dr.index.month]).ngroups}")
# gap size split (after era)
x = j[(~j.liquid) & (j.date >= "2025-12-08")].copy(); x["side"] = -np.sign(x.gap); x["r"] = x.side * (x.c5 / x.o - 1) * 1e4
print("\nafter-era gross fade to 09:20 by |gap| size:", x.groupby(pd.cut(x.gap.abs() * 1e4, [0, 25, 50, 75, 100, 150, 250, 1e4]), observed=True).r.agg(["mean", "count"]).round(1).to_dict("index"))
# ---- closing auction (CAS, live 2026-08-03): official close vs last regular 5-min close
c = j[(j.date >= "2026-08-03")].dropna(subset=["dclose"]).copy()
c["disloc"] = (c.dclose / c.cl - 1) * 1e4
c = c.sort_values(["sym", "date"]); c["next_o"] = c.groupby("sym").o.shift(-1); c["next_c5"] = c.groupby("sym").c5.shift(-1)
c["on_from_close"] = (c.next_o / c.dclose - 1) * 1e4
c["on_x"] = c.on_from_close - c.groupby("date").on_from_close.transform("mean")
print(f"\n=== CAS check since 2026-08-03: n {len(c)}, |official close - 15:30 price| median {c.disloc.abs().median():.1f}bp, 90th pct {c.disloc.abs().quantile(.9):.1f}bp")
print(f"corr(dislocation, next overnight return vs peers) = {c.disloc.corr(c.on_x):+.3f}; slope {np.polyfit(c.dropna(subset=['on_x']).disloc, c.dropna(subset=['on_x']).on_x, 1)[0]:+.2f} (−1 = full reversal by next open)")
big = c[c.disloc.abs() > c.disloc.abs().quantile(.9)]
print(f"top-decile dislocations: mean |disloc| {big.disloc.abs().mean():.1f}bp, reversal captured by next open {(-np.sign(big.disloc)*big.on_x).mean():+.1f}bp (delivery round trip costs ~25bp)")
