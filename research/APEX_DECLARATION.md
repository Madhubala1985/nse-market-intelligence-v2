# APEX research sweep — declared 2026-11-22 BEFORE any return was computed

Scope: research only. Indian trading stays retired; nothing here places an order.

## Why this is different from everything tested before
Every prior study in this repo was INTRADAY on 1-3 indices, where measured gross edge ≈ cost.
This sweep moves the two variables never changed: HORIZON (days to months, where cost share
falls with √time) and BREADTH (a cross-section of ~150-230 stocks instead of 3 indices).

## Data
- NSE cash bhavcopy 2010→2026 (point-in-time, includes delisted names). Daily return =
  CLOSE / PREVCLOSE − 1 (NSE adjusts PREVCLOSE on ex-dates; verified against Angel before use).
- NSE F&O bhavcopy 2010→2026: every future and option, EOD settle, volume, OI.
- Angel One SmartAPI: index 1-min since 2016, daily since 2002 (cross-check only).
- Universe on any date = stocks with a listed stock future ON THAT DATE (no survivorship).

## Costs (charged on every side traded)
- Stock/index futures: 7.5 bps per side base (STT, exchange, stamp, GST, brokerage, 3 bps
  slippage) → 15 bps round trip; a monthly roll costs one extra round trip. Stress = 2×.
- Cash delivery: 15 bps per side base (STT 10 + stamp + slippage). Stress = 2×.
- Index options: 1.5% of premium per side + ₹20/order (the cost model that killed the fly).

## Hypotheses — ONE canonical spec each, taken from published literature, no tuning
| # | Hypothesis | Mechanism | Spec |
|---|---|---|---|
| H1 | Cross-sectional momentum | under-reaction, slow information diffusion | rank on return t−252..t−21; monthly; long top quintile, short bottom; equal weight |
| H2 | Short-term reversal | liquidity provision to forced sellers | rank on 5-day return; weekly; long losers, short winners |
| H2b | Residual reversal | same, market move stripped | H2 on market-beta residual returns |
| H3 | Time-series trend | under-reaction + hedger demand | each stock: sign of 252-day return, weight 1/vol(60d); monthly |
| H4 | Overnight continuation | clientele split (overnight vs intraday holders) | rank on mean overnight return last 21d; hold close→open only; daily |
| H5 | Low volatility | leverage-constrained investors overpay for risk | rank on 252-day vol; monthly; long lowest, short highest quintile |
| H6 | 52-week-high | anchoring | rank on close / 252-day high; monthly quintiles |
| H7 | Turn of month (NIFTY) | salary + SIP inflows hit at month start | long from close of 4th-last trading day to close of 3rd trading day |
| H8 | Futures carry | speculators pay for leverage; rich basis = crowded longs | rank on annualised near-month basis; weekly; long cheapest, short richest |
| H9 | OI build-up (trader lore) | none stated in literature — tested as lore | 5d return sign × 5d OI change > 0 → hold 5d in that direction vs unwinding names |
| H10 | Shock drift (PEAD proxy) | under-reaction to news | \|ret\| > 3σ(60d) AND volume > 3× 20d median → hold direction 20 days |
| H11 | Calendar-spread reversion | roll flow pushes next-near spread off carry | z(20d) of next/near − 1; \|z\|>2 → fade for 5 days |
| H12 | Index variance premium | insurance buyers overpay; seller is paid for tail | sell ATM NIFTY straddle at close, buy back next close, every day; nearest expiry with ≥2 DTE; FULL 2010-2026 tail incl. Mar-2020 |
| H12b | VRP held to expiry | same | sell ATM monthly straddle 21 trading days out, hold to expiry |
| H13 | Index overnight vs intraday | clientele split | NIFTY futures close→open vs open→close, whole sample |
| H14 | Long-only momentum (cash, small-capital feasible) | as H1 | top 20 names by H1 rank, monthly, cash delivery; vs equal-weight universe and NIFTY |
| H15 | FII index-futures positioning (added 01:05, before download) | FIIs are the marginal informed index trader | 5-day change in FII net index-futures contracts (long−short): >0 → long NIFTY, <0 → short, next 5 days; data is published after the close, so entry is the NEXT day's close |
| H16 | Retail crowding fade (added 01:05, before download) | retail "Client" positioning is the crowded, wrong side at extremes | z(60d) of Client net index-futures long: z>1.5 → short NIFTY, z<−1.5 → long, 5 days, entry next day's close |

## Gates — ALL must pass; a failing hypothesis is dead and is NOT re-tuned
1. Net of base cost: mean > 0 with t ≥ 3.0 (bar raised from 2.0 because ~16 hypotheses are tried).
2. ≥ 70% of calendar years positive AND no 3 consecutive losing years.
3. Both halves of the sample positive.
4. Positive after removing the best month (best 5 days for daily strategies).
5. Holdout 2024-01-01 → 2026 net positive (reported separately).
6. Still positive at 2× cost.
7. Declared neighbours (lookback ×0.5 and ×2) keep the same sign — sanity, not selection.

Passing = a paper-trading candidate, not an edge. Every hypothesis is reported, pass or fail.
Capital feasibility (₹4L, lot sizes, margin) is reported for every survivor.

## Additions declared 2026-11-22 ~02:00, before their data was loaded
| # | Hypothesis | Mechanism | Spec |
|---|---|---|---|
| I1 | Intraday index momentum (Gao-Han-Li-Zhou) | late-informed trading + hedging flows | sign of NIFTY return prev close→09:45 → hold 15:00→15:25; index-futures cost 15 bp round trip; 1-min data 2015-2026 |
| I3 | Half-day momentum | same | sign of return 09:15→13:00 → hold 13:00→15:25 |
| I4 | Expiry-day momentum | option sellers hedge short gamma in the direction of the move | I1 and I3 restricted to NIFTY expiry days |
| T1 | Momentum + trend filter (long-only, cash) | momentum crashes cluster in bear markets | H14 portfolio, but hold cash (0%) for the month when NIFTY futures < 200-day average at month end |
| T2 | Dual momentum across assets | independent premia; trend persistence | month end: hold NIFTYBEES or GOLDBEES, whichever has the higher 12-month return, if it beats 6.5%/yr cash; else cash at 6.5%; 15 bp per side |

For T1/T2 (long-only allocations) gate 1 is applied to ABSOLUTE return and, separately, to excess over buy-and-hold NIFTY — only the excess counts as "edge"; the absolute number is the equity premium.

## Flagged as EXPLORATORY (found by slicing results, so not confirmatory; listed for transparency)
H10b short-only shock drift · H12c straddle by days-to-expiry · weekend long straddle · A1 opening-auction fade.
