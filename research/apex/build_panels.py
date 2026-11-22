"""Parse raw NSE bhavcopy zips into compact pandas pickles under data/apex/.

  python research/apex/build_panels.py cm   -> cm.pkl   (EQ/BE series, all symbols)
  python research/apex/build_panels.py fo   -> fut.pkl, idxopt.pkl
"""
import io, sys, zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW, OUT = ROOT / "data" / "nse_archive", ROOT / "data" / "apex"


def _read(path):
    with zipfile.ZipFile(path) as z:
        return pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), low_memory=False)


def cm_one(path):
    try:
        df = _read(path)
    except Exception as e:
        return None
    if "TckrSymb" in df.columns:
        df = df[df.SctySrs.isin(["EQ", "BE"])]
        out = pd.DataFrame({"date": pd.Timestamp(path.stem), "symbol": df.TckrSymb, "isin": df.ISIN,
                            "open": df.OpnPric, "high": df.HghPric, "low": df.LwPric, "close": df.ClsPric,
                            "prev": df.PrvsClsgPric, "vol": df.TtlTradgVol, "val": df.TtlTrfVal})
    else:
        df.columns = [c.strip() for c in df.columns]
        df = df[df.SERIES.isin(["EQ", "BE"])]
        if "ISIN" not in df.columns:
            df = df.assign(ISIN="")
        out = pd.DataFrame({"date": pd.Timestamp(path.stem), "symbol": df.SYMBOL,
                            "isin": df.ISIN, "open": df.OPEN, "high": df.HIGH, "low": df.LOW, "close": df.CLOSE,
                            "prev": df.PREVCLOSE, "vol": df.TOTTRDQTY, "val": df.TOTTRDVAL})
    return out


def fo_one(path):
    try:
        df = _read(path)
    except Exception:
        return None
    if "TckrSymb" in df.columns:
        d = pd.DataFrame({"date": pd.Timestamp(path.stem), "inst": df.FinInstrmTp, "symbol": df.TckrSymb,
                          "expiry": pd.to_datetime(df.XpryDt), "strike": df.StrkPric, "cp": df.OptnTp,
                          "open": df.OpnPric, "high": df.HghPric, "low": df.LwPric, "close": df.ClsPric,
                          "settle": df.SttlmPric, "vol": df.TtlTradgVol, "oi": df.OpnIntrst,
                          "und": df.UndrlygPric, "lot": df.NewBrdLotQty})
        d["inst"] = d.inst.map({"STF": "FUTSTK", "IDF": "FUTIDX", "IDO": "OPTIDX", "STO": "OPTSTK"})
    else:
        df.columns = [c.strip() for c in df.columns]
        d = pd.DataFrame({"date": pd.Timestamp(path.stem), "inst": df.INSTRUMENT,
                          "symbol": df.SYMBOL, "expiry": pd.to_datetime(df.EXPIRY_DT, format="mixed", dayfirst=True),
                          "strike": df.STRIKE_PR, "cp": df.OPTION_TYP, "open": df.OPEN, "high": df.HIGH,
                          "low": df.LOW, "close": df.CLOSE, "settle": df.SETTLE_PR, "vol": df.CONTRACTS,
                          "oi": df.OPEN_INT, "und": float("nan"), "lot": float("nan")})
    fut = d[d.inst.isin(["FUTSTK", "FUTIDX"])].drop(columns=["strike", "cp"])
    opt = d[(d.inst == "OPTIDX") & d.symbol.isin(["NIFTY", "BANKNIFTY"])]
    return fut, opt


def main():
    kind = sys.argv[1]
    files = sorted((RAW / kind).glob("*.zip"))
    with ProcessPoolExecutor(10) as ex:
        res = [r for r in ex.map(cm_one if kind == "cm" else fo_one, files, chunksize=20) if r is not None]
    if kind == "cm":
        df = pd.concat(res, ignore_index=True)
        df["symbol"] = df.symbol.astype("category")
        df.to_pickle(OUT / "cm.pkl")
        print("cm", df.shape, df.date.min(), df.date.max(), df.date.nunique())
    else:
        fut = pd.concat([r[0] for r in res], ignore_index=True)
        opt = pd.concat([r[1] for r in res], ignore_index=True)
        fut.to_pickle(OUT / "fut.pkl"); opt.to_pickle(OUT / "idxopt.pkl")
        print("fut", fut.shape, fut.date.min(), fut.date.max(), fut.date.nunique())
        print("opt", opt.shape)


if __name__ == "__main__":
    main()
