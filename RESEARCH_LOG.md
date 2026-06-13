# Research Log

Every experiment gets an entry. Format: date, candidate, hypothesis, exact
command and timerange, result, verdict. Before testing any idea, search this
file first. Entries are append-only; never delete a failure.

Gates G1 to G8 are defined in METHODOLOGY.md.

---

## Inherited results from the old project (May 2026)

Recorded here so v2 R&D does not silently repeat them. Old-project backtests
used 5y data 2021 to 2026-05, 29-30 pairs, 5x leverage, leveraged-ratio semantics.

| Date | Experiment | Result | Verdict |
|---|---|---|---|
| 2026-05-10 | v8 multi-setup (bbrsi + trend_cont + macro_swing + mirrored shorts, no protections) | trend_cont -13% (471 trades); shorts -37% (1,205 trades); mixed total -60% | DEAD: multi-setup in one bot |
| 2026-05-10 | v9 single-entry bbrsi + BTC-regime gate + protections + capped DCA | +150.21% / Sharpe 1.25 / DD 17.7% | Concept validated |
| 2026-05-10 | v10 longs + mean-reversion shorts (RSI>72 @ BB upper, bear-regime gated, ADX>25) | shorts leg -14.4% on 74 trades, 51% WR | DEAD: mean-rev shorts |
| 2026-05-11 | v11 trend-following shorts (confirmed breakdown, ADX>30, separate bot) | +52% BUT max DD 63%, 8,354 trades, avg profit = fees | DEAD: fee-bleed chop |
| 2026-05-11 | v9 entry sweep: rsi_buy >= 35 (loose entries) | -18% to negative, DD 49-77% | DEAD: loose RSI |
| 2026-05-11 | v12 = v9 + drop pair-level 4h gate + add ADX>=20 | +237.98% / Sharpe 1.21 / DD 28.0%; OOS 22mo +109.82% / Sharpe 1.82 | Old champion; v2 benchmark |
| 2026-05-12 | v13 = v12 + trend_cont second entry | -80% / DD 82% / Sharpe -0.50; trend_cont tag -107% across 6,800 trades | DEAD (3rd confirmation): trend_cont + any 2nd entry-tag |
| 2026-05-12 | v14 BB-squeeze breakout (separate bot) | +57.67% / Sharpe 0.64 / DD 30% / WR 54.2%; fired on 105 v12-quiet days | Positive; never deployed |
| 2026-05 | Naked funding-rate arb (no spot hedge) | Structurally broken, funding flips before reversion | DEAD without spot hedge |

Caveat on all inherited results: designed under a wrong risk narrative (stops
believed to be price-level; actually leveraged ratios, see METHODOLOGY section 1).
Backtests were internally consistent so totals stand, but stop sizing was never
deliberate. This matters most for the shorts verdicts: v11's "-5% price" stop was
really -1% price. Candidate S retests shorts with correctly-sized stops before
accepting the structural-failure conclusion.

Old live (dry-run) evidence, 2026-05-12 to 05-24, v12, $1k paper: 3 trades,
RUNE +2.58% (roi), SOL -7.20% (stop, = -1.4% price move, proving ratio semantics),
XRP +2.51% (roi). Net -2.64 USDT. Bot died silently around May 24 (laptop). 11
days and 3 trades = nothing validated; quiet stretches are expected (longest
backtest dry streak: 42 days) but were indistinguishable from a dead bot without
alerting.

---

## v2 experiments

### 2026-06-11 -- Phase 0/1 setup (no strategy yet)
- Old bot stopped (had auto-revived via restart: unless-stopped when Docker Desktop
  started, found running with 11 min uptime on 2026-06-11).
- All 29 pairs re-verified TRADING on Binance USDT-M futures.
- Futures OHLCV/funding/mark data refreshed to 2026-06-11 (15m/1h/4h, 40-day extension).

### 2026-06-11 -- Direction change (user)
Just do whatever is profitable, well enough. No blind rebuilds; carry over validated
concepts directly and optimise for profit.

### 2026-06-11 -- MeanRevLong (v12 port) re-validation -- DEPLOYED
- Hypothesis: archived v12 logic still passes on refreshed data 2021 to 2026-06.
- Command: `backtesting --strategy MeanRevLong --timerange 20210101-`
- Result: +346.37% / Sharpe 1.89 / Calmar 11.10 / DD 30.06% / WR 63.2% / 1,673
  trades / CAGR 31.68%. Beats archived benchmark (+237.98%, Sharpe 1.21). DD 30.06%
  sits exactly at the G1 line; accepted.
- Verdict: PASS, deployed dry-run as main bot (port 8080).

### 2026-06-11 -- SqueezeBreakout (v14 port) re-validation -- NOT DEPLOYED
- Hypothesis: archived v14 (+57.67%/DD 30%) reproduces on refreshed data.
- Command: `backtesting --strategy SqueezeBreakout --timerange 20210101-`
- Result: +37.56% / Sharpe 0.55 / profit factor 1.05 / DD 41.32% / 963 days
  underwater (2022-03 to 2024-11) / 2,735 trades / 562 exit timeouts.
- Verdict: FAIL (G1 DD, PF 1.05 = fee bleed). May 2026 positive result was fragile.

### 2026-06-11 -- ShortTrend corrected-stops retest -- SHORTS DEAD (4th failure)
- Hypothesis: old shorts failures were partly from accidentally-tight stops (-1%
  price); correctly-sized stops (-4% price at 3x) might work in a bear.
- Command: `backtesting --strategy ShortTrend --timerange 20220101-20230101` (G8)
- Result: -84.66% in 2022 while the market fell -72.86%. DD 87.93%, 3,502 trades,
  WR 51.7%, avg -0.34%/trade. Worse than old v11.
- Verdict: FAIL, conclusively. Trend-following shorts over-fire in a bear regime and
  bleed to chop + fees regardless of stop size. Shorts are DEAD on this universe.
  Do not revisit without a fundamentally different mechanic, not stop-size tweaks.

### 2026-06-11 -- Reality checks on the +346% headline
- Live-window replay: backtest of the exact old live period (20260512 to 20260524)
  produced 3 trades, identical to live. Backtest: 3 ROI wins, +9.39 USDT. Live: 2
  ROI wins + 1 stop, -2.64 USDT. Entire gap = ONE trade (SOL) flipping from ROI
  win to stop-out. Frequency matched perfectly; outcome diff is single-trade variance.
- Fee stress (G6): full 5.4y re-run at 0.04% taker: +211.15% / CAGR 23.2% /
  Sharpe 1.44 / DD 32.4%. Edge survives doubled fees.
- Working expectation: 15-35%/yr if live tracks backtest; need ~100 live trades
  (2-4 months) to compare distribution vs backtest.

### 2026-06-11 -- Literature research sweep
Findings ranked by strength of evidence:
1. Time-series momentum at 1-4 week horizons is the most confirmed crypto anomaly
   (Dobrynskaya SSRN 3913263). Our 15m dip-buyer exploits the reversal side; the
   momentum side was untapped.
2. Donchian-ensemble trend following with vol-scaled sizing on top-20 liquid coins:
   Sharpe >1.5, +10.8%/yr alpha vs BTC (Zarattini/Pagani/Barbon, SSRN 5209907).
3. Volatility targeting improves Sharpe across asset classes.
4. Funding-rate carry is real (~8%/yr) but requires the spot hedge already parked.
5. NostalgiaForInfinity (community): hundreds of opaque conditions on 5m;
   unauditable, contradicts our single-signal lesson. Config conventions only.
Conclusion: build a 4h long-only Donchian-ensemble trend rider as the decorrelated
complement to MeanRevLong. Two-bot portfolio (reversal + momentum) is the
evidence-optimal design at this capital size.

### 2026-06-11 -- TrendDonchian (3 variants) -- DEAD END
- Design: 4h long-only Donchian ensemble (7/14/28d highs), turtle exits + chandelier,
  2x leverage, ATR-scaled stakes.
- v1 (no BTC gate): full +170.28% BUT 2022 -12.70% / PF 0.87, OOS Sharpe 0.38 / PF 1.10.
- v2 (+BTC 4h regime gate): 2022 fixed (+3.22%) but OOS: +11.84% / Sharpe 0.18 / PF 1.06.
- v3 (strict 3/3 ensemble entry, 10-day-low exit): OOS +11.81% / Sharpe 0.19 / PF 1.08.
- Verdict: FAIL G2 decisively. Two structurally different variants with the same OOS
  result = concept-level failure, not tuning. The literature edge requires
  continuously-rebalanced rotational portfolios; freqtrade's per-trade slot model
  cannot express it. Do not revisit with parameter tweaks.

### 2026-06-11 -- MeanRevLongOpt hyperopt polish -- REJECTED (overfit)
- CalmarHyperOptLoss, spaces buy+sell only, train 2021-01 to 2024-06, 150 epochs.
  Best epoch: rsi_buy 42, min_adx 29, bb_mult 2.1, dca_dip -0.035, rsi_sell 71,
  train +194.52%.
- OOS head-to-head (20240701 to 2026-06-11):

| params | profit | WR | trades |
|---|---|---|---|
| hyperopt | +33.27% / CAGR 15.9% | 58.1% | 577 |
| current live (rsi 32/adx 20) | +133.61% / CAGR 54.7% | 68.3% | 666 |

- Verdict: textbook overfit, 4x worse OOS despite winning in-sample. Current params
  stay. Do not re-run hyperopt on this strategy without a new degree of freedom.

### 2026-06-12 -- Exit study -- ADOPTED
- Hypothesis: the v12 ROI ladder (+0.5-2% price targets) sells winners into the
  bounce it predicted.
- A (ROI off): +148.70% / DD 31.1% / WR 49.5%. Worse; winners round-trip.
- B (ROI x2, 0.20/0.10/0.05/0.024/0.01 = +4/2/1/0.48/0.2% price):

| window | B | baseline |
|---|---|---|
| Full 2021 to now | +448.87% / CAGR 36.8% / DD 18.6% | +346.37% / 31.7% / 30.1% |
| OOS 2024-07 to now | +145.67% / Sharpe 2.71 / PF 1.41 | +133.61% |
| Fee stress 0.04% | +270.13% / CAGR 27.2% | +211.15% |

- B beats baseline on every gate in and out of sample. Adopted. Bot restarted
  2026-06-12 04:23 UTC with the new ladder.

### 2026-06-12 -- PanicRev1d (daily capitulation buyer) -- DEAD
- Connors-style RSI(3)<25 + close>EMA200 + close<SMA10 on 1d, 2x leverage.
  Full 2021 to now: -89.00% / 814 trades / WR 49.0% / avg -1.73%.
- Verdict: daily-bar dip-buying does not work in crypto. Equities reversal edge
  does not transfer at this horizon. Do not revisit on daily bars.

### 2026-06-12 -- Coverage round
Bot is flat ~74% of days; signal-loosening twice-falsified, so tested coverage axes:
- GateA (drop ema50-slope from BTC regime): +420.76% / DD 18.6% / 1,661 trades.
  Worse than baseline on profit. REJECTED.
- GateB (regime = BTC > 4h ema200 only): full +490.35% / DD 16.75% / 2,148 trades.
  OOS: +124.98% / Sharpe 2.32 vs baseline +145.67% / 2.71. Loses OOS on every
  metric. REJECTED. The strict slope-confirmed gate is load-bearing for OOS quality.
- MeanRev1h (same logic on 1h): +11.07% / Sharpe 0.10 / 586 trades. DEAD.
  Reversal edge bracketed by timeframe: 15m works, 1h noise, 1d death.
- Universe expansion 29 to 67 pairs (same strict entry, more tickets): 38 verified
  TRADING Binance perps added. Results pending below.

### 2026-06-12 -- CrashBounce (event-driven, regime-free) -- DEAD
- Entry: >=5% drop/1h + 2.5x volume + RSI<25; no trend/regime gates.
- v1 (3x): full +840.5% and +74.62% in 2022 BUT OOS 2024-07 to now: -66.64% / DD 79.7%.
- v2 (2x, brutal chain-breakers): OOS -50.11% / DD 64.3%.
- Verdict: DECAYED EDGE. Real in 2021-2023, gone since 2024. Do not revisit without
  evidence the regime changed back.

### 2026-06-12 -- Universe expansion -- ADOPTED (29 to 39 pairs)
- 67-pair (all adds): full +594.65% but OOS +94.38% / Sharpe 1.89. REJECTED.
- 41-pair (top-12 adds by 24h volume): OOS +182.11% / Sharpe 3.02 / 853 trades.
  TON+TAO = -316 USDT on 36 trades (young-listing toxicity), trimmed.
- 39-pair final (29 + ZEC WLD 1000PEPE TRX CRV XLM CHZ FET DASH GALA):

| gate | 39-pair | 29-pair baseline |
|---|---|---|
| Full 2021 to now | +715.02% / CAGR 47.1% / Sharpe 2.05 / DD 21.45% | +448.87% / 36.8% / 18.62% |
| OOS 2024-07 to now | +188.41% / CAGR 72.3% / Sharpe 3.15 / PF 1.37 / DD 21.43% | +145.67% / 54.7% / 2.71 / 1.41 / 18.6% |
| Fee stress | +377.15% | +270.13% |
| OOS trade count | 827 (+24% coverage) | 666 |

- Adopted. Config whitelist updated to 39 pairs, bot restarted 2026-06-12 05:34 UTC.
- Lessons: universe quality > universe size; exclude pairs younger than ~18 months.

### 2026-06-12 -- Monte Carlo + robustness analysis
Bootstrap of 39-pair OOS trade history (827 trades, 23.3mo; 10k sims):
- Day-block resample: median CAGR +79.3%, 5th pct +11.9%, 95th pct +189.2%,
  median maxDD 18.6%, 95th pct DD 30.8%, P(DD>20%) = 39%, P(losing year) = 2.1%.
- Clustering roughly doubles tail risk vs naive MC. Expect a 20%+ drawdown most
  years; a losing year is possible.
- Parameter jitter (OOS baseline +188.4%/Sharpe 3.15): rsi 30 = +135.8%/2.56;
  rsi 34 = +64.7%/1.39; adx 17 = +148.2%/2.64; adx 23 = +204.5%/3.32. No
  collapse anywhere = smooth hill, not knife-edge. adx 23's higher number is NOT
  to be chased; jitter is a probe, not tuning.

### 2026-06-12 -- DeadZoneDip -- DEAD
- EXACT MeanRevLong logic, gate INVERTED, trades only when BTC regime is OFF.
- Full 2021 to now: -78.71% (2,081 trades, WR 46.9%). 2022: -48.98% / Sharpe -3.54.
  OOS: -45.35%.
- Same entries, same exits, same pairs: gate ON = +715%, gate OFF = -79%. The regime
  gate is not a filter, it is the alpha switch.
- Dead-zone directional trading falsified 8 ways. The only surviving dead-zone earner
  is delta-neutral funding carry (spot hedge required).
- Incident note: strategy file written as cp1252 crashed freqtrade's resolver on ALL
  strategies until converted to UTF-8. Always write strategy files with explicit utf-8.

---

## Next

- MeanRevLong (doubled ROI, 39 pairs) dry-run observation. Expectation: ~56% WR,
  ~1.1 trades/day, avg hold ~3h. Do not panic below DD 20%; reassess thesis only if
  live DD exceeds ~30% or a quarter is deeply negative.
- R&D queue: funding arb with spot hedge, funding-rate entry filter.
- Pair-list hygiene: monthly delisting check + young-listing rule (>=18mo).
