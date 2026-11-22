"""T1 momentum + trend filter, T2 dual momentum (long-only, small-capital feasible)."""
import numpy as np, pandas as pd
from engine import load_panels, simulate, report, CASH_SIDE, D
W = load_panels(); ret, uni = W["ret"], W["uni"]
start = uni.any(axis=1).idxmax()
ret = ret.loc[ret.index >= start - pd.Timedelta(days=420)]; uni = uni.loc[ret.index]
logr = np.log1p(ret.fillna(0)); valid = ret.notna(); dates = ret.index
mend = pd.Series(dates, index=dates).groupby([dates.year, dates.month]).last().values
mom = logr.rolling(231).sum().shift(21).where((valid.rolling(231).sum() >= 208).shift(21, fill_value=False))
fut = pd.read_pickle(D / "fut.pkl")
nf = fut[(fut.symbol == "NIFTY") & (fut.inst == "FUTIDX") & (fut.expiry >= fut.date)].sort_values(["expiry", "date"])
nf["px"] = nf.settle.where(nf.settle > 0, nf.close); nf["r"] = nf.groupby("expiry").px.pct_change()
nf["rank"] = nf.groupby("date").expiry.rank(method="first")
near = nf[nf["rank"] == 1].set_index("date"); nx = nf[nf["rank"] == 2].set_index("date")
roll = ((near.expiry - near.index).dt.days <= 0).shift(1, fill_value=False)
rn = near.r.where(~roll, nx.r.reindex(near.index)).fillna(near.r).reindex(dates).fillna(0)
lvl = (1 + rn).cumprod(); up = lvl > lvl.rolling(200).mean()
nifty_spot_like = rn + 0.065 / 252   # futures return + cash yield ~ total-return index proxy
def top20(filtered, mult=1.0):
    w = {}
    for t in mend:
        if t < start: continue
        s = mom.loc[t][uni.loc[t]].dropna()
        if len(s) < 40: continue
        w[t] = pd.Series(1 / 20, index=s.nlargest(20).index) if (up.loc[t] or not filtered) else pd.Series(dtype=float)
    return simulate(w, ret, CASH_SIDE, roll=False, mult=mult)[0]
a, b = top20(False), top20(True)
report("H14 (reference) top-20 momentum, always invested", a, top20(False, 2.0), show_years=False)
report("T1 top-20 momentum + NIFTY 200-day trend filter (ABSOLUTE)", b, top20(True, 2.0))
act = (b - nifty_spot_like).loc[b.ne(0).idxmax():]
report("T1 EXCESS over buy-and-hold NIFTY (total-return proxy)", act, (top20(True, 2.0) - nifty_spot_like).loc[b.ne(0).idxmax():], show_years=False)
bh = nifty_spot_like.loc[b.ne(0).idxmax():]
print(f"buy&hold NIFTY proxy: ann {bh.mean()*252:+.1%} vol {bh.std()*252**.5:.1%} maxDD {((1+bh).cumprod()/(1+bh).cumprod().cummax()-1).min():.1%}")
print("share of months invested:", round(float(np.mean([up.loc[t] for t in mend if t >= start])), 2))

# T2 dual momentum
cm = pd.read_pickle(D / "cm.pkl"); cm["symbol"] = cm.symbol.astype(str)
e = {}
for s in ("NIFTYBEES", "GOLDBEES"):
    x = cm[cm.symbol == s].sort_values("val").drop_duplicates("date", keep="last").set_index("date").sort_index()
    r = x.close / x.prev - 1
    gap = x.open / x.prev - 1
    bad = (gap.abs() > 0.2)
    print(s, "split-like days repaired:", [str(d.date()) for d in r[bad].index])
    e[s] = r.where(~bad, x.close / x.open - 1)
E2 = pd.DataFrame(e).dropna()
l12 = np.log1p(E2).rolling(252).sum()
cash_d = 0.065 / 252
me = pd.Series(E2.index, index=E2.index).groupby([E2.index.year, E2.index.month]).last().values
def dual(lb=252, mult=1.0):
    l = np.log1p(E2).rolling(lb).sum(); hold = pd.Series(index=E2.index, dtype=object)
    for t in me:
        if pd.isna(l.loc[t]).any(): continue
        best = l.loc[t].idxmax(); hold.loc[t] = best if l.loc[t, best] > np.log1p(0.065) * lb / 252 else "CASH"
    hold = hold.ffill().shift(1)
    r = pd.Series(cash_d, index=E2.index)
    for s in E2.columns: r = r.where(hold != s, E2[s])
    sw = (hold != hold.shift(1)) & hold.notna() & hold.shift(1).notna()
    r = r - sw * 2 * CASH_SIDE * mult
    return r[hold.notna()], hold
r2, hold = dual(); r2x, _ = dual(mult=2.0)
print("\nholding share:", hold.value_counts(normalize=True).round(2).to_dict(), "switches/yr:", round(((hold != hold.shift(1)) & hold.notna()).sum() / (len(r2) / 252), 1))
report("T2 dual momentum NIFTYBEES/GOLDBEES/cash (ABSOLUTE)", r2, r2x, [dual(126)[0].mean() * 252, dual(504)[0].mean() * 252])
bench = E2.NIFTYBEES.reindex(r2.index)
report("T2 EXCESS over buy-and-hold NIFTYBEES", r2 - bench, r2x - bench, show_years=False)
for nm, s in (("NIFTYBEES b&h", bench), ("GOLDBEES b&h", E2.GOLDBEES.reindex(r2.index)), ("50/50 monthly-rebalanced", (bench + E2.GOLDBEES.reindex(r2.index)) / 2)):
    eq = (1 + s).cumprod(); print(f"{nm:26s} ann {s.mean()*252:+.1%} vol {s.std()*252**.5:.1%} Sharpe(ex 6.5%) {(s.mean()*252-0.065)/(s.std()*252**.5):+.2f} maxDD {(eq/eq.cummax()-1).min():.1%}")
eq = (1 + r2).cumprod(); print(f"{'T2':26s} ann {r2.mean()*252:+.1%} vol {r2.std()*252**.5:.1%} Sharpe(ex 6.5%) {(r2.mean()*252-0.065)/(r2.std()*252**.5):+.2f} maxDD {(eq/eq.cummax()-1).min():.1%}")
