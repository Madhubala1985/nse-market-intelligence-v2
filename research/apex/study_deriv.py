"""Futures / options studies: H7, H8, H9, H11, H12, H12b, H13."""
import numpy as np, pandas as pd
from engine import load_panels, quintile_weights, simulate, report, stats, FUT_SIDE, D

W = load_panels()
fut = pd.read_pickle(D / "fut.pkl")
fut = fut[fut.expiry >= fut.date].sort_values(["symbol", "expiry", "date"])
fut["px"] = fut.settle.where(fut.settle > 0, fut.close)
fut["r"] = fut.groupby(["symbol", "expiry"]).px.pct_change()
fut["rank"] = fut.groupby(["date", "symbol"]).expiry.rank(method="first")
fut["dte"] = (fut.expiry - fut.date).dt.days
RES = []

# ---------- index series (NIFTY) ----------
nf = fut[(fut.symbol == "NIFTY") & (fut.inst == "FUTIDX")]
near = nf[nf["rank"] == 1].set_index("date")
nxt = nf[nf["rank"] == 2].set_index("date")
# held contract: near until the day before expiry, then next (so no expiry-day roll gap)
use_next = near.dte <= 0
r_idx = near.r.where(~use_next.shift(1, fill_value=False), nxt.r.reindex(near.index))
r_idx = r_idx.fillna(near.r).dropna()
dates = r_idx.index

# H13 overnight vs intraday (near contract)
on = (near.open / near.px.shift(1) - 1).where(near.dte.shift(1) > 0)
intra = near.close / near.open - 1
print("\n=== H13 NIFTY futures overnight vs intraday (gross, before a daily 15bp round trip) ===")
for nm, s in (("overnight", on), ("intraday", intra)):
    s = s.dropna(); yr = s.groupby(s.index.year).sum()
    print(f"{nm:9s} ann {s.mean()*252:+.1%} t {s.mean()/s.std()*np.sqrt(len(s)):+.2f} years+ {(yr>0).sum()}/{len(yr)}  per-day {s.mean()*1e4:+.1f}bp")
RES.append(report("H13 long overnight only, net of daily round trip", (on - 2 * FUT_SIDE).dropna(), (on - 4 * FUT_SIDE).dropna(), daily=True, show_years=False))

# H7 turn of month
ds = pd.Series(dates, index=dates)
pos_in_month = ds.groupby([dates.year, dates.month]).cumcount()
from_end = ds.groupby([dates.year, dates.month]).cumcount(ascending=False)
def tom(a, b, mult=1.0):
    inwin = (from_end < a) | (pos_in_month < b)       # returns earned on these days
    g = r_idx.where(inwin, 0.0)
    entry = inwin & ~inwin.shift(1, fill_value=False)
    return g - entry * 2 * FUT_SIDE * mult, g, r_idx.where(~inwin, 0.0)
n7, g7, rest = tom(3, 3); n7x, _, _ = tom(3, 3, 2.0)
print(f"\n[H7] in-window days {int((g7!=0).sum())}: mean {g7[g7!=0].mean()*1e4:+.1f}bp/day vs other days {rest[rest!=0].mean()*1e4:+.1f}bp/day; buy&hold ann {r_idx.mean()*252:+.1%}")
RES.append(report("H7 turn-of-month NIFTY (-3..+3)", n7, n7x, [tom(2, 2)[0].mean() * 252, tom(4, 4)[0].mean() * 252]))
exc = n7 - r_idx * (6 / 21)  # vs holding the same average exposure all month
RES.append(report("H7 same, EXCESS over equal always-on exposure", exc, n7x - r_idx * (6 / 21), show_years=False))

# ---------- stock futures panels ----------
sf = fut[fut.inst == "FUTSTK"].copy()
root = W["root"]
sf["id"] = sf.symbol.map(root).fillna(sf.symbol)
n1 = sf[sf["rank"] == 1].drop_duplicates(["date", "id"]).set_index(["date", "id"])
n2 = sf[sf["rank"] == 2].drop_duplicates(["date", "id"]).set_index(["date", "id"])
cal = W["ret"].index
wide = lambda s: s.unstack("id").reindex(cal)
r1, r2 = wide(n1.r), wide(n2.r)
dte1 = wide(n1.dte)
held_next = (dte1 <= 0).shift(1, fill_value=False)
fret = r1.where(~held_next, r2).clip(-0.6, 1.5)       # tradeable near-month futures return
px1, px2 = wide(n1.px), wide(n2.px)
vol2 = wide(n2.vol)
cash = W["close"].reindex(index=cal, columns=px1.columns)
uni = px1.notna()
start = uni.any(axis=1).idxmax()
weeks = pd.Series(cal, index=cal).groupby([cal.isocalendar().year.values, cal.isocalendar().week.values]).last().values

def run_ls(name, sig, rebs, neighbours=(), q=0.2):
    def go(sg, mult=1.0):
        w = {t: quintile_weights(sg.loc[t][uni.loc[t]], q=q) for t in rebs if t >= start}
        return simulate(w, fret, FUT_SIDE, mult=mult)
    net, gross = go(sig); net2, _ = go(sig, 2.0)
    print(f"\n[{name}] gross ann {gross[gross.ne(0).cummax()].mean()*252:+.1%}")
    RES.append(report(name, net, net2, [go(s)[0].mean() * 252 for s in neighbours]))
    return net

# H8 carry: annualised basis of the contract we would hold (near if dte>=5 else next)
dte2 = wide(n2.dte)
b1 = (px1 / cash - 1) * 365 / dte1.where(dte1 >= 5)
b2 = (px2 / cash - 1) * 365 / dte2
basis = b1.fillna(b2).clip(-1, 1)
print("\nbasis sanity: median annualised", f"{basis.stack().median():+.1%}", "IQR", basis.stack().quantile([.25, .75]).round(3).tolist())
run_ls("H8 carry: long cheap basis, short rich basis", -basis, weeks,
       neighbours=[-basis.rolling(3).mean(), -basis.rolling(10).mean()])

# H9 OI build-up lore
oi = sf.groupby(["date", "id"]).oi.sum().unstack("id").reindex(cal)
def h9(lb, mult=1.0):
    r5 = np.log1p(fret.fillna(0)).rolling(lb).sum(); d_oi = oi / oi.shift(lb) - 1
    w = {}
    for t in weeks:
        if t < start: continue
        x = np.sign(r5.loc[t]).where(d_oi.loc[t] > 0)[uni.loc[t]].dropna()
        x = x[x != 0]
        if len(x) >= 10:
            w[t] = x / len(x)
    return simulate(w, fret, FUT_SIDE, mult=mult)
n9, g9 = h9(5); n9x, _ = h9(5, 2.0)
print(f"\n[H9] gross ann {g9[g9.ne(0).cummax()].mean()*252:+.1%}")
RES.append(report("H9 OI build-up continuation (lore)", n9, n9x, [h9(3)[0].mean() * 252, h9(10)[0].mean() * 252]))

# H11 calendar-spread reversion (only where the next month actually traded)
spr = (px2 / px1 - 1).where((vol2 > 0) & (dte1 >= 6))
z = (spr - spr.rolling(20, min_periods=15).mean()) / spr.rolling(20, min_periods=15).std()
def h11(zc, hold=5, mult=1.0):
    sig = (-np.sign(z)).where(z.abs() > zc)                 # +1 = long spread (long next, short near)
    pos = sig.ffill(limit=hold - 1).shift(1).fillna(0)
    pnl_each = pos * (r2 - r1)
    n = pos.abs().sum(axis=1)
    w = pos.div(n.clip(lower=10), axis=0)
    g = (w * (r2 - r1)).sum(axis=1)
    turn = (w - w.shift(1)).abs().sum(axis=1)
    return (g - 2 * FUT_SIDE * mult * turn).loc[start:], g.loc[start:], int(sig.notna().sum().sum())
n11, g11, ne = h11(2); n11x, _, _ = h11(2, mult=2.0)
print(f"\n[H11] signals {ne}, spread daily sd {spr.diff().stack().std()*1e4:.1f}bp, gross ann {g11.mean()*252:+.2%}")
RES.append(report("H11 calendar-spread reversion", n11, n11x, [h11(1.5)[0].mean() * 252, h11(2.5)[0].mean() * 252]))

# ---------- H12 / H12b index variance premium ----------
op = pd.read_pickle(D / "idxopt.pkl")
op = op[(op.symbol == "NIFTY") & (op.expiry >= op.date)].copy()
op["px"] = op.close.where((op.close > 0) & (op.vol > 0), np.nan)
op["dte"] = (op.expiry - op.date).dt.days
pv = op.pivot_table(index=["date", "expiry", "strike"], columns="cp", values="px", aggfunc="first").dropna()
pv["strad"] = pv.CE + pv.PE; pv["gap"] = (pv.CE - pv.PE).abs()
days = sorted(op.date.unique())
nxt_day = dict(zip(days[:-1], days[1:]))
spot = near.px
rows = []
for d in days[:-1]:
    try: day = pv.loc[d]
    except KeyError: continue
    exps = [e for e in day.index.get_level_values(0).unique() if (e - d).days >= 2]
    if not exps: continue
    e = min(exps); ch = day.loc[e]; k = ch.gap.idxmin(); p0 = ch.strad.loc[k]
    d1 = nxt_day[d]
    try: p1 = pv.loc[(d1, e, k), "strad"]
    except KeyError:
        continue
    s = k + ch.CE.loc[k] - ch.PE.loc[k]
    cost = 0.015 * (p0 + p1) + 80 / 65.0
    rows.append((d1, (e - d).days, s, p0, p1, cost))
x = pd.DataFrame(rows, columns=["date", "dte", "spot", "p0", "p1", "cost"]).set_index("date")
x["g"] = (x.p0 - x.p1) / x.spot; x["n"] = (x.p0 - x.p1 - x.cost) / x.spot
x["n2"] = (x.p0 - x.p1 - 2 * x.cost) / x.spot
x.to_pickle(D / "h12_daily.pkl")
MARGIN = 0.18
print(f"\n[H12] {len(x)} one-day short straddles {x.index.min().date()}..{x.index.max().date()}; credit {(x.p0/x.spot).median():.2%} of spot; "
      f"gross {x.g.mean()*1e4:+.2f}bp/day of notional, cost {(x.cost/x.spot).mean()*1e4:.2f}bp, win rate {(x.n>0).mean():.1%}")
print(f"worst days (% of notional): {(x.n.nsmallest(6)*100).round(2).to_dict()}")
print(f"as % of ~18% margin: mean/day {x.n.mean()/MARGIN:+.3%}, worst day {x.n.min()/MARGIN:+.1%}, 1% quantile {x.n.quantile(.01)/MARGIN:+.1%}")
RES.append(report("H12 daily 1-day short ATM NIFTY straddle (return on 18% margin)", x.n / MARGIN, x.n2 / MARGIN, daily=True))
for lo, hi in ((2, 3), (4, 7), (8, 40)):
    s = x[(x.dte >= lo) & (x.dte <= hi)]
    print(f"  DTE {lo}-{hi}: n {len(s)}, net {s.n.mean()*1e4:+.2f}bp/day, win {(s.n>0).mean():.0%}, worst {s.n.min():.2%}")

# H12b: day after each monthly expiry sell next monthly ATM straddle, hold to expiry
mexp = sorted(nf.groupby([nf.expiry.dt.year, nf.expiry.dt.month]).expiry.min().unique())
rows = []
for e0, e1 in zip(mexp[:-1], mexp[1:]):
    cand = [d for d in days if d > e0]
    if not cand or e1 not in spot.index: continue
    d = cand[0]
    try: ch = pv.loc[(d, e1)]
    except KeyError: continue
    k = ch.gap.idxmin(); p0 = ch.strad.loc[k]; ST = spot.loc[e1]
    s = k + ch.CE.loc[k] - ch.PE.loc[k]
    cost = 0.015 * p0 + 80 / 65.0  # expiry leg settles, no exit spread
    rows.append((e1, s, p0, abs(ST - k), cost))
m = pd.DataFrame(rows, columns=["date", "spot", "p0", "pay", "cost"]).set_index("date")
m["n"] = (m.p0 - m.pay - m.cost) / m.spot
print(f"\n=== H12b monthly ATM straddle held to expiry: n {len(m)} ===")
tt = m.n.mean() / m.n.std() * np.sqrt(len(m)); yr = m.n.groupby(m.index.year).sum()
print(f"credit {(m.p0/m.spot).mean():.2%} of spot, mean net {m.n.mean():+.3%}/month of notional (={m.n.mean()/MARGIN:+.2%} on margin), t {tt:+.2f}, win {(m.n>0).mean():.0%}, worst {m.n.min():.2%} (= {m.n.min()/MARGIN:.0%} of margin)")
print(f"years+ {(yr>0).sum()}/{len(yr)}; halves {m.n.iloc[:len(m)//2].mean():+.3%}/{m.n.iloc[len(m)//2:].mean():+.3%}; holdout {m.n[m.index>='2024'].mean():+.3%}; by year {(yr*100).round(1).to_dict()}")
pd.to_pickle({"RES": RES, "h12": x, "h12b": m}, D / "res_deriv.pkl")
