# Research Log

Every experiment gets an entry. Format: date, candidate, hypothesis, exact
command/timerange, result, verdict. **Before testing any idea, search this file —
has it failed before?** Entries are append-only; never delete a failure.

Gates G1–G8 are defined in [METHODOLOGY.md](METHODOLOGY.md) §2.

---

## Inherited results from the old project (May 2026, `_archive/`)

Recorded here so v2 R&D doesn't silently repeat them. Old-project backtests used
5y data 2021→2026-05, 29–30 pairs, 5x leverage, leveraged-ratio semantics.

| Date | Experiment | Result | Verdict |
|---|---|---|---|
| 2026-05-10 | v8 multi-setup (bbrsi + trend_cont + macro_swing + mirrored shorts, no protections) | trend_cont -13% (471 trades); shorts -37% (1,205 trades); mixed total -60% | DEAD: multi-setup in one bot |
| 2026-05-10 | v9 single-entry bbrsi + BTC-regime gate + protections + capped DCA | +150.21% / Sharpe 1.25 / DD 17.7% | Concept validated |
| 2026-05-10 | v10 longs + mean-reversion shorts (RSI>72 @ BB upper, bear-regime gated, ADX>25) | shorts leg -14.4% on 74 trades, 51% WR | DEAD: mean-rev shorts |
| 2026-05-11 | v11 trend-following shorts (confirmed breakdown, ADX>30, separate bot) | +52% BUT max DD 63%, 8,354 trades, avg profit ≈ fees | DEAD: fee-bleed chop |
| 2026-05-11 | v9 entry sweep: rsi_buy ≥ 35 (loose entries) | -18% to negative, DD 49–77% | DEAD: loose RSI |
| 2026-05-11 | v12 = v9 + drop pair-level 4h gate + add ADX≥20 | +237.98% / Sharpe 1.21 / DD 28.0%; OOS 22mo +109.82% / Sharpe 1.82 | Old champion; v2 benchmark |
| 2026-05-12 | v13 = v12 + trend_cont second entry | -80% / DD 82% / Sharpe -0.50; trend_cont tag -107% across 6,800 trades | DEAD (3rd confirmation): trend_cont + any 2nd entry-tag |
| 2026-05-12 | v14 BB-squeeze breakout (separate bot) | +57.67% / Sharpe 0.64 / DD 30% / WR 54.2%; fired on 105 v12-quiet days | Positive; never deployed |
| 2026-05 | Naked funding-rate arb (no spot hedge) | Structurally broken — funding flips before reversion | DEAD without spot hedge |

**Caveat on all inherited results:** designed under a wrong risk narrative
(stops believed to be price-level; actually leveraged ratios — see METHODOLOGY §1).
Backtests were internally consistent, so totals stand, but *stop sizing was never
deliberate*. This matters most for the shorts verdicts: v11's "-5% price" stop was
really -1% price. Candidate S retests shorts with correctly-sized stops before
accepting the structural-failure conclusion.

**Old live (dry-run) evidence, 2026-05-12 → 05-24, v12, $1k paper:** 3 trades —
RUNE +2.58% (roi), SOL -7.20% (stop, = -1.4% price move, proving ratio semantics),
XRP +2.51% (roi). Net -2.64 USDT. Bot died silently ~May 24 (laptop). 11 days /
3 trades = nothing validated; quiet stretches are expected (longest backtest dry
streak: 42 days) but were indistinguishable from a dead bot without alerting.

---

## v2 experiments

### 2026-06-11 — Phase 0/1 setup (no strategy yet)
- Old bot stopped (it had auto-revived via `restart: unless-stopped` when Docker
  Desktop started — found running with 11 min uptime on 2026-06-11).
- All 29 pairs re-verified TRADING on Binance USDT-M futures.
- Futures OHLCV/funding/mark data refreshed to 2026-06-11 (15m/1h/4h, 40-day extension).

### 2026-06-11 — Direction change (user)
"Just do whatever's profitable, well enough" — no blind rebuilds; carry over the
validated concepts directly and optimize for profit.

### 2026-06-11 — MeanRevLong (v12 port) re-validation ✅ DEPLOYED
- Hypothesis: archived v12 logic still passes on refreshed data 2021→2026-06.
- Command: `backtesting --strategy MeanRevLong --timerange 20210101-`
- Result: **+346.37% / Sharpe 1.89 / Calmar 11.10 / DD 30.06% / WR 63.2% /
  1,673 trades / CAGR 31.68%**. Beats archived benchmark (+237.98%, Sharpe 1.21) —
  May–June 2026 bull extension helped. DD 30.06% sits exactly at the G1 line
  (archived run: 28.01%); accepted.
- Verdict: PASS → deployed dry-run as the main bot (port 8080).

### 2026-06-11 — SqueezeBreakout (v14 port) re-validation ❌ NOT DEPLOYED
- Hypothesis: archived v14 (+57.67%/DD 30%) reproduces on refreshed data.
- Command: `backtesting --strategy SqueezeBreakout --timerange 20210101-`
- Result: **+37.56% / Sharpe 0.55 / profit factor 1.05 / DD 41.32% / 963 days
  underwater (2022-03→2024-11) / 2,735 trades / 562 exit timeouts**.
- Verdict: FAIL (G1 DD, and PF 1.05 ≈ fee bleed). The May-2026 positive result was
  fragile. Possible future rescue via hyperopt (squeeze_pct, breakout_vol_mult,
  min_adx); not worth bot #2 as-is.

### 2026-06-11 — ShortTrend corrected-stops retest ❌ SHORTS DEAD (4th failure)
- Hypothesis: old shorts failures were partly an artifact of accidentally-tight
  stops (-1% price); correctly-sized stops (-4% price at 3x) might work in a bear.
- Command: `backtesting --strategy ShortTrend --timerange 20220101-20230101` (G8)
- Result: **-84.66% in 2022 while the market fell -72.86%.** DD 87.93%, 3,502
  trades, WR 51.7%, avg -0.34%/trade. Worse than the old v11.
- Verdict: FAIL, conclusively. Trend-following shorts over-fire in a bear regime
  (the gate is open all year) and bleed to chop + fees regardless of stop size.
  Shorts are DEAD on this universe — do not revisit without a fundamentally
  different mechanic (not stop-size tweaks).

### Next
- MeanRevLong dry-run observation ≥4 weeks; compare live distribution vs backtest.
- Optional R&D queue (from `_archive/FUTURE_STRATEGIES.md`, in promise order):
  funding arb WITH spot hedge, 4h multi-timeframe trend, squeeze hyperopt rescue.
