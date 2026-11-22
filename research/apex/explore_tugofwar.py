"""EXPLORATORY: intraday fade of overnight-strong stocks, CASH (open = pre-open auction price).
Design window <= 2023; 2024-2026 is looked at once, after the spec is frozen."""
import numpy as np, pandas as pd
from engine import load_panels, HOLDOUT
W = load_panels()
uni = W["uni"]; start = uni.any(axis=1).idxmax()
on = W["on"].where(uni).loc[start:].clip(-0.3, 0.3); intra = W["intra"].where(uni).loc[start:].clip(-0.3, 0.3)
on = on.where(~W["fixed"].loc[start:])            # drop corporate-action days from signal and gap
sig = on.rolling(21, min_periods=15).mean().shift(1)
rk = sig.rank(axis=1, pct=True)
gap_rk = on.rank(axis=1, pct=True)
mkt_i = intra.mean(axis=1)
des = intra.index < HOLDOUT
def line(lab, m, rows=None):
    r = intra.where(m).mean(axis=1); a = (intra.sub(mkt_i, axis=0)).where(m).mean(axis=1)
    for nm, sel in (("design<=2023", des), ("holdout 24-26", ~des)):
        x, y = r[sel].dropna(), a[sel].dropna()
        if len(x) < 50: continue
        print(f"{lab:34s} {nm:13s} n_days {len(x):4d} names/day {m[sel].sum(axis=1).mean():5.1f}  intraday {x.mean()*1e4:+7.2f}bp (t {x.mean()/x.std()*np.sqrt(len(x)):+5.1f})  vs-universe {y.mean()*1e4:+7.2f}bp (t {y.mean()/y.std()*np.sqrt(len(y)):+5.1f})")
print("universe intraday mean bp:", round(mkt_i[des].mean()*1e4, 2), "/", round(mkt_i[~des].mean()*1e4, 2))
line("A top-decile overnight signal", rk > .9)
line("B top-5% overnight signal", rk > .95)
line("C today's gap top decile (any sig)", gap_rk > .9)
line("D sig top-20% AND gap top-20%", (rk > .8) & (gap_rk > .8))
line("E sig top-10% AND gap top-10%", (rk > .9) & (gap_rk > .9))
line("F gap bottom decile (any sig)", gap_rk < .1)
line("G sig bottom-10% AND gap bottom-10%", (rk < .1) & (gap_rk < .1))
for lo, hi in ((0.02, 0.04), (0.04, 0.08), (0.08, 0.3)):
    line(f"H absolute gap +{lo:.0%}..+{hi:.0%}", (on > lo) & (on <= hi))
    line(f"I absolute gap -{hi:.0%}..-{lo:.0%}", (on < -lo) & (on >= -hi))
pd.to_pickle({"rk": rk, "gap_rk": gap_rk, "intra": intra, "on": on, "mkt_i": mkt_i}, "data/apex/tow.pkl")
