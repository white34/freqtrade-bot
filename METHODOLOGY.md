# Methodology

This is the rulebook for the rebuild. Every strategy, backtest, and deployment
decision follows what's written here. It exists because the original May 2026
project produced a profitable-looking backtest while carrying a completely wrong
risk narrative, three failed shorts attempts, and a live bot that died silently
for three weeks. Read this before touching any strategy code.

---

## 1. The risk model

Freqtrade applies stoploss, minimal_roi, trailing stop values, and current_profit
to the leveraged profit ratio (profit relative to stake), not to the price move.

Proven from the old bot's live DB (trade #2): SOL opened at 95.72 at 5x with
stoploss = -0.07, stop placed at 94.38 = -1.4% price = -7% of stake. Not -7% price.

Conversion: price_move = ratio / leverage

| Setting (ratio) | At 1x (price) | At 3x (price) | At 5x (price) | Loss/gain on stake |
|---|---|---|---|---|
| stoploss -0.05 | -5.0% | -1.67% | -1.0% | -5% of stake |
| stoploss -0.07 | -7.0% | -2.33% | -1.4% | -7% of stake |
| stoploss -0.15 | -15.0% | -5.0% | -3.0% | -15% of stake |
| stoploss -0.25 | -25.0% | -8.33% | -5.0% | -25% of stake |
| roi 0.10 | +10.0% | +3.33% | +2.0% | +10% of stake |
| roi 0.025 | +2.5% | +0.83% | +0.5% | +2.5% of stake |

Rules:
1. Every strategy file must have a comment block stating stop in price terms, stop
   in stake terms, and each ROI rung in price terms for its configured leverage.
2. Stop distances are designed in price terms first, then converted to the ratio.
3. Wallet-level loss per stopped trade = stoploss x stake. With max_open_trades = 8,
   one stake is roughly 12.5% of capital, so a -0.07 stop costs about 0.9% of the
   wallet. State this in the strategy header.
4. Leverage choice needs a written rationale. "More leverage = more profit" is not
   a rationale. Leverage divides the price-stop distance and raises fee and funding
   exposure without changing edge.

---

## 2. Evaluation gates

Run in order. A candidate that fails any gate gets documented in RESEARCH_LOG.md
and dropped. Don't iterate aggressively on a failed concept as it may be
structurally broken. The old project relearned this four times.

| # | Gate | Pass criteria |
|---|---|---|
| G1 | Full-history backtest (2021-01 to now) | Total profit > 0, max DD < 30% |
| G2 | OOS holdout: train 2021-01 to 2024-06, test 2024-07 to now | Profit > 0, Sharpe > 0.8, DD < 25%, WR > 55% |
| G3 | Walk-forward: 2 rolling splits (train 2021-2022 / test 2023, train 2021-2023 / test 2024) | Both test windows profit > 0 |
| G4 | Per-entry-tag | Every tag net-positive standalone |
| G5 | Per-pair concentration | No pair > 30% of total losses |
| G6 | Fee sensitivity | Re-run G1 at fee 0.0004 (taker), still net-positive |
| G7 | Architecture | New signal class = separate bot. Never add a second entry setup inside an existing gated bot |

For shorts candidates additionally:

| G8 | Bear-window check | Backtest 2022-01 to 2022-12 alone. A shorts strategy that cannot profit in 2022 has no reason to exist |

Hyperopt policy:
- Only after a candidate passes G1 to G3 on hand-set defaults. Hyperopt polishes
  a real edge, it does not find one.
- Loss function: CalmarHyperOptLoss. Exclude stoploss from spaces (set by design).
  Train period only, never the OOS window. Re-run G2 after.
- Always diff the generated strategy JSON against intent before running the bot.
  It silently overrides the .py defaults.

---

## 3. Universe and market assumptions

29 pairs, all verified trading on Binance USDT-M futures as of June 2026:
BTC ETH SOL XRP ADA AVAX DOT LINK LTC ATOM DOGE NEAR AAVE UNI FIL INJ ARB OP APT
SUI TIA SEI RUNE ETC ALGO IMX BCH GRT AXS (all /USDT:USDT)

- Same universe for every candidate. Pair-list changes are a methodology change
  and get logged here.
- Static lists rot. Check Binance delisting announcements monthly.
- Fees: maker 0.02% via post-only entries, taker 0.04% (gate G6).
- Funding and mark data downloaded alongside OHLCV. Futures backtests without it
  are invalid.
- Timeframes 15m and up. Fewer and longer trades tolerate laptop data gaps better
  than 15m scalping.

---

## 4. Benchmarks from the old project

Backtests on the same universe, leveraged-ratio semantics, 5x:

| Strategy | 5y backtest | OOS 22mo | Notes |
|---|---|---|---|
| v12 mean-reversion longs | +237.98%, Sharpe 1.21, DD 28.0%, WR 63.5%, 1529 trades | +109.82%, Sharpe 1.82, DD 17.4%, WR 69% | OOS beat in-sample |
| v14 BB-squeeze breakout | +57.67%, Sharpe 0.64, DD 30%, WR 54.2%, 2432 trades | n/a | Passed on coverage, never deployed |
| v9 baseline | +150.21%, Sharpe 1.25, DD 17.7% | n/a | Parent of v12 |

A rebuilt candidate in the same signal class should land in a similar range.
If a blind rebuild cannot get near v12, that is evidence v12 was overfit. Record
it, do not quietly tune toward the old numbers.

---

## 5. Known dead ends

Re-challenge only with a new hypothesis:

- Trend-continuation pullback entries: 3 failures (-13%, -60%, -107%).
- Adding a second entry-tag to a gated bot: always net-negative. Separate bots work.
- Loose RSI entries (rsi_buy >= 35 on mean-reversion): -18%+, DD 49-77%.
- Naked funding-rate arb with no spot hedge: structurally broken.
- Shorts (3 attempts): all failed, but all were designed under the wrong leverage
  model. The v2 retry gets correctly-sized price stops and gate G8. If it fails
  again with correct sizing, shorts are dead until a sustained bear regime.

---

## 6. Process rules

1. RESEARCH_LOG.md entry for every experiment: hypothesis, exact command and
   timerange, result, verdict. Before testing an idea, grep the log first.
2. Every strategy change is a commit. No filename-suffix versioning.
3. Strategy selection only via config.json. Compose has no --strategy flag.
4. Secrets only in .env. Never personal passwords. _archive/ stays gitignored.
5. Dry-run discipline: 4+ weeks live-dry, compare trade distribution against
   backtest expectation, before any real-money discussion. Real money additionally
   requires API keys that are IP-restricted, withdrawal-disabled, MFA enabled,
   and billing alerts on.
6. Monitoring is part of the build. Telegram on, heartbeat configured. A bot
   whose death goes unnoticed for three weeks does not count as deployed.
