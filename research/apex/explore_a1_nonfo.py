"""EXPLORATORY: does the auction fade survive outside F&O stocks (which the Dec-2025 F&O pre-open does not anchor)?
NSE cash bhavcopy, EQ series only, 2019-2026. Universe each day = the 300 most-traded NON-F&O stocks (60d median turnover),
price >= Rs 50. Corporate-action days removed by a gap rule (|gap| > 15%). Hedged quintile L/S, auction open -> close."""
import numpy as np, pandas as pd
from engine import D, load_panels
cm = pd.read_pickle(D / "cm.pkl"); cm = cm[cm.date >= "2018-09-01"]; cm["symbol"] = cm.symbol.astype(str)
W = load_panels(); root = W["root"]
fut = pd.read_pickle(D / "fut.pkl"); fo = fut[(fut.inst == "FUTSTK") & (fut.date >= "2018-09-01")][["date", "symbol"]].drop_duplicates()
fo["fo"] = True
cm = cm.merge(fo, on=["date", "symbol"], how="left"); cm["fo"] = cm.fo.fillna(False)
cm = cm.sort_values("val").drop_duplicates(["date", "symbol"], keep="last")
piv = lambda c: cm.pivot(index="date", columns="symbol", values=c)
o, c, p, v, isfo = piv("open"), piv("close"), piv("prev"), piv("val"), piv("fo").fillna(False).astype(bool)
gap = o / p - 1; intra = c / o - 1
liq = v.rolling(60, min_periods=30).median().shift(1)
ok = (~isfo) & (p >= 50) & (gap.abs() < 0.15) & liq.notna() & (intra.abs() < 0.2)
lr = liq.where(ok).rank(axis=1, ascending=False)
def run(sub, q=.2, cost=15):
    g = gap.where(sub); rk = g.rank(axis=1, pct=True)
    L = intra.where(rk <= q).mean(axis=1); S = intra.where(rk > 1 - q).mean(axis=1)
    return ((L - S) / 2 * 1e4).dropna() - cost, L * 1e4, S * 1e4
print("net of a 15bp round trip (wider spreads than F&O names); bp per unit gross per day")
for lab, sub in (("non-F&O rank 1-100 by turnover", ok & (lr <= 100)), ("non-F&O rank 101-300", ok & (lr > 100) & (lr <= 300)), ("non-F&O rank 301-600", ok & (lr > 300) & (lr <= 600))):
    n, L, S = run(sub)
    print(f"\n{lab}: median daily turnover Rs {v.where(sub).loc['2026':].stack().median()/1e7:.1f} crore")
    for era, sl in (("2019-2024", slice("2019", "2024")), ("2025 to Dec-7", slice("2025-01-01", "2025-12-07")), ("Dec-8-2025..Nov-2026", slice("2025-12-08", None)), ("since 2026-09-07", slice("2026-09-07", None))):
        x = n[sl]; m = x.groupby([x.index.year, x.index.month]).sum()
        print(f"   {era:22s} gross {x.mean()+15:+6.1f}  net {x.mean():+6.1f}  sd {x.std():4.0f}  t {x.mean()/x.std()*np.sqrt(len(x)):+5.1f}  win {(x>0).mean():.0%}  months+ {int((m>0).sum())}/{len(m)}  worst {x.min():.0f} | long leg raw {L[sl].mean():+.1f}, short leg raw {-S[sl].mean():+.1f}")
