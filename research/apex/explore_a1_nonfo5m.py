"""EXPLORATORY: is the non-F&O auction fade real or bid-ask bounce? Random sample of non-F&O stocks, 5-min bars since 2025-12."""
import glob, os, json, numpy as np, pandas as pd
from engine import ROOT
tier = {v["name"]: v["tier"] for v in json.loads((ROOT / "data/angel/shadow_universe.json").read_text()).values()}
rows, roll = [], {}
for f in sorted(glob.glob(str(ROOT / "data/angel/stock_5m_nonfo/*.csv.gz"))):
    s = os.path.basename(f)[:-7]; a = pd.read_csv(f)
    if len(a) < 3000: continue
    ts = pd.to_datetime(a.timestamp.str[:19]); a["date"] = ts.dt.normalize(); a["t"] = ts.dt.hour * 60 + ts.dt.minute
    a = a[(a.t >= 555) & (a.t <= 925)]
    mid = a[(a.t >= 600) & (a.t <= 900)].copy(); mid["r"] = mid.groupby("date").close.pct_change()
    cov = (mid.r * mid.groupby("date").r.shift(1)).mean()
    roll[s] = 2 * np.sqrt(-cov) * 1e4 if cov < 0 else 0.0          # Roll effective-spread estimate, bp
    g = a.groupby("date"); d = pd.DataFrame({"o5": g.open.first(), "t0": g.t.first(), "h0": g.high.first(), "l0": g.low.first(), "v0": g.volume.first(), "vd": g.volume.sum()})
    for nm, tt in (("c5", 555), ("c10", 560), ("c15", 565), ("c30", 580), ("c60", 610), ("cl", 925)): d[nm] = a[a.t == tt].set_index("date").close
    d = d[d.t0 == 555]; d["pc"] = d.cl.shift(1); d["sym"] = s; d["tier"] = tier.get(s, "?")
    d["turn0"] = d.v0 * d.o5
    rows.append(d.reset_index())
j = pd.concat(rows).dropna(subset=["pc", "c5", "cl"])
j["o"] = j.o5                                   # first print of the 09:15 bar (auction price when the auction matched)
j["gap"] = j.o / j.pc - 1
j = j[j.gap.abs() < 0.15]
print("stocks", j.sym.nunique(), j.groupby("tier").sym.nunique().to_dict(), "days", j.date.nunique(), j.date.min().date(), "..", j.date.max().date())
print(f"Roll effective spread (bp): median {np.median(list(roll.values())):.1f}, 75th pct {np.percentile(list(roll.values()), 75):.1f}; first-bar range median {((j.h0/j.l0-1)*1e4).median():.0f}bp; first 5 min turnover median Rs {j.turn0.median()/1e5:.1f} lakh, 10th pct Rs {j.turn0.quantile(.1)/1e5:.1f} lakh")
j["rk"] = j.groupby("date").gap.rank(pct=True); j["n"] = j.groupby("date").gap.transform("size"); j = j[j.n >= 20]
print("\nhedged quintile L/S from the 09:15 first print; bp per unit gross per day")
prev = "o"
for col in ("c5", "c10", "c15", "c30", "c60", "cl"):
    r = (j[col] / j.o - 1) * 1e4
    L = r[j.rk <= .2].groupby(j.date[j.rk <= .2]).mean(); S = r[j.rk > .8].groupby(j.date[j.rk > .8]).mean(); ls = ((L - S) / 2).dropna()
    seg = (j[col] / j[prev] - 1) * 1e4
    Ls = seg[j.rk <= .2].groupby(j.date[j.rk <= .2]).mean(); Ss = seg[j.rk > .8].groupby(j.date[j.rk > .8]).mean(); inc = ((Ls - Ss) / 2).dropna()
    m = (ls - 15).groupby([ls.index.year, ls.index.month]).sum()
    print(f"  open->{col:3s}: gross {ls.mean():+6.1f} (t {ls.mean()/ls.std()*np.sqrt(len(ls)):+5.1f}) sd {ls.std():3.0f} win@15bp {(ls>15).mean():.0%} months+@15bp {int((m>0).sum())}/{len(m)} | this segment alone ({prev}->{col}) {inc.mean():+6.1f} (t {inc.mean()/inc.std()*np.sqrt(len(inc)):+4.1f})")
    prev = col
legs = j[(j.rk <= .2) | (j.rk > .8)]
print(f"\nlegs: mean |gap| {legs.gap.abs().mean()*1e4:.0f}bp; mean Roll spread of leg names {legs.sym.map(roll).mean():.1f}bp -> bounce can explain at most ~{legs.sym.map(roll).mean()/2:.0f}bp of the gross")
print("by tier (open->c15):")
for t, y in j.groupby("tier"):
    y = y.assign(rk=y.groupby("date").gap.rank(pct=True)); r = (y.c15 / y.o - 1) * 1e4
    L = r[y.rk <= .2].groupby(y.date[y.rk <= .2]).mean(); S = r[y.rk > .8].groupby(y.date[y.rk > .8]).mean(); ls = ((L - S) / 2).dropna()
    print(f"  {t}: {y.sym.nunique()} stocks, gross {ls.mean():+.1f} (t {ls.mean()/ls.std()*np.sqrt(len(ls)):+.1f}), Roll spread {np.mean([roll[s] for s in y.sym.unique()]):.1f}bp")
