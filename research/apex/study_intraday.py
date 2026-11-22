"""I1 / I3 / I4: intraday index momentum on 1-minute data (Angel), 2015-2026. Index used as futures proxy."""
import sys, numpy as np, pandas as pd
from engine import report, ROOT, D
RT = 0.0015
exp_days = set(pd.read_pickle(D / "vrp_by_td.pkl")["NIFTY"].expiry.unique())
for sym in ("NIFTY", "BANKNIFTY"):
    f = ROOT / "data/angel/index_1m" / f"{sym}.csv.gz"
    if not f.exists(): continue
    a = pd.read_csv(f); ts = pd.to_datetime(a.timestamp.str[:19]); a["date"] = ts.dt.normalize(); a["t"] = ts.dt.hour * 60 + ts.dt.minute
    a = a[(a.t >= 555) & (a.t <= 929)]
    px = a.pivot(index="date", columns="t", values="close")
    op = a[a.t == 555].set_index("date").open
    px = px[(px.notna().sum(axis=1) > 300)]
    last = px.ffill(axis=1).iloc[:, -1]
    prev = last.shift(1)
    P = lambda t: px[t]
    print(f"\n######## {sym}: {len(px)} sessions {px.index.min().date()}..{px.index.max().date()}")
    r_open30 = P(584) / prev - 1; r_last30 = P(924) / P(899) - 1
    r_am = P(779) / op.reindex(px.index) - 1; r_pm = P(924) / P(779) - 1
    for nm, sig, fwd in (("I1 first-30m (from prev close) -> last 25m", r_open30, r_last30), ("I3 morning (open->13:00) -> afternoon", r_am, r_pm)):
        d = pd.concat([sig, fwd], axis=1).dropna(); d.columns = ["s", "f"]
        g = np.sign(d.s) * d.f
        print(f"{nm}: corr {d.s.corr(d.f):+.3f}, hit rate {(g>0).mean():.1%}, gross {g.mean()*1e4:+.2f}bp/trade (t {g.mean()/g.std()*np.sqrt(len(g)):+.2f}), |fwd move| mean {d.f.abs().mean()*1e4:.1f}bp vs cost 15bp")
        print("   gross bp by year:", (g.groupby(g.index.year).mean() * 1e4).round(1).to_dict())
        report(nm + " NET", g - RT, g - 2 * RT, daily=True, show_years=False)
        ex = g[g.index.isin(exp_days)]
        if len(ex) > 100:
            print(f"   I4 expiry days only: n {len(ex)} gross {ex.mean()*1e4:+.2f}bp (t {ex.mean()/ex.std()*np.sqrt(len(ex)):+.2f}) hit {(ex>0).mean():.1%}; non-expiry {g[~g.index.isin(exp_days)].mean()*1e4:+.2f}bp")
        big = d.s.abs() > d.s.abs().rolling(250, min_periods=100).quantile(0.8).shift(1)
        gb = g[big]; print(f"   (descriptive) top-20% strongest signals: n {len(gb)} gross {gb.mean()*1e4:+.2f}bp (t {gb.mean()/gb.std()*np.sqrt(len(gb)):+.2f})")
