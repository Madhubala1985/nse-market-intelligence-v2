"""EXPLORATORY: first-5-minute gap fade, liquid vs less-liquid F&O stocks, 2025 vs 2026 (after F&O pre-open began 2025-12-08)."""
import glob, os, numpy as np, pandas as pd
from engine import ROOT
liquid = set("HDFCBANK RELIANCE ICICIBANK BSE BHARTIARTL INFY SBIN ETERNAL TCS AXISBANK BAJFINANCE M&M LT KOTAKBANK ITC TATASTEEL DIXON".split())
rows = []
for f in sorted(glob.glob(str(ROOT / "data/angel/stock_5m/*.csv.gz"))):
    s = os.path.basename(f)[:-7]; a = pd.read_csv(f)
    if len(a) < 5000: continue
    ts = pd.to_datetime(a.timestamp.str[:19]); a["date"] = ts.dt.normalize(); a["t"] = ts.dt.hour * 60 + ts.dt.minute
    a = a[(a.t >= 555) & (a.t <= 925) & (a.date >= "2025-01-01")]
    g = a.groupby("date")
    d = pd.DataFrame({"o": g.open.first(), "t0": g.t.first(), "h0": g.high.first(), "l0": g.low.first(), "v0": g.volume.first(), "vday": g.volume.sum()})
    for nm, tt in (("c5", 555), ("c15", 565), ("cl", 925)): d[nm] = a[a.t == tt].set_index("date").close
    d = d[d.t0 == 555]; d["prev"] = d.cl.shift(1); d["sym"] = s
    d["tier"] = "A most-liquid" if len(pd.read_csv(f, usecols=[0])) > 60000 else "B less-liquid"
    rows.append(d.reset_index())
j = pd.concat(rows).dropna(subset=["prev", "c5", "cl"]).reset_index(drop=True)
print(j.groupby("tier").sym.nunique().to_dict())
j["gap"] = j.o / j.prev - 1
j["r5"] = (j.c5 / j.o - 1) * 1e4; j["r5_15"] = (j.c15 / j.c5 - 1) * 1e4; j["rest"] = (j.cl / j.c5 - 1) * 1e4
for c in ("r5", "r5_15", "rest"): j[c + "x"] = j[c] - j.groupby(["tier", "date"])[c].transform("mean")
j["era"] = np.where(j.date < "2025-12-08", "2025 (before F&O pre-open)", "Dec-2025..Nov-2026 (after)")
j["bucket"] = pd.cut(j.gap * 1e4, [-1e4, -150, -75, -40, 40, 75, 150, 1e4], labels=["<-150", "-150..-75", "-75..-40", "flat", "40..75", "75..150", ">150"])
pd.set_option("display.width", 200)
for tier, x in j.groupby("tier"):
    print(f"\n=== {tier}: first-bar range median {((x.h0/x.l0-1)*1e4).median():.0f}bp; first 5 min = {(x.v0/x.vday).median():.1%} of day volume")
    t = x.pivot_table(index="bucket", columns="era", values="r5x", aggfunc=["mean", "count"], observed=True).round(1)
    print("market-adjusted return 09:15 open -> 09:20 (bp):"); print(t.to_string())
    for era, y in x.groupby("era"):
        up, dn = y[y.gap > 0.0075], y[y.gap < -0.0075]
        fade = (dn.r5x.mean() - up.r5x.mean()) / 2
        days = y.date.nunique(); n = len(up) + len(dn)
        se = np.sqrt(up.r5x.var() / max(len(up), 1) + dn.r5x.var() / max(len(dn), 1)) / 2
        print(f"  {era}: fade of |gap|>0.75% = {fade:+.1f}bp per unit (t {fade/se:+.1f}), {n} events over {days} days = {n/days:.1f}/day; after 09:20 the same names move {(dn.restx.mean()-up.restx.mean())/2:+.1f}bp to close")
