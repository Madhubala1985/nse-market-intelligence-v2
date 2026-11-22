"""EXPLORATORY (not pre-declared): H4 overnight continuation measured on the tradeable stock FUTURES."""
import numpy as np, pandas as pd
from engine import D
fut = pd.read_pickle(D / "fut.pkl")
sf = fut[(fut.inst == "FUTSTK") & (fut.expiry > fut.date)].sort_values(["symbol", "expiry", "date"])
sf = sf[(sf.vol > 0) & (sf.open > 0) & (sf.close > 0)]
sf["pc"] = sf.groupby(["symbol", "expiry"]).close.shift(1)
sf["on"] = sf.open / sf.pc - 1
sf["intra"] = sf.close / sf.open - 1
sf["rank"] = sf.groupby(["date", "symbol"]).expiry.rank(method="first")
n = sf[sf["rank"] == 1]
on = n.pivot(index="date", columns="symbol", values="on").clip(-0.3, 0.3)
intra = n.pivot(index="date", columns="symbol", values="intra").clip(-0.3, 0.3)
print("panel", on.shape, "mean names/day", int(on.notna().sum(axis=1).mean()))
print(f"all-names overnight mean {on.stack().mean()*1e4:+.2f}bp, intraday mean {intra.stack().mean()*1e4:+.2f}bp")
for lb in (21,):
    sig = on.rolling(lb, min_periods=15).mean().shift(1)     # known at yesterday's close
    rk = sig.rank(axis=1, pct=True)
    for lab, lo, hi in (("top 20%", .8, 1.01), ("top 10%", .9, 1.01), ("top 5%", .95, 1.01), ("bottom 20%", -.01, .2), ("bottom 10%", -.01, .1), ("bottom 5%", -.01, .05)):
        m = (rk > lo) & (rk <= hi)
        o = on.where(m).mean(axis=1).dropna(); i = intra.where(m).mean(axis=1).dropna()
        yr = o.groupby(o.index.year).mean() * 1e4
        print(f"lb{lb} {lab:10s} overnight {o.mean()*1e4:+6.2f}bp/night (t {o.mean()/o.std()*np.sqrt(len(o)):+6.1f})  next intraday {i.mean()*1e4:+6.2f}bp (t {i.mean()/i.std()*np.sqrt(len(i)):+5.1f})  2024+ {o[o.index>='2024'].mean()*1e4:+.2f}  min-yr {yr.min():+.1f} max-yr {yr.max():+.1f}")
    # long top decile overnight, short bottom decile overnight: per-unit-gross edge vs cost
    L = on.where(rk > .9).mean(axis=1); S = on.where(rk <= .1).mean(axis=1)
    ls = ((L - S) / 2).dropna()
    print(f"L/S decile per unit gross: {ls.mean()*1e4:+.2f}bp per night; break-even round-trip cost = that number. Statutory-only RT ~6.5bp, with slippage ~10-15bp.")
    yr = ls.groupby(ls.index.year).mean() * 1e4
    print("by year bp/night:", yr.round(1).to_dict())
    # tug of war: intraday reversal of same names
    Li = intra.where(rk > .9).mean(axis=1); Si = intra.where(rk <= .1).mean(axis=1)
    print(f"same names intraday: top decile {Li.mean()*1e4:+.2f}bp, bottom decile {Si.mean()*1e4:+.2f}bp -> close-to-close spread {(L+Li-S-Si).mean()*1e4/2:+.2f}bp/day")
