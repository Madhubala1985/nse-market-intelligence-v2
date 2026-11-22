"""EXPLORATORY: where inside the day does the gap fade happen? Angel 5-min bars, F&O stocks, 2023-2026."""
import glob, os, numpy as np, pandas as pd
from engine import ROOT
rows = []
for f in sorted(glob.glob(str(ROOT / "data/angel/stock_5m/*.csv.gz"))):
    s = os.path.basename(f)[:-7]
    a = pd.read_csv(f)
    if len(a) < 5000: continue
    ts = pd.to_datetime(a.timestamp.str[:19]); a["date"] = ts.dt.normalize(); a["t"] = ts.dt.hour * 60 + ts.dt.minute
    a = a[(a.t >= 555) & (a.t <= 925)]
    g = a.groupby("date")
    d = pd.DataFrame({"o": g.open.first(), "t0": g.t.first(), "v0": g.volume.first(), "h0": g.high.first(), "l0": g.low.first()})
    for nm, tt in (("c5", 555), ("c10", 560), ("c15", 565), ("c30", 580), ("c60", 610), ("c150", 700), ("cl", 925)):
        d[nm] = a[a.t == tt].set_index("date").close
    d = d[d.t0 == 555]
    d["prev"] = d.cl.shift(1)
    dd = ROOT / "data/angel/daily" / f"{s}.csv.gz"
    if dd.exists():
        x = pd.read_csv(dd); x.index = pd.to_datetime(x.timestamp.str[:10]); d["dopen"] = x.open.reindex(d.index); d["dclose"] = x.close.reindex(d.index)
    d["sym"] = s
    rows.append(d.reset_index())
j = pd.concat(rows).dropna(subset=["prev", "c5", "cl"])
j["gap"] = j.o / j.prev - 1
print("stocks", j.sym.nunique(), "stock-days", len(j), j.date.min().date(), j.date.max().date())
print("5m first-bar open vs Angel DAILY open: exactly equal %.1f%%, |diff| median %.2fbp, mean signed %.2fbp" % ((np.isclose(j.o, j.dopen, rtol=1e-5)).mean() * 100, ((j.o / j.dopen - 1).abs() * 1e4).median(), ((j.o / j.dopen - 1) * 1e4).mean()))
print("first-bar range median %.1fbp; first-bar volume share of day n/a" % (((j.h0 / j.l0 - 1) * 1e4).median()))
j["rk"] = j.groupby("date").gap.rank(pct=True)
j["n"] = j.groupby("date").gap.transform("size")
j = j[j.n >= 20].reset_index(drop=True)
seg = {"0-5m": j.c5 / j.o - 1, "5-10m": j.c10 / j.c5 - 1, "10-15m": j.c15 / j.c10 - 1, "15-30m": j.c30 / j.c15 - 1, "30-60m": j.c60 / j.c30 - 1, "60m-close": j.cl / j.c60 - 1, "open-close": j.cl / j.o - 1, "5m-close": j.cl / j.c5 - 1}
S = pd.DataFrame(seg) * 1e4
mk = S.groupby(j.date).transform("mean")           # equal-weight market move in the same segment
X = S - mk
print("\nMarket-adjusted return by gap decile (bp), all years:")
dec = pd.cut(j.rk, [0, .05, .1, .2, .8, .9, .95, 1.0], labels=["bot5%", "5-10%", "10-20%", "mid", "80-90%", "90-95%", "top5%"])
print(X.groupby(dec, observed=True).mean().round(1).to_string())
print("\nmean gap by bucket (bp):", (j.gap * 1e4).groupby(dec, observed=True).mean().round(0).to_dict())
ls = lambda col, lo=.1, hi=.9: (X[col][j.rk <= lo].groupby(j.date[j.rk <= lo]).mean() - X[col][j.rk > hi].groupby(j.date[j.rk > hi]).mean()) / 2
print("\nL/S fade (long bottom-gap decile, short top-gap decile), bp per unit gross per day:")
for col in ("0-5m", "5-10m", "10-15m", "15-30m", "30-60m", "60m-close", "open-close", "5m-close"):
    r = ls(col).dropna(); yr = r.groupby(r.index.year).mean()
    print(f"  {col:10s} mean {r.mean():+6.2f}  t {r.mean()/r.std()*np.sqrt(len(r)):+6.1f}  win {(r>0).mean():.0%}  by year {yr.round(1).to_dict()}")
r = ls("0-5m", .05, .95).dropna(); print(f"  top/bottom 5% 0-5m: mean {r.mean():+.2f} t {r.mean()/r.std()*np.sqrt(len(r)):+.1f} by year {r.groupby(r.index.year).mean().round(1).to_dict()}")
j.assign(**{k: v for k, v in S.items()}).to_pickle("data/apex/open5m.pkl")
