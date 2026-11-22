"""Cross-sectional stock studies: H1, H2, H2b, H3, H4, H5, H6, H10, H14."""
import sys
import numpy as np, pandas as pd
from engine import load_panels, quintile_weights, simulate, report, FUT_SIDE, CASH_SIDE

W = load_panels()
ret, uni = W["ret"], W["uni"]
start = uni.any(axis=1).idxmax()
ret = ret.loc[ret.index >= start - pd.Timedelta(days=420)]
uni = uni.loc[ret.index]
logr = np.log1p(ret.fillna(0))
valid = ret.notna()
dates = ret.index
month_end = pd.Series(dates, index=dates).groupby([dates.year, dates.month]).last().values
week_end = pd.Series(dates, index=dates).groupby([dates.isocalendar().year.values, dates.isocalendar().week.values]).last().values
mkt = ret.where(uni).mean(axis=1)  # equal-weight F&O universe
RES = []


def cum(lb, skip=0):
    full = valid.rolling(lb).sum() >= lb * 0.9
    return (logr.rolling(lb).sum().shift(skip)).where(full.shift(skip, fill_value=False))


def ls(name, sig, rebs, long_only=False, side=FUT_SIDE, neighbours=None, daily=False, roll=True, q=0.2):
    def run(sg, mult=1.0):
        w = {t: quintile_weights(sg.loc[t][uni.loc[t]], long_only, q) for t in rebs if t in sg.index and t >= start}
        return simulate(w, ret, side, roll=roll, mult=mult)
    net, gross = run(sig)
    net2, _ = run(sig, 2.0)
    nb = [run(s)[0].mean() * 252 for s in (neighbours or [])]
    print(f"\n[{name}] gross ann {gross[gross.ne(0).cummax()].mean()*252:+.1%}")
    s = report(name, net, net2, nb, daily)
    RES.append(s)
    return net


# H1 momentum 12-1
mom = lambda lb: cum(lb - 21, 21)
n1 = ls("H1 momentum 12-1 L/S (futures)", mom(252), month_end, neighbours=[mom(126), mom(504)])
# H14 long-only top-20 momentum in cash, vs universe
def top20(sig, mult=1.0):
    w = {}
    for t in month_end:
        if t < start: continue
        s = sig.loc[t][uni.loc[t]].dropna()
        if len(s) >= 40:
            w[t] = pd.Series(1 / 20, index=s.nlargest(20).index)
    return simulate(w, ret, CASH_SIDE, roll=False, mult=mult)
n14, g14 = top20(mom(252)); n14x, _ = top20(mom(252), 2.0)
RES.append(report("H14 long-only top-20 momentum, cash (ABSOLUTE)", n14, n14x))
act = n14 - mkt.reindex(n14.index).fillna(0) * (n14.ne(0).cummax())
act2 = n14x - mkt.reindex(n14.index).fillna(0) * (n14x.ne(0).cummax())
RES.append(report("H14 same, EXCESS over equal-weight F&O universe", act, act2,
                  [(top20(mom(126))[0] - mkt).loc[start:].mean() * 252, (top20(mom(504))[0] - mkt).loc[start:].mean() * 252]))
print("universe equal-weight ann:", f"{mkt.loc[start:].mean()*252:+.1%}", "vol", f"{mkt.loc[start:].std()*252**.5:.1%}")
# H2 reversal
rev = lambda lb: -cum(lb)
ls("H2 5-day reversal L/S", rev(5), week_end, neighbours=[rev(3), rev(10)])
# H2b residual reversal
beta = ret.rolling(120, min_periods=80).cov(mkt).div(mkt.rolling(120, min_periods=80).var(), axis=0).shift(1)
resid = ret - beta.mul(mkt, axis=0)
rr = lambda lb: -resid.rolling(lb).sum().where(valid.rolling(lb).sum() >= lb)
ls("H2b 5-day residual reversal L/S", rr(5), week_end, neighbours=[rr(3), rr(10)])
# H3 time-series trend
def tsmom(lb, mult=1.0):
    sgn = np.sign(cum(lb)); vol = ret.rolling(60, min_periods=40).std() * np.sqrt(252)
    w = {}
    for t in month_end:
        if t < start: continue
        x = (sgn.loc[t] / vol.loc[t])[uni.loc[t]].replace([np.inf, -np.inf], np.nan).dropna()
        if len(x) >= 20:
            w[t] = x / x.abs().sum()  # gross 1
    return simulate(w, ret, FUT_SIDE, mult=mult)
n3, _ = tsmom(252); n3x, _ = tsmom(252, 2.0)
RES.append(report("H3 time-series trend (gross 1)", n3, n3x, [tsmom(126)[0].mean() * 252, tsmom(504)[0].mean() * 252]))
# H5 low vol
lv = lambda lb: -ret.rolling(lb, min_periods=int(lb * .9)).std()
ls("H5 low-vol minus high-vol L/S", lv(252), month_end, neighbours=[lv(126), lv(504)])
# H6 52-week high
adj = np.exp(logr.cumsum())
hi = lambda lb: (adj / adj.rolling(lb, min_periods=int(lb * .9)).max()).where(valid)
ls("H6 52-week-high proximity L/S", hi(252), month_end, neighbours=[hi(126), hi(504)])
# H4 overnight continuation: signal mean overnight ret last 21d; hold close->open daily
on, intra = W["on"].loc[dates], W["intra"].loc[dates]
def h4(lb, mult=1.0):
    sig = on.rolling(lb, min_periods=int(lb * .9)).mean()
    rk = sig.where(uni).rank(axis=1, pct=True)
    wl = (rk > 0.8).astype(float); ws = (rk < 0.2).astype(float)
    wl = wl.div(wl.sum(axis=1), axis=0); ws = ws.div(ws.sum(axis=1), axis=0)
    w = (wl - ws).shift(1)  # decided at prior close, positions opened at that close
    g = (w * on).sum(axis=1)
    return (g - 2 * 2 * FUT_SIDE * mult * (w.abs().sum(axis=1) > 0)).loc[start:], g.loc[start:]
n4, g4 = h4(21); n4x, _ = h4(21, 2.0)
print(f"\n[H4] gross ann {g4.mean()*252:+.1%} (before a daily round trip on both legs)")
RES.append(report("H4 overnight continuation L/S (close->open)", n4, n4x, [h4(10)[0].mean() * 252, h4(42)[0].mean() * 252], daily=True))
# H10 shock drift
val = W["val"].loc[dates]
sd = ret.rolling(60, min_periods=40).std().shift(1)
vmed = val.rolling(20, min_periods=15).median().shift(1)
def h10(k, hold=20, mult=1.0):
    ev = ((ret.abs() > k * sd) & (val > 3 * vmed) & uni)
    pos = (np.sign(ret).where(ev)).ffill(limit=hold).shift(1).fillna(0)  # enter next close-to-close
    n = pos.abs().sum(axis=1)
    w = pos.div(n.clip(lower=10), axis=0)  # cap: full gross only when >=10 names active
    g = (w * ret).sum(axis=1)
    turn = (w - w.shift(1)).abs().sum(axis=1)
    return (g - FUT_SIDE * mult * turn).loc[start:], g.loc[start:], ev.sum().sum()
n10, g10, nev = h10(3); n10x, _, _ = h10(3, mult=2.0)
print(f"\n[H10] events {nev}, gross ann {g10.mean()*252:+.1%}")
RES.append(report("H10 shock drift (PEAD proxy), 20d hold", n10, n10x, [h10(2.5)[0].mean() * 252, h10(4)[0].mean() * 252]))
pd.to_pickle({"RES": RES, "series": {"H1": n1, "H14": n14, "H14x": act, "H3": n3, "H4": n4, "H10": n10, "mkt": mkt}}, "/dev/null" if len(sys.argv) > 1 else str(__import__("engine").D / "res_xs.pkl"))
