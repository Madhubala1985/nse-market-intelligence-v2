"""Download NSE public end-of-day archives (F&O and cash bhavcopy), resumable.

  python scripts/fetch_nse_bhavcopy.py fo|cm [START=2010-01-01]
Raw zips land in data/nse_archive/<fo|cm>/<YYYYMMDD>.zip. Non-trading days
return 404 and are recorded in _missing.txt so they are not retried.
"""
import datetime as dt, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
      "Referer": "https://www.nseindia.com/"}
BASE = "https://nsearchives.nseindia.com/content"
SWITCH = dt.date(2024, 7, 8)  # first day of the new UDiFF format


def url(kind: str, d: dt.date) -> str:
    if d >= SWITCH:
        seg = "fo" if kind == "fo" else "cm"
        return f"{BASE}/{seg}/BhavCopy_NSE_{seg.upper()}_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"
    mon = d.strftime("%b").upper()
    if kind == "fo":
        return f"{BASE}/historical/DERIVATIVES/{d.year}/{mon}/fo{d:%d}{mon}{d.year}bhav.csv.zip"
    return f"{BASE}/historical/EQUITIES/{d.year}/{mon}/cm{d:%d}{mon}{d.year}bhav.csv.zip"


def fetch(kind: str, d: dt.date, out: Path) -> str:
    path = out / f"{d:%Y%m%d}.zip"
    if path.exists():
        return "have"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url(kind, d), headers=UA)
            data = urllib.request.urlopen(req, timeout=40).read()
            if data[:2] != b"PK":
                return "missing"
            path.write_bytes(data)
            return "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return "missing"
            time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(2 * (attempt + 1))
    return "error"


def main() -> None:
    kind = sys.argv[1]
    start = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date(2010, 1, 1)
    out = ROOT / "data" / "nse_archive" / kind
    out.mkdir(parents=True, exist_ok=True)
    miss_file = out / "_missing.txt"
    missing = set(miss_file.read_text().split()) if miss_file.exists() else set()
    days = []
    d = start
    while d <= dt.date.today():
        if d.weekday() < 5 and d.isoformat() not in missing:
            days.append(d)
        d += dt.timedelta(days=1)
    counts = {}
    with ThreadPoolExecutor(6) as ex:
        for day, res in zip(days, ex.map(lambda x: fetch(kind, x, out), days)):
            counts[res] = counts.get(res, 0) + 1
            if res == "missing" and (dt.date.today() - day).days > 5:
                missing.add(day.isoformat())
    miss_file.write_text("\n".join(sorted(missing)))
    print(kind, counts, flush=True)


if __name__ == "__main__":
    main()
