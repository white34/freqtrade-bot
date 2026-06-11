# Methodology — freqtrade-bot v2

This file is the constitution of the rebuild. Every strategy, backtest, and deploy
decision follows the rules here. It exists because the old project (May 2026, see
`_archive/`) produced a profitable-looking backtest while carrying a 5x-wrong risk
narrative, three structurally failed shorts attempts, and a live bot that died
silently. Read this before writing or editing ANY strategy code.

---

## 1. The risk model (get this right or nothing else matters)

**Freqtrade applies `stoploss`, `minimal_roi`, trailing-stop values, and
`current_profit` to the LEVERAGED profit ratio (profit relative to stake), not to
the price move.**

Proven from the old bot's live DB (`_archive/tradesv3.sqlite`, trade #2):
SOL opened 95.72 at 5x with `stoploss = -0.07` → stop placed at 94.38 =
**-1.4% price** = -7% of stake. Not -7% price.

Conversion: `price_move = ratio / leverage`

| Setting (ratio) | At 1x (price) | At 3x (price) | At 5x (price) | Loss/gain on stake |
|---|---|---|---|---|
| stoploss -0.05 | -5.0% | -1.67% | -1.0% | -5% of stake |
| stoploss -0.07 | -7.0% | -2.33% | -1.4% | -7% of stake |
| stoploss -0.15 | -15.0% | -5.0% | -3.0% | -15% of stake |
| stoploss -0.25 | -25.0% | -8.33% | -5.0% | -25% of stake |
| roi 0.10 | +10.0% | +3.33% | +2.0% | +10% of stake |
| roi 0.025 | +2.5% | +0.83% | +0.5% | +2.5% of stake |

**Rules:**
1. Every strategy file MUST contain a comment block stating, for its chosen leverage:
   stop in price terms, stop in stake terms, and each ROI rung in price terms.
2. Stop distances are DESIGNED in price terms first (e.g. "shorts need 4% price room
   for squeezes"), then converted to the ratio for the configured leverage.
3. Wallet-level loss per stopped trade = `|stoploss| × stake`. With
   `max_open_trades = 8` and unlimited stake, one stake ≈ 12.5% of capital, so a
   -0.07 stop costs ≈ 0.9% of the wallet. State this in the strategy header too.
4. Leverage choice must have a written rationale (why 3x/5x, what price-stop it
   implies). "More leverage = more profit" is not a rationale: leverage divides the
   price-stop distance, raises fee+funding surface vs margin, and changes nothing
   about edge.

## 2. Evaluation gates (every candidate, no exceptions)

Run in order; a candidate that fails any gate is documented in RESEARCH_LOG.md and
stopped. Don't iterate aggressively on a failed concept — every iteration burns
time and the concept may be structurally broken (old project re-learned this 4x).

| # | Gate | Pass criteria |
|---|---|---|
| G1 | Full-history backtest (2021-01 → now) | Total profit > 0, max DD < 30% |
| G2 | OOS holdout: train 2021-01→2024-06, test 2024-07→now | Profit > 0, Sharpe > 0.8, DD < 25%, WR > 55% |
| G3 | Walk-forward (NEW vs old project): 2 more rolling splits — train 2021→2022-12 / test 2023; train 2021→2023-12 / test 2024 | Both test windows profit > 0 (no single lucky holdout) |
| G4 | Per-entry-tag | Every tag net-positive standalone; no carried losers |
| G5 | Per-pair concentration | No pair > 30% of total losses |
| G6 | Fee sensitivity | Re-run G1 with fee 0.0004 (taker); still net-positive |
| G7 | Architecture | New signal class = separate bot. Never add a second entry setup inside an existing gated bot (failed 4x in old project) |

For shorts candidates additionally:
| G8 | Bear-window check | Backtest 2022-01→2022-12 alone (the bear year). A shorts strategy that can't make money in 2022 has no reason to exist |

Hyperopt policy:
- Only AFTER a candidate passes G1–G3 on hand-set defaults. Hyperopt is for
  polishing a real edge, not for finding one.
- Loss function: CalmarHyperOptLoss; `--spaces` exclude stoploss (set by design,
  Section 1); train period only (never the OOS window); re-run G2 after.
- **Always diff the generated `<Strategy>.json` against intent before running the
  bot** — it silently overrides the `.py` defaults (the old "broken exits" bug).

## 3. Fixed universe & market assumptions

- 29 pairs (re-verified all TRADING on Binance USDT-M futures, 2026-06-11):
  BTC ETH SOL XRP ADA AVAX DOT LINK LTC ATOM DOGE NEAR AAVE UNI FIL INJ ARB OP APT
  SUI TIA SEI RUNE ETC ALGO IMX BCH GRT AXS (all `/USDT:USDT`)
- Same universe for every candidate (comparability). Pair-list changes are a
  methodology change, logged here.
- Static list rots: check Binance delisting announcements monthly (MKR died mid-run
  in the old project).
- Fees: maker 0.02% via post-only entries; taker 0.04% (gate G6).
- Funding/mark data downloaded alongside OHLCV — futures backtests are invalid without it.
- Timeframes 15m and up. Laptop hosting note: fewer/longer trades (1h/4h candidates)
  tolerate data gaps better than 15m scalping.

## 4. Benchmarks from the old project (the bar to beat)

Backtests on the same universe/data, leveraged-ratio semantics, 5x:

| Strategy (archived) | 5y backtest | OOS 22mo | Notes |
|---|---|---|---|
| v12 mean-reversion longs | +237.98%, Sharpe 1.21, DD 28.0%, WR 63.5%, 1529 trades | +109.82%, Sharpe 1.82, DD 17.4%, WR 69% | OOS beat in-sample — strongest old result |
| v14 BB-squeeze breakout | +57.67%, Sharpe 0.64, DD 30%, WR 54.2%, 2432 trades | — | Passed on complementary coverage, never deployed |
| v9 baseline | +150.21%, Sharpe 1.25, DD 17.7% | — | Pre-relaxation parent of v12 |

A rebuilt candidate in the same signal class should land in the same neighborhood.
If a blind rebuild can't get near v12, that is evidence v12 was overfit — record it,
don't quietly tune toward the old numbers.

## 5. Known dead ends (from `_archive/FUTURE_STRATEGIES.md`, re-challenge only with a NEW hypothesis)

- **Trend-continuation pullback entries**: 3 failures (-13%, -60%, -107%).
- **Adding any 2nd entry-tag to a gated bot**: always net-negative. Separate bots work.
- **Loose RSI entries** (rsi_buy ≥ 35 on mean-reversion): -18%+, DD 49–77%.
- **Naked funding-rate arb** (no spot hedge): structurally broken.
- **Shorts (3 attempts)**: mirrored (-37%), mean-rev in bear regime (-14%),
  trend-following (+52% but DD 63%, profit ≈ fees). *Caveat: all three were designed
  under the wrong leverage model — e.g. v11's "-5%" stop was really -1% price.
  The v2 retry (Candidate S) gets correctly-sized price stops and gate G8. If it
  fails again with correct sizing, shorts are dead until a sustained bear regime.*

## 6. Process rules

1. `RESEARCH_LOG.md` entry for EVERY experiment: hypothesis, exact command/timerange,
   result, verdict. Before testing an idea, grep the log — has it failed before?
2. Git: every strategy change is a commit. No filename-suffix versioning (v2…v14).
3. Strategy selection only via `config.json`; compose has no `--strategy` flag.
4. Secrets only in `.env` / generated values; never personal passwords; `_archive/`
   stays gitignored (contains old secrets).
5. Dry-run discipline: 4+ weeks live-dry, compare trade distribution against
   backtest expectation, before ANY real-money discussion. Real money additionally
   requires: API keys IP-restricted + withdrawal-disabled + MFA + billing alerts.
6. Monitoring is part of "working": Telegram notifications on, heartbeat ping
   configured (see README). A bot whose death goes unnoticed for 3 weeks (old
   project, May 24 → June 11) does not count as deployed.
