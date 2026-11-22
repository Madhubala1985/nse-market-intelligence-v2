"""EXPLORATORY: minute-by-minute timing of the non-F&O auction fade (42 sampled stocks, 1-min bars, last ~3 months)."""
import glob, os, numpy as np, pandas as pd
from engine import ROOT
rows = []
for f in sorted(glob.glob(str(ROOT / "data/angel/stock_1m_nonfo/*.csv.gz"))):
    s = os.path.basename(f)[:-7]; a = pd.read_csv(f)
    if len(a) < 3000: continue
    ts = pd.to_datetime(a.timestamp.str[:19]); a["date"] = ts.dt.normalize(); a["t"] = ts.dt.hour * 60 + ts.dt.minute
    a = a[(a.t >= 555) & (a.t <= 929)]
    g = a.groupby("date"); d = pd.DataFrame({"o": g.open.first(), "t0": g.t.first(), "v1": g.volume.first(), "h1": g.high.first(), "l1": g.low.first(), "cl": g.close.last()})
    for k in (1, 2, 3, 4, 5, 10, 15, 30):
        d[f"m{k}"] = a[a.t == 554 + k].set_index("date").close
    d["o2"] = a[a.t == 556].set_index("date").open          # first print of the 2nd minute (09:16:00)
    d = d[d.t0 == 555]; d["pc"] = d.cl.shift(1); d["sym"] = s; d["turn1"] = d.v1 * d.o
    rows.append(d.reset_index())
j = pd.concat(rows).dropna(subset=["pc", "m1", "m5"]); j["gap"] = j.o / j.pc - 1; j = j[j.gap.abs() < .15]
j["rk"] = j.groupby("date").gap.rank(pct=True); j["n"] = j.groupby("date").gap.transform("size"); j = j[j.n >= 20]
print("stocks", j.sym.nunique(), "days", j.date.nunique(), j.date.min().date(), "..", j.date.max().date(), "| first-minute turnover median Rs %.1f lakh; first-minute range median %.0fbp" % (j.turn1.median() / 1e5, ((j.h1 / j.l1 - 1) * 1e4).median()))
def ls(a, b):
    r = (j[b] / j[a] - 1) * 1e4
    L = r[j.rk <= .2].groupby(j.date[j.rk <= .2]).mean(); S = r[j.rk > .8].groupby(j.date[j.rk > .8]).mean(); x = ((L - S) / 2).dropna()
    return x.mean(), x.mean() / x.std() * np.sqrt(len(x)), (x > 0).mean()
print("\nhedged quintile L/S, gross bp per unit per day, by segment:")
for a, b, lab in (("o", "m1", "09:15:00 first print -> 09:16"), ("m1", "m2", "09:16 -> 09:17"), ("m2", "m3", "09:17 -> 09:18"), ("m3", "m5", "09:18 -> 09:20"), ("m5", "m10", "09:20 -> 09:25"), ("m10", "m30", "09:25 -> 09:45"),
                  ("o", "m5", "TOTAL first print -> 09:20"), ("o2", "m5", "enter 09:16:00 print -> 09:20"), ("o2", "m15", "enter 09:16:00 print -> 09:30"), ("m1", "m5", "enter 09:16 close -> 09:20")):
    m, t, w = ls(a, b); print(f"  {lab:34s} {m:+6.1f}  (t {t:+5.1f}, positive days {w:.0%})")
# where inside the first minute's range does the first print sit? (1 = at the high, 0 = at the low)
j["pos"] = (j.o - j.l1) / (j.h1 - j.l1).replace(0, np.nan)
print("\nfirst print's position inside the first-minute range (0=low,1=high): gap-up legs %.2f, gap-down legs %.2f, middle names %.2f" % (j[j.rk > .8].pos.mean(), j[j.rk <= .2].pos.mean(), j[(j.rk > .4) & (j.rk <= .6)].pos.mean()))
print("first-minute share of the gap given back: gap-up legs %.0f%%, gap-down legs %.0f%%" % (-100 * ((j.m1 / j.o - 1)[j.rk > .8].mean() / j.gap[j.rk > .8].mean()), -100 * ((j.m1 / j.o - 1)[j.rk <= .2].mean() / j.gap[j.rk <= .2].mean())))
