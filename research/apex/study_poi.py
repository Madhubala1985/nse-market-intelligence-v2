"""H15 / H16: participant-wise index-futures positioning vs next-5-day NIFTY."""
import glob, io, numpy as np, pandas as pd
from engine import report, FUT_SIDE, D, ROOT
rows = []
for f in sorted(glob.glob(str(ROOT / "data/nse_archive/poi/*.csv"))):
    lines = [l.split(",") for l in open(f, errors="ignore").read().splitlines()]
    hi = next((i for i, l in enumerate(lines) if l and l[0].strip().lower().startswith("client type")), None)
    if hi is None: continue
    hdr = [c.strip() for c in lines[hi]]
    try:
        il, ish = hdr.index("Future Index Long"), hdr.index("Future Index Short")
        t = {l[0].strip().upper(): (float(l[il]), float(l[ish])) for l in lines[hi + 1:] if len(l) > ish and l[0].strip()}
        rows.append({"date": pd.Timestamp(f[-12:-4]), **{k: t[k.upper()][0] - t[k.upper()][1] for k in ("Client", "FII", "Pro", "DII")}, "tot": t["TOTAL"][0]})
    except Exception as e:
        pass
p = pd.DataFrame(rows).set_index("date")
fut = pd.read_pickle(D / "fut.pkl")
nf = fut[(fut.symbol == "NIFTY") & (fut.inst == "FUTIDX") & (fut.expiry >= fut.date)].sort_values(["expiry", "date"])
nf["px"] = nf.settle.where(nf.settle > 0, nf.close); nf["r"] = nf.groupby("expiry").px.pct_change()
nf["rank"] = nf.groupby("date").expiry.rank(method="first")
near = nf[nf["rank"] == 1].set_index("date"); nxt = nf[nf["rank"] == 2].set_index("date")
roll = ((near.expiry - near.index).dt.days <= 0).shift(1, fill_value=False)
r = near.r.where(~roll, nxt.r.reindex(near.index)).fillna(near.r)
p = p.reindex(r.index)
print("coverage", p.FII.notna().sum(), p.index[p.FII.notna()][0].date())
def run(sig, mult=1.0):
    pos = np.sign(sig).shift(2).fillna(0)          # known evening of t -> enter close t+1 -> earns from t+2
    return pos * r - FUT_SIDE * mult * (pos - pos.shift(1)).abs().fillna(0), pos
def weekly(sig):                                   # act only every 5th day, hold 5 days
    s = sig.copy(); keep = np.arange(len(s)) % 5 == 0
    return s.where(keep).ffill(limit=4)
frac = p.div(p.tot, axis=0)                        # net as share of total index-futures OI
h15 = lambda lb: weekly(frac.FII - frac.FII.shift(lb))
n, pos = run(h15(5)); n2, _ = run(h15(5), 2.0)
start = p.FII.first_valid_index()
print("H15 gross ann", f"{(pos*r)[start:].mean()*252:+.1%}", " corr(5d dFII, next5d ret):", round((frac.FII-frac.FII.shift(5)).corr(r.rolling(5).sum().shift(-6)), 3))
report("H15 FII net index-futures 5d change -> NIFTY 5d", n[start:], n2[start:], [run(h15(3))[0][start:].mean() * 252, run(h15(10))[0][start:].mean() * 252])
def h16(lb, zc=1.5):
    z = (frac.Client - frac.Client.rolling(lb).mean()) / frac.Client.rolling(lb).std()
    return weekly((-np.sign(z)).where(z.abs() > zc, 0.0))
n, pos = run(h16(60)); n2, _ = run(h16(60), 2.0)
print("\nH16 active days share", round((pos != 0).mean(), 2), "gross ann", f"{(pos*r)[start:].mean()*252:+.1%}")
report("H16 fade retail net index-futures extreme", n[start:], n2[start:], [run(h16(30))[0][start:].mean() * 252, run(h16(120))[0][start:].mean() * 252])
# descriptive: level relations (reported, not traded)
for k in ("FII", "Client", "Pro"):
    lv = frac[k]; f5 = r.rolling(5).sum().shift(-6)
    print(f"  level corr {k} net share vs next-5d NIFTY: {lv.corr(f5):+.3f}; 5d-change corr: {(lv-lv.shift(5)).corr(f5):+.3f}")
