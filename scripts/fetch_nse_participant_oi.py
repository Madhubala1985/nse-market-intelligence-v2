"""Download NSE participant-wise F&O open interest (Client/DII/FII/Pro), daily since 2012."""
import datetime as dt, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
OUT = Path(__file__).resolve().parents[1] / "data" / "nse_archive" / "poi"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36", "Referer": "https://www.nseindia.com/"}
def fetch(d):
    p = OUT / f"{d:%Y%m%d}.csv"
    if p.exists(): return "have"
    for a in range(3):
        try:
            data = urllib.request.urlopen(urllib.request.Request(f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{d:%d%m%Y}.csv", headers=UA), timeout=30).read()
            if b"Client" not in data: return "missing"
            p.write_bytes(data); return "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404: return "missing"
            time.sleep(2)
        except Exception: time.sleep(2)
    return "error"
OUT.mkdir(parents=True, exist_ok=True)
d, days = dt.date(2012, 1, 1), []
while d <= dt.date.today():
    if d.weekday() < 5: days.append(d)
    d += dt.timedelta(days=1)
c = {}
with ThreadPoolExecutor(4) as ex:
    for r in ex.map(fetch, days): c[r] = c.get(r, 0) + 1
print(c)
