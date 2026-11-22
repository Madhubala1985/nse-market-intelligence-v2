"""LOGS-ONLY shadow recorder for the opening-auction fade (candidate A1). Places NO orders.

Run once per trading day before 09:00 IST (e.g. cron 03:25 UTC Mon-Fri). It snapshots Angel One quotes for
every F&O stock at 09:06:30 (pre-open, indicative), 09:15:20, 09:20, 09:30 and 15:25 IST and appends them
to data/auction_shadow/<date>.jsonl, then writes a one-line daily summary to data/auction_shadow/summary.csv.

What it answers (the open questions from research/APEX_RESULTS.md), per liquidity tier:
  1. Is the gap ranking knowable at 09:06:30, before the auction closes?  (indicative_overlap)
  2. Is the fade still there on live quotes, and at bid/ask rather than last price?
  3. What would the hedged quintile rule have paid after costs?

  python scripts/auction_fade_shadow.py            # live day
  python scripts/auction_fade_shadow.py --probe    # one snapshot now, print a sample, exit (connectivity test)
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import pyotp
from SmartApi import SmartConnect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "auction_shadow"
IST = ZoneInfo("Asia/Kolkata")
SNAPS = [("pre", (9, 6, 30)), ("open", (9, 15, 20)), ("t0920", (9, 20, 0)), ("t0930", (9, 30, 0)), ("close", (15, 25, 0))]
COST = 0.0008   # round trip assumed for F&O names; non-F&O tiers need ~15 bp (see research/APEX_RESULTS.md)


def universe() -> dict[str, dict]:
    """token -> {name, tier}. Built by the 2026-11-22 research run from NSE turnover (F&O + 600 non-F&O stocks)."""
    return json.loads((ROOT / "data" / "angel" / "shadow_universe.json").read_text())


def login() -> SmartConnect:
    cfg = json.loads((ROOT / "configs" / "angelone_config.json").read_text())
    api = SmartConnect(api_key=cfg["api_key"])
    res = api.generateSession(cfg["client_code"], cfg["mpin_or_password"], pyotp.TOTP(cfg["totp_secret"]).now())
    if not res.get("status"):
        raise SystemExit(f"login failed: {res.get('message')}")
    return api


def snapshot(api: SmartConnect, tokens: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(tokens), 50):
        for attempt in range(4):
            try:
                res = api.getMarketData("FULL", {"NSE": tokens[i:i + 50]})
                for q in (res.get("data") or {}).get("fetched", []):
                    rec = {k: q.get(k) for k in ("ltp", "open", "high", "low", "close", "tradeVolume", "totBuyQuan", "totSellQuan", "exchFeedTime")}
                    depth = q.get("depth") or {}
                    rec["bid"] = (depth.get("buy") or [{}])[0].get("price")     # top of book: lets the summary be
                    rec["ask"] = (depth.get("sell") or [{}])[0].get("price")    # re-scored at bid/ask, not last price
                    out[str(q["symbolToken"])] = rec
                break
            except Exception:
                time.sleep(1 + attempt)
        time.sleep(1.05)   # quote API is limited to ~1 request/second
    return out


def wait_until(h: int, m: int, s: int) -> None:
    target = dt.datetime.now(IST).replace(hour=h, minute=m, second=s, microsecond=0)
    while (left := (target - dt.datetime.now(IST)).total_seconds()) > 0:
        time.sleep(min(left, 20))


def summarise(day: str, snaps: dict[str, dict], uni: dict[str, dict]) -> None:
    """Hedged rule per tier: long the 20% biggest gap-downs, short the 20% biggest gap-ups at the official open,
    exit 09:20. Scored twice: at last price, and conservatively at bid (longs) / ask (shorts)."""
    new = not (OUT / "summary.csv").exists()
    with open(OUT / "summary.csv", "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["date", "tier", "names", "gross_bp_last", "gross_bp_bidask", "net_bp_last", "indicative_overlap"])
        for tier in sorted({v["tier"] for v in uni.values()}):
            rows = []
            for tok, meta in uni.items():
                if meta["tier"] != tier:
                    continue
                o, p, a = snaps["open"].get(tok), snaps.get("pre", {}).get(tok), snaps["t0920"].get(tok)
                if not (o and a and o.get("open") and o.get("close") and a.get("ltp")):
                    continue
                ind = (p["ltp"] / p["close"] - 1) if (p and p.get("ltp") and p.get("close")) else None
                rows.append((o["open"] / o["close"] - 1, ind, o["open"], a["ltp"], a.get("bid") or a["ltp"], a.get("ask") or a["ltp"]))
            if len(rows) < 15:
                continue
            k = max(len(rows) // 5, 1)
            by_gap = sorted(rows, key=lambda r: r[0])
            longs, shorts = by_gap[:k], by_gap[-k:]
            last = (sum(r[3] / r[2] - 1 for r in longs) / k - sum(r[3] / r[2] - 1 for r in shorts) / k) / 2 * 1e4
            ba = (sum(r[4] / r[2] - 1 for r in longs) / k - sum(r[5] / r[2] - 1 for r in shorts) / k) / 2 * 1e4
            have = [r for r in rows if r[1] is not None]
            overlap = ""
            if len(have) >= 15:
                by_ind = sorted(have, key=lambda r: r[1])
                picked = {id(r) for r in by_ind[:k] + by_ind[-k:]}
                overlap = round(sum(id(r) in picked for r in longs + shorts) / (2 * k), 3)
            w.writerow([day, tier, len(rows), round(last, 2), round(ba, 2), round(last - COST * 1e4, 2), overlap])


def main() -> None:
    uni = universe()
    names = {t: v["name"] for t, v in uni.items()}
    api = login()
    tokens = sorted(names)
    if "--probe" in sys.argv:
        snap = snapshot(api, tokens)
        print(f"{len(snap)}/{len(tokens)} quotes;", "sample:", names[next(iter(snap))], next(iter(snap.values())))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    day = dt.datetime.now(IST).date().isoformat()
    snaps: dict[str, dict] = {}
    with open(OUT / f"{day}.jsonl", "a") as fh:
        for label, hms in SNAPS:
            wait_until(*hms)
            snaps[label] = snapshot(api, tokens)
            fh.write(json.dumps({"label": label, "taken": dt.datetime.now(IST).isoformat(), "quotes": {names[t]: q for t, q in snaps[label].items()}}) + "\n")
            fh.flush()
    if snaps.get("open") and any(q.get("tradeVolume") for q in snaps["open"].values()):
        summarise(day, snaps, uni)


if __name__ == "__main__":
    main()
