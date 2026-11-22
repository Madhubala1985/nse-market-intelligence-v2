"""Shared machinery for the APEX sweep: panels, portfolio simulation, gates."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data" / "apex"
HOLDOUT = pd.Timestamp("2024-01-01")
FUT_SIDE, CASH_SIDE = 0.00075, 0.0015


def load_panels():
    """Wide daily panels keyed by a rename-chained id. Returns dict of DataFrames."""
    cache = D / "wide.pkl"
    if cache.exists():
        return pd.read_pickle(cache)
    cm = pd.read_pickle(D / "cm.pkl")
    cm["symbol"] = cm.symbol.astype(str)
    cm = cm.sort_values(["date", "val"]).drop_duplicates(["date", "symbol"], keep="last")
    # chain renames: a symbol that first appears with the ISIN another symbol ended on
    first = cm.groupby("symbol").agg(d0=("date", "min"), d1=("date", "max"))
    isin_first = cm.sort_values("date").groupby("symbol").isin.first()
    isin_last = cm.sort_values("date").groupby("symbol").isin.last()
    last_by_isin = {}
    for s, i in isin_last.items():
        if isinstance(i, str) and len(i) == 12:
            last_by_isin.setdefault(i, []).append(s)
    root = {}
    for s in first.sort_values("d0").index:
        prev = [p for p in last_by_isin.get(isin_first[s], []) if p != s
                and first.d1[p] < first.d0[s] and (first.d0[s] - first.d1[p]).days <= 10]
        root[s] = root.get(prev[0], prev[0]) if prev else s
    cm["id"] = cm.symbol.map(root)
    fut = pd.read_pickle(D / "fut.pkl")
    fs = fut[fut.inst == "FUTSTK"]
    fo_ids = set(fs.symbol.map(root).fillna(fs.symbol))
    cm = cm[cm.id.isin(fo_ids)].sort_values("val").drop_duplicates(["date", "id"], keep="last")
    cm["ret"] = cm.close / cm.prev - 1
    cm["on"] = cm.open / cm.prev - 1
    cm["intra"] = cm.close / cm.open - 1
    w = {k: cm.pivot(index="date", columns="id", values=k) for k in ("ret", "on", "intra", "val", "close", "high")}
    # --- corporate-action repair: bhavcopy PREVCLOSE is NOT split/bonus adjusted (verified) ---
    raw = w["ret"].copy()
    ang_dir = ROOT / "data" / "angel" / "daily"
    n_ang = 0
    for f in sorted(ang_dir.glob("*.csv.gz")):
        cur = f.name[:-7]
        i = root.get(cur)
        if i is None or i not in raw.columns:
            continue
        a = pd.read_csv(f)
        a.index = pd.to_datetime(a.timestamp.str[:10])
        ar = a.close.pct_change().reindex(raw.index)
        bad = (ar - raw[i]).abs() > 0.02
        n_ang += int(bad.sum())
        w["ret"].loc[bad, i] = ar[bad]
    gap = w["on"]
    heur = ((gap < -0.28) | (gap > 0.45)) & (w["intra"].abs() < 0.2) & (w["ret"] == raw)
    w["ret"] = w["ret"].where(~heur, w["intra"])
    print(f"corp-action repair: {n_ang} days fixed from Angel adjusted series, {int(heur.sum().sum())} by gap rule")
    w["on"] = (1 + w["ret"]) / (1 + w["intra"]) - 1
    w["ret"] = w["ret"].clip(-0.6, 1.5)
    w["fixed"] = (w["ret"] != raw) & raw.notna()
    u = fs.assign(one=True).drop_duplicates(["date", "symbol"])
    u["id"] = u.symbol.map(root).fillna(u.symbol)
    uni = u.drop_duplicates(["date", "id"]).pivot(index="date", columns="id", values="one")
    w["uni"] = uni.reindex(index=w["ret"].index, columns=w["ret"].columns).fillna(False).astype(bool)
    w["root"] = pd.Series(root)
    pd.to_pickle(w, cache)
    return w


def quintile_weights(sig: pd.Series, long_only=False, q=0.2):
    s = sig.dropna()
    if len(s) < 20:
        return pd.Series(dtype=float)
    k = max(int(len(s) * q), 1)
    r = s.rank(method="first")
    longs, shorts = r[r > len(s) - k].index, r[r <= k].index
    w = pd.Series(0.0, index=s.index)
    w[longs] = 1.0 / k
    if not long_only:
        w[shorts] = -1.0 / k
    return w[w != 0]


def simulate(weights: dict, ret: pd.DataFrame, side_cost=FUT_SIDE, roll=True, mult=1.0):
    """weights: {rebalance_date: Series}. Weights decided at close of date t earn from t+1.
    Returns daily net and gross return Series."""
    dates = ret.index
    reb = sorted(weights)
    cur = pd.Series(dtype=float)
    gross, net, i = [], [], 0
    pending_cost = 0.0
    for t in dates:
        g = float((cur * ret.loc[t].reindex(cur.index).fillna(0)).sum()) if len(cur) else 0.0
        c = pending_cost
        pending_cost = 0.0
        if roll and len(cur):
            c += 2 * side_cost * mult * cur.abs().sum() / 21
        gross.append(g); net.append(g - c)
        if i < len(reb) and reb[i] == t:
            new = weights[t]
            allidx = cur.index.union(new.index)
            turn = (new.reindex(allidx).fillna(0) - cur.reindex(allidx).fillna(0)).abs().sum()
            pending_cost = side_cost * mult * turn
            cur = new
            i += 1
    idx = dates
    return pd.Series(net, idx), pd.Series(gross, idx)


def stats(r: pd.Series, daily_strategy=False, label=""):
    r = r.dropna()
    r = r[r.ne(0).cummax()]  # start at first active day
    if len(r) < 250:
        return {"label": label, "n_days": len(r), "PASS": False, "note": "too short"}
    m = (1 + r).groupby([r.index.year, r.index.month]).prod() - 1
    t = m.mean() / m.std(ddof=1) * np.sqrt(len(m))
    yr = (1 + r).groupby(r.index.year).prod() - 1
    full_years = yr[(r.groupby(r.index.year).size() > 120)]
    neg = (full_years <= 0).astype(int)
    run3 = (neg.rolling(3).sum() == 3).any()
    half = len(r) // 2
    h1, h2 = r.iloc[:half].mean() * 252, r.iloc[half:].mean() * 252
    if daily_strategy:
        ex = (r.sum() - r.nlargest(5).sum()) / len(r) * 252
    else:
        ex = (m.sum() - m.max()) / len(m) * 12
    ho = r[r.index >= HOLDOUT]
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    out = {
        "label": label, "ann": r.mean() * 252, "vol": r.std() * np.sqrt(252),
        "sharpe": r.mean() / r.std() * np.sqrt(252), "t": t, "maxdd": dd,
        "yrs_pos": f"{int((full_years > 0).sum())}/{len(full_years)}", "run3neg": bool(run3),
        "h1": h1, "h2": h2, "ex_best": ex, "holdout_ann": ho.mean() * 252 if len(ho) else np.nan,
        "years": yr.round(3).to_dict(),
    }
    out["g1"] = bool(r.mean() > 0 and t >= 3.0)
    out["g2"] = bool((full_years > 0).mean() >= 0.7 and not run3)
    out["g3"] = bool(h1 > 0 and h2 > 0)
    out["g4"] = bool(ex > 0)
    out["g5"] = bool(len(ho) and ho.mean() > 0)
    return out


def report(name, net, net2x, neighbours=(), daily=False, show_years=True):
    s = stats(net, daily, name)
    s2 = stats(net2x, daily)
    s["g6"] = bool(s2.get("ann", -1) > 0)
    s["g7"] = all(n > 0 for n in neighbours) if neighbours else None
    gates = [s.get(f"g{i}") for i in range(1, 8)]
    s["PASS"] = all(g for g in gates if g is not None)
    print(f"\n=== {name} ===")
    if "ann" not in s:
        print(s); return s
    print(f"net ann {s['ann']:+.1%}  vol {s['vol']:.1%}  Sharpe {s['sharpe']:+.2f}  t {s['t']:+.2f}  maxDD {s['maxdd']:.1%}")
    print(f"years+ {s['yrs_pos']}  halves {s['h1']:+.1%}/{s['h2']:+.1%}  ex-best {s['ex_best']:+.1%}  holdout {s['holdout_ann']:+.1%}  2xcost {s2.get('ann', float('nan')):+.1%}  neighbours {[round(n,3) for n in neighbours]}")
    print("gates 1-7:", ["P" if g else ("-" if g is None else "F") for g in gates], "=> PASS" if s["PASS"] else "=> FAIL")
    if show_years:
        print("by year:", {k: f"{v:+.0%}" for k, v in s["years"].items()})
    return s
