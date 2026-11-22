# APEX research sweep — results (2026-11-22)

Rules were fixed in `APEX_DECLARATION.md` before any return was computed. Every hypothesis is listed,
pass or fail. Code: `research/apex/`. Research only — no order was placed and none can be (no static IP).

## Bottom line
- **21 pre-declared hypotheses, 0 pass.** Daily-to-monthly horizons and a 200-stock cross-section did not
  rescue the classic strategies. Most have a real gross effect that is smaller than the cost of trading it.
- **One exploratory find is statistically overwhelming: the opening-auction fade (A1).** Stocks that gap
  at the 09:00-09:08 pre-open auction give part of the gap back in the first five minutes. It was a very
  large edge through 2025 and was mostly closed by NSE's F&O pre-open session (live 2025-12-08).
  A hedged version still shows about +8-10 bp/day net on paper in less-liquid F&O stocks in 2026,
  and more in mid/small caps outside F&O.
  It is unverified on live fills and fading, so it is a **shadow-test candidate, not a strategy**.
- The only reliably positive return a ₹4L account can hold today is plain risk premium:
  NIFTY ≈ 12%/yr, gold ≈ 12.5%/yr, a 50/50 mix ≈ 12.2%/yr at two-thirds of the volatility.

## Data built (all reusable)
| Set | Coverage | Where |
|---|---|---|
| NSE cash bhavcopy | 2010-01 → 2026-11, 4,170 days, incl. delisted names | `data/nse_archive/cm`, parsed `data/apex/cm.pkl` |
| NSE F&O bhavcopy | same span; every future, every NIFTY/BANKNIFTY option | `data/nse_archive/fo`, `data/apex/fut.pkl`, `idxopt.pkl` |
| NSE participant OI | 2012 → 2026, FII/DII/Pro/Client | `data/nse_archive/poi` |
| Angel daily (adjusted) | 236 F&O stocks + 15 indices, from 2002 | `data/angel/daily` |
| Angel 1-min index | NIFTY, BANKNIFTY 2015 → 2026 | `data/angel/index_1m` |
| Angel 5-min stocks | 23 large caps 2023 →, ~30 less-liquid 2025 → | `data/angel/stock_5m` |

Two data traps found and fixed: bhavcopy `PREVCLOSE` is **not** split/bonus adjusted (repaired from
Angel's adjusted series, 411 days, plus a gap rule for dead names); and option rows for expiries beyond
the data end were briefly mis-settled (inflated 2026 straddle numbers; removed).

## Pre-declared hypotheses (net of declared costs, 2010-2026 unless noted)
| # | Hypothesis | Gross/yr | Net/yr | t | Years + | Verdict |
|---|---|---|---|---|---|---|
| H1 | Momentum 12-1 long/short | +11.0% | +6.5% | 1.34 | 9/16 | FAIL (t, years) |
| H14 | Top-20 momentum long-only, absolute | — | +15.8% | 2.94 | 10/16 | FAIL (just under t=3) |
| H14 | …excess over equal-weight universe | — | +4.9% | 1.68 | 11/16 | FAIL; 2024-26 excess +0.1% |
| H2 | 5-day reversal | +6.5% | −9.5% | −2.30 | 3/17 | FAIL (cost) |
| H2b | Residual reversal | +9.4% | −6.5% | −1.66 | 4/17 | FAIL (cost) |
| H3 | Time-series trend | — | +0.3% | 0.15 | 8/16 | FAIL |
| H4 | Overnight continuation | +39.5% | −35.9% | −20 | 0/17 | FAIL (real effect, t≈9 gross, but ≈10 bp/night vs 15-30 bp cost) |
| H5 | Low volatility | +7.8% | +3.8% | 0.70 | 6/16 | FAIL |
| H6 | 52-week high | +7.0% | +2.1% | 0.50 | 6/16 | FAIL |
| H7 | Turn of month, NIFTY | — | +4.1% | 1.98 | 11/17 | FAIL; 2024-26 −3.4% |
| H8 | Futures carry | +11.9% | −2.0% | −0.74 | 8/17 | FAIL; negative since 2015 |
| H9 | OI build-up lore | +1.5% | −6.4% | −2.08 | 4/17 | FAIL |
| H10 | Shock drift (PEAD proxy) | +10.3% | +7.7% | 2.46 | 13/17 | NEAR MISS — every gate but t≥3 |
| H11 | Calendar-spread reversion | +15.5% | −3.0% | −4.61 | 7/17 | FAIL (cost) |
| H12 | Daily 1-day short ATM straddle | +1.7 bp/day | negative | −10 | 0/17 | FAIL even at realistic cost (≈0) |
| H12b | Monthly straddle to expiry | — | −0.27%/mo | −1.28 | 4/17 | FAIL — no variance premium at the money |
| H13 | NIFTY overnight vs intraday | +6.0% overnight | −31.8% | — | 0/17 | FAIL (2.4 bp/night vs 15 bp) |
| H15 | Follow FII index-futures flow | −1.1% | −4.8% | −1.08 | 4/15 | FAIL |
| H16 | Fade retail positioning | −0.2% | −1.2% | −0.61 | 7/15 | FAIL |
| I1 | First-30-min → last-30-min | +0.5 bp/trade | — | 1.22 | — | FAIL |
| I3 | Morning → afternoon momentum | +3.4 bp/trade | — | 3.74 gross | — | FAIL (real, but 3 bp vs 15 bp cost) |
| I4 | Same on expiry days | no different | — | — | — | FAIL |
| T1 | Momentum + 200-day trend filter | — | +8.9% | 2.57 | 10/16 | FAIL; filter costs 7%/yr |
| T2 | Dual momentum NIFTY/gold/cash | — | +13.8% | 3.50 | 10/16 | FAIL; excess over NIFTY +1.8% (t 0.44) |

## Exploratory follow-ups (found by slicing — not confirmatory)
- **H10b short-only shock drift.** Event study looks strong (down-shocks lag the market 1.2% over 20 days,
  clustered t ≈ −5) but the hedged calendar-time portfolio nets +3.1%/yr, t 1.38, holdout +0.1%. FAIL.
- **H12c straddle by days-to-expiry.** Only the last 1-3 trading days pay. NIFTY 2 days out: +5.5 bp of
  notional per trade, t 3.6, worst −1.5%; BANKNIFTY last day: +7.4 bp, t 2.0, worst −7.7% of notional.
  Protective wings at ±2-4% remove all of it. Confirms the earlier small-sample finding; too thin for the tail.
- **Weekend long straddle.** Disappears once each weekend is counted once (t 1.3). FAIL.
- **Closing auction (CAS).** Dislocations revert ~17 bp overnight; delivery round trip costs ~25 bp. FAIL.

## A1 — opening-auction fade (the one live lead)
Mechanism: overnight retail order imbalance sets the single auction price too far from fair value; it
corrects within five minutes of continuous trading. 5-minute data shows the whole move is 09:15→09:20 and
nothing after, so it can only be captured by trading **in the auction** (order entered 09:00-09:07).

| Version | Period | Result (per unit of gross exposure, per day) |
|---|---|---|
| Decile long/short, all F&O stocks, open→close, 6 bp cost | 2013-2025 | every year positive; gross 19-64 bp/day |
| Same | 2026 | gross 10.8 bp/day (large caps 0.7, least-liquid third 22.6) |
| Unhedged (fade every gap > 0.75%), less-liquid tier, 5-min data | 2025 before reform | +28 bp net per trade, 12/12 months |
| Same | after 2025-12-08 | −6 bp net per trade — dead |
| Hedged quintile long/short within less-liquid tier, official open → 09:20, 8 bp cost | 2025 before reform | +12.2 bp net, t 4.8, 11/12 months |
| Same | 2025-12-08 → 2026-11 | **+8.3 bp net, t 4.3, 11/12 months** (+4.3 bp at 12 bp cost) |
| Same | since 2026-09-07 pre-open revision | +4.8 bp net, t 1.3 (46 days) |
| **Independent check:** same hedged rule on NSE daily data, less-liquid half (~104 stocks), open→close, 8 bp | 2019-2024 | +25.1 bp net, 71/72 months positive |
| Same | 2025-12-08 → 2026-11 | **+10.1 bp net, t 4.4, 11/12 months** |
| Same, more-liquid half | 2025-12-08 → 2026-11 | −2.9 bp net — dead |
| **Outside F&O** (not anchored by the F&O pre-open), same hedged rule, 15 bp cost: turnover rank 101-300 | 2019-2024 / after reform | +37.0 / **+11.1 bp net** (t 5.0, 11/12 months) |
| Outside F&O, turnover rank 301-600 (≈ ₹13 crore/day) | 2019-2024 / after reform | +67.3 / **+28.3 bp net** (t 13.5, 12/12 months, 81% of days) |
| Outside F&O, **5-minute data**, random sample of 39 stocks, first print → 09:20, gross | 2025-12 → 2026-11 | **+38.9 bp gross/unit/day, t 17, 12/12 months**; all of it in the first 5 minutes |

Bounce check on that sample: the estimated effective spread of the traded names is ~13 bp, so bid-ask bounce
explains at most ~7 bp of the 39 bp. Median turnover in the first five minutes is ₹67 lakh per stock
(10th percentile ₹10 lakh), enough for ₹50k-₹1L tickets. After ~15 bp of costs that is roughly +17 to +24 bp
per unit per day on paper — large enough that the remaining doubt is purely about execution, listed below.

**Timing (1-minute bars, 42 non-F&O stocks, Aug-Nov 2026):** +30 of the +39 bp happens between the 09:15:00
first print and 09:16; entering with an ordinary order at 09:16 leaves +7 bp gross, below cost. Gap-up names
print first near the top of the first minute's range and return 39% of the gap within that minute.
**So the edge exists only at the opening print itself** — it is earned by whoever supplies the other side of the
auction/first trade, and cannot be caught afterwards.

**Tail on the short leg:** in non-F&O rank 101-600, 1.3% of short-leg stock-days closed locked at an upper price
band; the 99th-percentile adverse move from open to the day's high is 12%. A 1-5 minute hold avoids most of it,
but a short that locks immediately cannot be covered.

Portfolio construction was chosen on 2019-2024 and reported once on the post-reform year: plain rank-based
quintiles with equal weights hold up best; weighting by gap size does worse (the biggest gaps are news and
do not fade). The effect is larger the thinner the stock — it is a payment for providing liquidity at the open,
which is why a small account fits it and a large fund cannot use it.

Paper economics for ₹4L at 5× intraday leverage (₹20L gross): about ₹1,660/day mean, ₹5,800 daily
standard deviation, worst day −₹13,000. Why this is not yet believable:
1. Fills are assumed at the official auction price; never tested live.
2. The long/short ranking needs the final gap, known only when the auction closes; the 09:06 indicative
   price must be a good proxy (untested).
3. Only one post-reform year exists and the effect is still shrinking (two independent data sets agree on its size).
4. Part of the measured fade may be bid-ask bounce on the first print; wide opening spreads could take up
   to half of the 16 bp gross. The recorder logs bid/ask so this can be scored properly.
5. Orders need a funded account and, for API placement, a registered static IP.
6. Flat ₹20-per-order brokerage is 4-8 bp on ₹50k-₹1L tickets — as large as the edge in F&O names. It needs
   either a zero-brokerage intraday plan or few, larger positions.
7. In thin stocks the auction often does not match, so the "open" is the first continuous trade. Getting
   that price means being the resting order an impatient trader hits — fills are then adversely selected,
   and an order placed into a thin auction moves the price against itself.
8. Outside F&O the numbers are bigger but so are the unknowns: opening spreads of 10-30 bp (part of the
   measured fade is bid-ask bounce), intraday-short eligibility, and shorts trapped at an upper circuit.

`scripts/auction_fade_shadow.py` records exactly what is needed to settle points 1-3 (logs only, no
orders; 818 stocks in five liquidity tiers, with bid/ask; `--probe` verified 818/818 quotes). It is **not scheduled** — the cron install was blocked.
To enable: `25 4 * * 1-5 cd ~/.cache/auction_shadow && <venv>/bin/python <repo>/scripts/auction_fade_shadow.py`
(04:25 CET = 08:55 IST). Pre-declared kill rule, applied per tier after 40 recorded sessions: drop the tier unless the bid/ask-scored
gross is ≥ 8 bp above that tier's cost (8 bp F&O, 15 bp non-F&O) and `indicative_overlap` ≥ 0.70.

### The cheapest decisive test
History cannot answer whether a small order gets the auction price. A live test can, for almost nothing:
for ~10 sessions place 1-share contrarian limit orders in the pre-open (09:00-09:07) on ~10 gapping stocks and
compare the fill price with the official open and the 09:16 price. Risk is a few hundred rupees; it needs a
funded account but no API or static IP (orders can be typed by hand). This is a real-money action, so it is
the operator's decision — nothing was placed.

## What the sweep says about the project
1. Horizon and breadth were not the missing ingredient. Published factor premia in Indian F&O stocks are
   real gross and ≤ cost net, and momentum's excess return was zero in 2024-26.
2. The edges that are large (auction fade, overnight drift) are microstructure edges with small capacity.
   That is where a small account has an advantage over large funds — and exchanges close them by rule
   changes, so they must be found early and monitored.
3. Short volatility is paid only in the last days before expiry and only for carrying the tail.
4. Next hypotheses worth one honest test each (data not yet in hand): true earnings-date drift (H10 was a
   proxy and nearly passed; NSE and BSE results-date APIs were not reachable from here), the new futures pre-open vs cash pre-open basis, F&O ban-list entry/exit,
   and index-rebalance flows.
