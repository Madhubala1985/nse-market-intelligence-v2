"""EXPLORATORY: A1 portfolio construction. Variants are chosen on the DESIGN window (2019-2024) and then all
reported once on the post-reform window (2025-12-08 ->). NSE daily data, less-liquid half of F&O stocks, open->close."""
import numpy as np, pandas as pd
from engine import load_panels
W = load_panels(); ok = (W["uni"] & ~W["fixed"]).loc["2019":]
on = W["on"].loc["2019":].where(ok).clip(-.3, .3); intra = W["intra"].loc["2019":].where(ok).clip(-.3, .3)
liq = W["val"].rolling(60, min_periods=20).median().shift(1).loc["2019":].where(ok); lr = liq.rank(axis=1, pct=True)
g = on.where(lr <= .5); r = intra.where(g.notna())
dm = g.sub(g.mean(axis=1), axis=0); sd = g.std(axis=1); rk = g.rank(axis=1, pct=True)
def norm(w): return w.div(w.abs().sum(axis=1), axis=0)
V = {
    "V0 quintile, equal weight": norm(((rk <= .2).astype(float) - (rk > .8).astype(float)).where(g.notna())),
    "V3 decile, equal weight": norm(((rk <= .1).astype(float) - (rk > .9).astype(float)).where(g.notna())),
    "V1 all names, weight ∝ −demeaned gap": norm(-dm),
    "V2 |demeaned gap| > 1 sd, equal weight": norm((-np.sign(dm)).where(dm.abs().gt(sd, axis=0))),
    "V4 |demeaned gap| > 1 sd, weight ∝ gap": norm((-dm).where(dm.abs().gt(sd, axis=0))),
    "V5 |demeaned gap| > 2 sd, equal weight": norm((-np.sign(dm)).where(dm.abs().gt(2 * sd, axis=0))),
}
print(f"{'variant':42s} {'DESIGN 2019-24 net':>19s} {'t':>6s} | {'2025 pre':>9s} | {'AFTER net':>10s} {'t':>5s} {'win':>4s} {'mo+':>6s} {'worst':>6s} {'names':>6s} | {'since Sep-7':>11s} | {'AFTER @12bp':>11s}")
for nm, w in V.items():
    p = (w * r).sum(axis=1, min_count=1).dropna() * 1e4
    net = p - 8
    a, b, c, e = net["2019":"2024"], net["2025-01-01":"2025-12-07"], net["2025-12-08":], net["2026-09-07":]
    m = c.groupby([c.index.year, c.index.month]).sum()
    print(f"{nm:42s} {a.mean():+19.1f} {a.mean()/a.std()*np.sqrt(len(a)):+6.1f} | {b.mean():+9.1f} | {c.mean():+10.1f} {c.mean()/c.std()*np.sqrt(len(c)):+5.1f} {(c>0).mean():4.0%} {int((m>0).sum()):3d}/{len(m):<2d} {c.min():6.0f} {int(w['2025-12-08':].notna().mul(w['2025-12-08':].ne(0)).sum(axis=1).mean()):6d} | {e.mean():+11.1f} | {c.mean()-4:+11.1f}")
