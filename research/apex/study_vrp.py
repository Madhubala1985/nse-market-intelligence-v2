"""H12c: short ATM straddle by trading-days-to-expiry (NIFTY, BANKNIFTY), incl. hold into expiry.
Exploratory follow-up of H12's DTE split and of the earlier expiry-gradient finding (n=7). Vectorised."""
import numpy as np, pandas as pd
from engine import D
op_all = pd.read_pickle(D / "idxopt.pkl")
fut = pd.read_pickle(D / "fut.pkl")
out = {}
for sym in ("NIFTY", "BANKNIFTY"):
    op = op_all[(op_all.symbol == sym) & (op_all.expiry >= op_all.date)]
    days = np.array(sorted(op.date.unique()))
    und = op.dropna(subset=["und"]).drop_duplicates("date").set_index("date").und
    f = fut[(fut.symbol == sym) & (fut.inst == "FUTIDX") & (fut.expiry >= fut.date)].sort_values("expiry").drop_duplicates("date").set_index("date")
    final = und.reindex(days).fillna(f.settle.where(f.settle > 0, f.close).reindex(days))
    op = op.assign(px=op.close.where((op.close > 0) & (op.vol > 0))).dropna(subset=["px"])
    pv = op.pivot_table(index=["date", "expiry", "strike"], columns="cp", values="px", aggfunc="first").dropna().reset_index()
    di = pd.Series(np.arange(len(days)), index=days)
    pv["i"] = pv.date.map(di).values
    pv["ei"] = np.searchsorted(days, pv.expiry.values, side="right") - 1
    pv["td"] = pv.ei - pv.i
    pv = pv[(pv.td >= 1) & (pv.td <= 25) & (pv.i + 1 < len(days))]
    pv["strad"] = pv.CE + pv.PE; pv["gap"] = (pv.CE - pv.PE).abs()
    atm = pv.sort_values("gap").drop_duplicates(["date", "expiry"]).copy()
    atm["spot"] = atm.strike + atm.CE - atm.PE
    atm["d1"] = days[atm.i.values + 1]
    nxt = pv[["date", "expiry", "strike", "CE", "PE"]].rename(columns={"date": "d1", "CE": "CE1", "PE": "PE1"})
    x = atm.merge(nxt, on=["d1", "expiry", "strike"], how="left")
    x["ST"] = final.reindex(x.d1.values).values
    x["settle"] = x.td == 1
    x["p0"] = x.strad
    x["p1"] = np.where(x.settle, (x.ST - x.strike).abs(), x.CE1 + x.PE1)
    # wings
    for w in (2, 3, 4):
        for side, col, sgn in (("c", "CE", 1), ("p", "PE", -1)):
            tgt = x[["date", "expiry", "spot"]].assign(strike=lambda d: d.spot * (1 + sgn * w / 100)).sort_values("strike")
            m = pd.merge_asof(tgt.reset_index(), pv[["date", "expiry", "strike", col]].sort_values("strike").rename(columns={"strike": "kw"}).assign(strike=lambda d: d.kw),
                              on="strike", by=["date", "expiry"], direction="nearest").set_index("index")
            x[f"k{side}{w}"] = m.kw; x[f"{side}{w}_0"] = m[col]
            n1 = pv[["date", "expiry", "strike", col]].rename(columns={"date": "d1", "strike": f"k{side}{w}", col: f"{side}{w}_1x"})
            x = x.merge(n1, on=["d1", "expiry", f"k{side}{w}"], how="left")
            intr = np.maximum(sgn * (x.ST - x[f"k{side}{w}"]), 0)
            x[f"{side}{w}_1"] = np.where(x.settle, intr, x[f"{side}{w}_1x"])
        x[f"w{w}_0"] = x[f"c{w}_0"] + x[f"p{w}_0"]; x[f"w{w}_1"] = x[f"c{w}_1"] + x[f"p{w}_1"]
    x = x.dropna(subset=["p1"]).rename(columns={"date": "entry"}).rename(columns={"d1": "date"})
    x["g"] = (x.p0 - x.p1) / x.spot
    x["c_real"] = (0.0035 * x.p0 + np.where(x.settle, 0, 0.0020 * x.p1)) / x.spot + 0.95e-4 * np.where(x.settle, 0.5, 1)
    x["c_decl"] = (0.015 * x.p0 + np.where(x.settle, 0, 0.015 * x.p1)) / x.spot + 0.8e-4
    x["n"] = x.g - x.c_real; x["nd"] = x.g - x.c_decl
    out[sym] = x
    print(f"\n######## {sym}: {len(x)} (entry,expiry) pairs, {x.entry.min().date()}..{x.entry.max().date()}")
    print("td = trading days to expiry at entry (1 = sold the day before expiry, settled at expiry); bp of notional per 1-day hold")
    print(f"{'td':>5} {'n':>5} {'credit%':>8} {'gross':>7} {'net_real':>9} {'net_decl':>9} {'t_real':>7} {'win':>5} {'worst%':>7} {'q01%':>6} {'yrs+':>6} {'h1':>6} {'h2':>6} {'2024+':>6}")
    for lab, m in [("1", x.td == 1), ("2", x.td == 2), ("3", x.td == 3), ("4", x.td == 4), ("5", x.td == 5), ("6-10", x.td.between(6, 10)), ("11-25", x.td > 10)]:
        s_ = x[m].sort_values("date")
        if len(s_) < 30: continue
        yr = s_.groupby(s_.date.dt.year).n.sum(); h = len(s_) // 2
        print(f"{lab:>5} {len(s_):5d} {(s_.p0/s_.spot).mean()*100:8.2f} {s_.g.mean()*1e4:7.1f} {s_.n.mean()*1e4:9.1f} {s_.nd.mean()*1e4:9.1f} {s_.n.mean()/s_.n.std()*np.sqrt(len(s_)):7.2f} {(s_.n>0).mean():5.0%} {s_.n.min()*100:7.2f} {s_.n.quantile(.01)*100:6.2f} {(yr>0).sum():3d}/{len(yr):<2d} {s_.n.iloc[:h].mean()*1e4:6.1f} {s_.n.iloc[h:].mean()*1e4:6.1f} {s_[s_.date>='2024'].n.mean()*1e4:6.1f}")
pd.to_pickle(out, D / "vrp_by_td.pkl")
