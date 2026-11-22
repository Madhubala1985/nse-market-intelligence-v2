# Project APEX — what we tried, how, and why it failed

Written 2026-11-22. This folder is research only. Nothing here places an order.

## What we are trying to do

Turn a trading system that lost money into one that makes money after all costs, for a small
account (about ₹4 lakh) on Indian markets. The rule is that nothing trades real money until it has
passed fixed tests on history and then on paper.

## Where we started

The original system traded Indian index options intraday (minutes to hours). Its live paper book
ended at 149 trades, 35% winners, **−₹31,948**, and was stopped on 2026-09-02. Follow-up studies
showed why: at intraday horizons the average price move is about the same size as the cost of
trading it. Signals were often right about direction and still lost money.

## What this sweep did

The earlier work only ever changed the signal. This sweep changed the two things never changed
before:

- **Horizon:** hold for days to months instead of minutes, so costs are a smaller share of the move.
- **Breadth:** trade across about 200 stocks instead of 3 indices.

How it was done:

1. **Data.** 16 years (2010–2026) of official NSE end-of-day files for every stock, future and
   index option, including delisted names, plus daily institutional/retail positioning since 2012.
   Angel One's free API supplied split-adjusted daily prices and 1-minute and 5-minute bars.
2. **Rules written first.** `APEX_DECLARATION.md` lists every idea, its exact specification, the
   costs to charge and the pass/fail tests. It was written before any return was computed, so
   results could not be tuned to look good.
3. **Realistic costs.** Futures 15 bp per round trip, cash delivery 30 bp, index options 1.5% of
   premium per side plus ₹20 per order. (1 bp = 0.01%.)
4. **Seven tests, all must pass.** Strong statistical significance after costs, positive in most
   calendar years, positive in both halves of the sample, positive without the best month, positive
   on 2024–2026 data held back, positive at double cost, and stable when the settings are nudged.
5. **Everything reported.** Every idea is in `APEX_RESULTS.md`, pass or fail.

## What happened

**21 ideas were tested. None passed.**

| Family | Ideas | Outcome |
|---|---|---|
| Stock selection | momentum, short-term reversal, trend, low volatility, 52-week high, long-only momentum | Small gross returns; after costs weak or negative. Momentum's advantage over the market was zero in 2024–26 |
| Overnight effects | overnight continuation in stocks, overnight vs intraday in NIFTY | Real effect (+39.5%/yr gross in stocks) but about 10 bp a night against 15–30 bp of cost: −35.9%/yr net |
| Futures | carry, calendar-spread reversion, open-interest build-up | Negative after costs |
| Positioning | follow foreign institutions, fade retail | No effect even before costs |
| Selling options | daily and monthly at-the-money straddles | No premium at the money; pays only in the last 1–3 days before expiry, for carrying crash risk |
| Calendar and intraday | turn of month, three intraday index-momentum rules | Too small (best: 3.4 bp gross against 15 bp cost) |
| Allocation | momentum with trend filter, NIFTY/gold/cash switching | Earned the market's return, nothing extra |
| Reaction to news shocks | drift after a large move on heavy volume | **Nearest miss:** +7.7%/yr net, passed every test except significance |

## Why it failed

1. **Costs are about as large as the edge.** Most of these effects are real before costs. They
   survive in the data because nobody can trade them at a profit, large funds included.
2. **These are textbook strategies.** Everyone knows them, so competition has pushed the profit
   down to the cost of trading. Testing them was worth doing once, because it had never been done
   here at longer horizons, but the outcome was predictable.
3. **A longer horizon and more stocks were not the missing ingredient.** That was the hypothesis of
   the sweep, and the data rejected it.
4. **The tests are strict on purpose.** With 21 ideas tried, a few will look good by luck. Several
   ideas that fail here would have "passed" a looser test and then lost real money.

Mistakes made and caught along the way are listed in `APEX_RESULTS.md`. The main ones were an
unadjusted price field that produced fake −50% days on stock splits, option contracts settled
before they expired, and an early version of the one lead below that looked alive only because it
was measured against the market and not as the profit of the positions actually held.

## The one thing that did show up

It did not come from the list. It came from looking at how the exchange opens.

NSE sets each stock's opening price in a single auction from orders collected before 09:08. When
a stock gaps up or down, that auction price overshoots and gives part of the gap back in the first
minute of trading. Buying the biggest gap-downs and shorting the biggest gap-ups at the open, in
equal amounts, was profitable in every year from 2013 to 2025.

Its current state:

- **Large stocks:** gone. A rule change on 2025-12-08 (a pre-open session for futures) removed it.
- **Less liquid stocks:** still there on paper, roughly +10 to +28 bp per day after costs, and
  shrinking.
- **Timing:** about three-quarters of it is over by 09:16. An ordinary order placed a minute late
  earns less than it costs.
- **Unproven:** whether a small order actually gets the auction price. History cannot answer that;
  only real orders can.

So it is a candidate for a paper test, not a strategy. `scripts/auction_fade_shadow.py` records
the quotes needed to judge it and sends no orders. It is not yet scheduled.

## What we take from this

- A small account cannot win on speed or cost. It can provide liquidity in places too small for
  big funds, and it can hold ordinary market risk.
- The only reliable return found was the plain one: NIFTY and gold held 50/50 returned about
  12%/yr over the sample. That is the market's return, not skill.
- Next ideas should start from how a specific part of the market works and who is forced to trade
  there, with data used to check size and cost. Three are worth one honest test each: drift after
  actual earnings dates, entries and exits from the F&O ban list, and index-rebalance flows.
- No profit is promised anywhere in this project.

## Files

| Path | What it is |
|---|---|
| `APEX_DECLARATION.md` | Ideas, costs and tests, fixed before any result |
| `APEX_RESULTS.md` | Full results for every idea, and the opening-auction detail |
| `apex/engine.py` | Data panels, cost model, portfolio simulator, the seven tests |
| `apex/build_panels.py` | Parses the raw NSE files |
| `apex/study_*.py` | One file per family of declared ideas |
| `apex/explore_*.py` | Follow-up checks, marked exploratory |
| `../scripts/fetch_nse_bhavcopy.py`, `fetch_nse_participant_oi.py`, `fetch_angel_history.py` | Data downloaders |
| `../scripts/auction_fade_shadow.py` | Logs-only recorder for the opening-auction test |

The data itself (about 5 GB) is not in the repository; the downloaders rebuild it. Broker
credentials are read from `configs/angelone_config.json`, which is not committed.
