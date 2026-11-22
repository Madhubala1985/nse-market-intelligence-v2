"""Bulk, resumable history pull from Angel One SmartAPI (data only, no orders).

Writes gzip CSVs under data/angel/:
  daily/<NAME>.csv.gz        cash daily candles for every F&O underlying + indices
  fut_daily/<SYMBOL>.csv.gz  daily candles for each live stock/index future
  index_1m/<NAME>.csv.gz     1-minute index candles

Usage (run from a scratch dir: the SDK writes request logs, including the API
key, to ./logs):
  python scripts/fetch_angel_history.py daily|fut_daily|index_1m|stock_5m [--since YYYY-MM-DD]
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import sys
import time
import urllib.request
from pathlib import Path

import pyotp
from SmartApi import SmartConnect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "angel"
MASTER_URL = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"
INDICES = {
    "NIFTY": "99926000", "BANKNIFTY": "99926009", "FINNIFTY": "99926037",
    "MIDCPNIFTY": "99926074", "INDIAVIX": "99926017", "NIFTY500": "99926004",
    "NIFTYNXT50": "99926013", "NIFTYIT": "99926008", "NIFTYAUTO": "99926029",
    "NIFTYPHARMA": "99926023", "NIFTYFMCG": "99926021", "NIFTYMETAL": "99926030",
    "NIFTYPSUBANK": "99926025", "NIFTYENERGY": "99926020", "NIFTYREALTY": "99926018",
}
CHUNK_DAYS = {"ONE_DAY": 1900, "ONE_MINUTE": 28, "FIVE_MINUTE": 95}
PAUSE = 0.4


def login() -> SmartConnect:
    cfg = json.loads((ROOT / "configs" / "angelone_config.json").read_text())
    api = SmartConnect(api_key=cfg["api_key"])
    res = api.generateSession(cfg["client_code"], cfg["mpin_or_password"],
                              pyotp.TOTP(cfg["totp_secret"]).now())
    if not res.get("status"):
        raise SystemExit(f"login failed: {res.get('message')}")
    return api


def master() -> list[dict]:
    path = OUT / "scripmaster.json"
    if not path.exists() or time.time() - path.stat().st_mtime > 86400:
        OUT.mkdir(parents=True, exist_ok=True)
        path.write_bytes(urllib.request.urlopen(MASTER_URL, timeout=180).read())
    return json.loads(path.read_text())


def candles(api, exch, token, interval, start: dt.date, end: dt.date) -> list[list]:
    rows: list[list] = []
    step = dt.timedelta(days=CHUNK_DAYS[interval])
    a = start
    while a <= end:
        b = min(a + step, end)
        req = {"exchange": exch, "symboltoken": str(token), "interval": interval,
               "fromdate": f"{a} 09:00", "todate": f"{b} 23:59"}
        for attempt in range(6):
            time.sleep(PAUSE * (1 + 3 * attempt))
            try:
                res = api.getCandleData(req)
            except Exception as exc:  # network / SDK parse errors: back off, retry
                res = {"status": False, "message": repr(exc)}
            if res.get("status"):
                rows.extend(res.get("data") or [])
                break
        else:
            raise RuntimeError(f"{exch}:{token} {a}..{b}: {res.get('message')}")
        a = b + dt.timedelta(days=1)
    return rows


def save(path: Path, rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    seen, out = set(), []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            out.append(r)
    out.sort(key=lambda r: r[0])
    tmp = path.with_suffix(".tmp")
    with gzip.open(tmp, "wt", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        w.writerows(out)
    tmp.replace(path)


def run(jobs: list[tuple[Path, str, str, str, dt.date]]) -> None:
    api = login()
    today = dt.date.today()
    done = failed = 0
    for path, exch, token, interval, start in jobs:
        if path.exists():
            continue
        try:
            rows = candles(api, exch, token, interval, start, today)
            save(path, rows)
            done += 1
            print(f"ok   {path.name:32s} {len(rows):8d} rows", flush=True)
        except Exception as exc:
            failed += 1
            print(f"FAIL {path.name:32s} {exc}", flush=True)
    print(f"finished: {done} written, {failed} failed, "
          f"{len(jobs) - done - failed} already present", flush=True)


def main() -> None:
    mode = sys.argv[1]
    since = None
    if "--since" in sys.argv:
        since = dt.date.fromisoformat(sys.argv[sys.argv.index("--since") + 1])
    m = master()
    fno = sorted({r["name"] for r in m if r["exch_seg"] == "NFO" and r["instrumenttype"] == "FUTSTK"
                  and "NSETEST" not in r["name"]})
    eq = {r["name"]: r["token"] for r in m if r["exch_seg"] == "NSE" and r["symbol"].endswith("-EQ")}
    jobs = []
    if mode == "daily":
        s = since or dt.date(2002, 1, 1)
        jobs += [(OUT / "daily" / f"{n}.csv.gz", "NSE", t, "ONE_DAY", s) for n, t in INDICES.items()]
        jobs += [(OUT / "daily" / f"{n}.csv.gz", "NSE", eq[n], "ONE_DAY", s) for n in fno if n in eq]
    elif mode == "fut_daily":
        s = since or dt.date(2015, 1, 1)
        for r in m:
            if r["exch_seg"] == "NFO" and r["instrumenttype"] in ("FUTSTK", "FUTIDX"):
                jobs.append((OUT / "fut_daily" / f"{r['symbol']}.csv.gz", "NFO", r["token"], "ONE_DAY", s))
    elif mode == "index_1m":
        s = since or dt.date(2015, 1, 1)
        jobs += [(OUT / "index_1m" / f"{n}.csv.gz", "NSE", INDICES[n], "ONE_MINUTE", s)
                 for n in ("NIFTY", "BANKNIFTY", "INDIAVIX", "FINNIFTY", "MIDCPNIFTY")]
    elif mode == "stock_5m":
        s = since or dt.date(2023, 1, 1)
        order = [x for x in (OUT / "liquidity_order.txt").read_text().split()] if (OUT / "liquidity_order.txt").exists() else fno
        names = [n for n in order if n in eq and n in fno] + [n for n in fno if n in eq and n not in order]
        jobs += [(OUT / "stock_5m" / f"{n}.csv.gz", "NSE", eq[n], "FIVE_MINUTE", s) for n in names]
    elif mode == "stock_5m_list":   # names from data/angel/list_5m.txt (any NSE-EQ symbol)
        s = since or dt.date(2025, 12, 1)
        names = (OUT / "list_5m.txt").read_text().split()
        jobs += [(OUT / "stock_5m_nonfo" / f"{n}.csv.gz", "NSE", eq[n], "FIVE_MINUTE", s) for n in names if n in eq]
    elif mode == "stock_1m_list":   # same list, 1-minute bars
        s = since or (dt.date.today() - dt.timedelta(days=60))
        names = (OUT / "list_5m.txt").read_text().split()
        jobs += [(OUT / "stock_1m_nonfo" / f"{n}.csv.gz", "NSE", eq[n], "ONE_MINUTE", s) for n in names if n in eq]
    else:
        raise SystemExit(__doc__)
    run(jobs)


if __name__ == "__main__":
    main()
