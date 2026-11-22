"""A1 (EXPLORATORY, found during the sweep): opening-auction fade.
Each day rank F&O stocks by overnight gap (auction open / previous close). Long the bottom decile, short the top
decile AT THE AUCTION PRICE, exit same day. Daily data uses open->close; 5-min data shows the whole move is 09:15-09:20.
Cost: cash intraday round trip 6bp per unit gross (STT 2.5 + exchange/stamp/GST 1 + exit slippage 2 + brokerage 0.5); stress 12bp."""
import numpy as np, pandas as pd
from engine import load_panels, report
W = load_panels()
uni = W["uni"]; start = uni.any(axis=1).idxmax()
ok = uni & ~W["fixed"]
on = W["on"].where(ok).loc[start:].clip(-0.3, 0.3); intra = W["intra"].where(ok).loc[start:].clip(-0.3, 0.3)
val = W["val"].loc[start:]
liq = val.rolling(60, min_periods=20).median().shift(1).where(ok)
liq_rk = liq.rank(axis=1, pct=True)
def run(lo=.1, hi=.9, sub=None, cost=6e-4):
    o = on if sub is None else on.where(sub)
    rk = o.rank(axis=1, pct=True)
    L = intra.where(rk <= lo).mean(axis=1); S = intra.where(rk > hi).mean(axis=1)
    g = ((L - S) / 2).dropna()
    return g - cost, g, (L - intra.where(o.notna()).mean(axis=1)).dropna(), (intra.where(o.notna()).mean(axis=1) - S).dropna()
n, g, Lx, Sx = run(); n2, _, _, _ = run(cost=12e-4)
yr = lambda s: (s.groupby(s.index.year).mean() * 1e4).round(1).to_dict()
print("gross bp/day per unit gross by year:", yr(g))
print("long-leg excess (gap-down names vs universe):", yr(Lx)); print("short-leg excess (universe vs gap-up names):", yr(Sx))
report("A1 opening-auction fade, deciles, all F&O stocks (per unit gross, unlevered)", n, n2, [run(.05, .95)[0].mean() * 252, run(.2, .8)[0].mean() * 252], daily=True)
r13 = n["2013":]; report("A1 same, 2013 onward only (pre-open auction covers all stocks)", r13, n2["2013":], daily=True, show_years=False)
for lab, m in (("most liquid third", liq_rk > 2 / 3), ("middle third", (liq_rk > 1 / 3) & (liq_rk <= 2 / 3)), ("least liquid third", liq_rk <= 1 / 3)):
    nn, gg, _, _ = run(sub=m)
    print(f"  {lab:18s} gross by year:", {k: v for k, v in yr(gg).items() if k >= 2019}, f" | 2026 net {nn['2026':].mean()*1e4:+.1f}bp/day")
# monthly 2026 for all
x = g["2025-10":]; print("monthly gross bp 2025-10..:", (x.groupby([x.index.year, x.index.month]).mean() * 1e4).round(0).astype(int).to_dict())
# magnitude vs gap size 2026
rk = on.rank(axis=1, pct=True)
for lab, sl in (("2019-2025", slice("2019", "2025")), ("2026", slice("2026", None))):
    print(lab, "mean gap of top/bottom decile (bp):", round(on.where(rk > .9).loc[sl].stack().mean() * 1e4), round(on.where(rk <= .1).loc[sl].stack().mean() * 1e4),
          " fade as share of gap:", round(-intra.where(rk > .9).loc[sl].stack().mean() / on.where(rk > .9).loc[sl].stack().mean(), 2))
pd.to_pickle({"net": n, "gross": g}, str(__import__("engine").D / "res_auction.pkl"))
