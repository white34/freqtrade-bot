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

### 2026-06-11 — Reality checks on the +346% headline (user asked "is this realistic?")
- **Live-window replay**: backtest of the exact old live period (20260512–20260524)
  produced **3 trades** — identical count to live. Backtest: 3 ROI wins, +9.39 USDT.
  Live: 2 ROI wins + 1 stop, -2.64 USDT. Entire gap = ONE trade (SOL) flipping from
  ROI win to stop-out. Frequency matched perfectly; outcome diff is single-trade variance.
- **Fee stress (G6)**: full 5.4y re-run at 0.04% taker (double the maker fee):
  **+211.15% / CAGR 23.2% / Sharpe 1.44 / DD 32.4%**. Edge survives doubled fees —
  not fee-fragile (contrast SqueezeBreakout PF 1.05).
- Remaining honest discounts on the headline: backtest/dry-run fill optimism for
  post-only mean-reversion entries (adverse selection unmodeled — biggest unknown),
  survivor bias (best of ~14 variants on same history; mitigated by OOS>in-sample),
  regime dependence (profit clusters in bull-dip windows; ~0 expected in chop/bear).
- Working expectation: **15–35%/yr if live tracks backtest**; need ~100 live trades
  (2–4 months) to compare WR/avg-win/avg-loss/frequency vs backtest distribution.

### 2026-06-11 — Literature/online research sweep ("develop the best strategy possible")
Findings, ranked by strength of evidence × implementability:
1. **Time-series momentum at 1–4 week horizons** is the most-confirmed crypto anomaly:
   Dobrynskaya (SSRN 3913263) — momentum up to 2–4 weeks, reversal beyond ~1 month;
   confirmed by AUT TS/CS momentum study and others. Our 15m dip-buyer exploits the
   short-horizon *reversal* side; the *momentum* side was untapped.
2. **Donchian-ensemble trend following with vol-scaled sizing** on top-20 liquid
   coins: Sharpe >1.5, +10.8%/yr alpha vs BTC (Zarattini/Pagani/Barbon, SSRN 5209907,
   Concretum Group 2025).
3. **Volatility targeting improves Sharpe** across asset classes (QuantPedia survey;
   crypto momentum with vol filter ~1.2 vs ~1.0 Sharpe).
4. **Funding-rate carry** is real (~8%/yr at 0.8% vol — BIS WP 1087, CMU Crypto Carry)
   but requires the spot hedge we've already parked. Funding-as-signal: viable later.
5. **NostalgiaForInfinity** (community favorite): hundreds of opaque conditions on 5m;
   unauditable, contradicts our single-signal lesson. Config conventions only.
Conclusion: build a 4h long-only Donchian-ensemble trend rider with ATR-scaled
stakes as the decorrelated complement to MeanRevLong. Two-bot portfolio
(reversal + momentum) IS the evidence-optimal design at this capital size.

### 2026-06-11 — TrendDonchian (3 variants) ❌ DEAD END
- Design: 4h long-only Donchian ensemble (7/14/28d highs), turtle exits + chandelier,
  2x leverage, ATR-scaled stakes, evidence-based per SSRN 5209907.
- v1 (no BTC gate): full +170.28% (1,473 trades, WR 26.1%) BUT 2022 -12.70% /
  PF 0.87, OOS Sharpe 0.38 / PF 1.10, DD 48% at taker fees.
- v2 (+BTC 4h regime gate): 2022 fixed (+3.22%) but full only +105.2% (Sharpe 0.32)
  and OOS 2024-07→: +11.84% / **Sharpe 0.18 / PF 1.06** / DD 27.5%.
- v3 (strict 3/3 ensemble entry, 10-day-low exit): full +106.88%; OOS +11.81% /
  **Sharpe 0.19 / PF 1.08**. Identical OOS noise.
- Verdict: FAIL G2 decisively (need Sharpe >0.8). Two structurally different
  variants → same OOS result = concept-level failure in our framework, not tuning.
  The literature edge comes from continuously-rebalanced rotational vol-scaled
  portfolios; freqtrade's per-trade slot model can't express it. Do NOT revisit
  with parameter tweaks; only with a true portfolio-rotation engine (not freqtrade).

### 2026-06-11 — MeanRevLongOpt hyperopt polish ❌ REJECTED (overfit)
- Isolated sandbox (MeanRevLongOpt), CalmarHyperOptLoss, spaces buy+sell only,
  train 2021-01→2024-06, 150 epochs. Best epoch 29: rsi_buy 42, min_adx 29,
  bb_mult 2.1, dca_dip -0.035, rsi_sell 71 → train +194.52%.
- OOS head-to-head (20240701→2026-06-11, identical config):
  | params | profit | WR | trades |
  |---|---|---|---|
  | hyperopt | +33.27% / CAGR 15.9% | 58.1% | 577 |
  | **current live (rsi 32/adx 20)** | **+133.61% / CAGR 54.7%** | **68.3%** | 666 |
- Verdict: textbook overfit — 4x worse OOS despite winning in-sample. Adoption
  rule (OOS-must-improve) correctly rejected it. Current params stay. Sandbox
  files deleted (rejected param JSONs on disk are a footgun — broken-JSON lesson).
- Bonus datum: current params' OOS on refreshed data is +133.61% (archived run to
  May was +109.8%) — the edge held up through the newest month of data.
- Lesson recorded: hand-relaxed v9→v12 params have now beaten a fresh 150-epoch
  hyperopt OOS. Do not re-run hyperopt on this strategy without a NEW degree of
  freedom (different signal input, not the same 7 params).

### 2026-06-12 — Exit study (user: "exits too early/too often") ✅ ADOPTED
- Hypothesis: the v12 ROI ladder (+0.5–2% price targets) sells winners into the
  bounce it predicted. Entry-loosening was NOT tested (twice-falsified).
- A (ROI off): +148.70% / DD 31.1% / WR 49.5% — worse; winners round-trip.
- B (ROI ×2 → 0.20/0.10/0.05/0.024/0.01 = +4/2/1/0.48/0.2% price):
  | window | B | baseline |
  |---|---|---|
  | Full 2021→ | **+448.87% / CAGR 36.8% / DD 18.6%** | +346.37% / 31.7% / 30.1% |
  | OOS 2024-07→ | **+145.67% / Sharpe 2.71 / PF 1.41** | +133.61% |
  | Fee stress 0.04% | **+270.13% / CAGR 27.2%** | +211.15% |
- B beats baseline on every gate, in- AND out-of-sample → adopted into
  MeanRevLong; live bot restarted 2026-06-12 04:23 UTC with the new ladder
  (verified in startup log). Sandbox files deleted. User's live observation
  was correct and worth ~+100pp/5y and -11.5pp max drawdown.

### 2026-06-12 — PanicRev1d (daily capitulation buyer) ❌ DEAD
- Connors-style RSI(3)<25 + close>EMA200 + close<SMA10 on 1d, exit first strength,
  2x leverage. Full 2021→: **-89.00%** / 814 trades / WR 49.0% / avg -1.73%.
- Verdict: daily-bar "dips in uptrends" keep falling in crypto; the equities
  reversal edge does not transfer at this horizon. Do not revisit on daily bars.
- Note: this brackets the reversal edge by timeframe — it lives at 15m (validated),
  not at 1d (dead). Same lesson shape as trend (works in papers' weekly rotation,
  dead in per-trade 4h).

### On other asset classes (user offered forex/stocks, 2026-06-12)
Recommendation logged: stay crypto until ~10x capital. Freqtrade is crypto-only;
FX/equities need a new stack (MT5/IBKR), have thinner retail-algo edges, fee/data
overhead, and market hours. Crypto's documented inefficiencies are the edge at $2k.

### 2026-06-12 — Coverage round (user: "always misses really good opportunities")
Bot is flat ~74% of days; signal-loosening twice-falsified, so tested coverage axes:
- **GateA** (drop ema50-slope from BTC regime): +420.76% / DD 18.6% / 1,661 trades —
  worse than baseline on profit with no real coverage gain. ❌ REJECTED.
- **GateB** (regime = BTC > 4h ema200 only): full +490.35% / DD 16.75% / 2,148
  trades — dominated in-sample, BUT OOS: +124.98% / Sharpe 2.32 / PF 1.25 vs
  baseline's +145.67% / 2.71 / 1.41. Loses OOS on every metric = the extra
  trades were 2021-bull regime-fit. ❌ REJECTED by adoption rule. The strict
  slope-confirmed gate IS load-bearing for OOS quality.
- **MeanRev1h** (same logic on 1h): +11.07% / Sharpe 0.10 / 586 trades. ❌ DEAD.
  Reversal edge now triple-bracketed by timeframe: 15m works, 1h noise, 1d death
  (PanicRev1d -89%).
- **Universe expansion 29→67 pairs** (same strict entry, more tickets): 38 verified
  TRADING Binance perps added (TRX XLM VET HBAR ICP SAND MANA THETA EGLD CHZ GALA
  ONE CRV COMP SNX SUSHI YFI 1INCH DYDX ENS KAVA ZEC DASH ANKR IOTA NEO QTUM ZRX
  STORJ WLD TON 1000PEPE FET RENDER LDO STX TAO WIF; EOS delisted). Data
  downloaded; results pending below.
- Note for FreqUI readers: chart "exit signals" fire constantly by design (RSI>70 /
  BB-upper) and are meaningless without an open trade; entry scarcity is the real
  metric, addressed via universe size.

### 2026-06-12 — CrashBounce (fundamentally different: event-driven, regime-free) ❌ DEAD
- Entry: ≥5% drop/1h + 2.5x volume + RSI<25; no trend/regime gates. Fast bounce exits.
- v1 (3x): full +840.5% / CAGR 51% and **+74.62% in 2022 (Sharpe 2.94)** — the only
  strategy in project history to pass the bear-year acid test. BUT max account
  underwater 79.5%, and **OOS 2024-07→: -66.64% / DD 79.7%**.
- v2 (2x, same price levels, brutal chain-breakers): OOS **-50.11%** / DD 64.3%.
- Verdict: DECAYED EDGE. Real in 2021-2023, gone since 2024 (liquidation-bounce got
  arbitraged/front-run away as cascade data went mainstream). Risk tweaks cannot fix
  a dead edge. Do not revisit without evidence the regime changed back.

### 2026-06-12 — Universe expansion ✅ ADOPTED (29 → 39 pairs)
- 67-pair (all adds): full +594.65% but OOS +94.38% / Sharpe 1.89 — diluted. ❌
- 41-pair (top-12 adds by TODAY'S 24h volume — a-priori criterion, no OOS peeking):
  OOS +182.11% / Sharpe 3.02 / 853 trades. Full +664.85% but TON+TAO = -316 USDT
  on 36 trades (young-listing toxicity) → G5 trim.
- **39-pair final** (29 + ZEC WLD 1000PEPE TRX CRV XLM CHZ FET DASH GALA):
  | gate | 39-pair | 29-pair baseline |
  |---|---|---|
  | Full 2021→ | **+715.02% / CAGR 47.1% / Sharpe 2.05 / maxDD(acct) 21.45%** | +448.87% / 36.8% / 18.62% |
  | OOS 2024-07→ | **+188.41% / CAGR 72.3% / Sharpe 3.15 / PF 1.37 / DD 21.43%** | +145.67% / 54.7% / 2.71 / 1.41 / 18.6% |
  | Fee stress (41p proxy) | +377.15% | +270.13% |
  | OOS trade count | 827 (+24% coverage) | 666 |
- Metric note: console "Max % account underwater (balance)" (35.66%) includes open-
  position marks; the gate metric used throughout is closed-equity max_drawdown_account.
  DD window for both: 2025-01-17→26 (post-inauguration crash).
- Honesty note: 41p was a second look at the holdout after 67p rejection; criterion
  was a-priori (volume rank) and the win is dominant, but live tracking is the real
  test. Adopted: config whitelist → 39 pairs, bot restarted 2026-06-12 05:34 UTC,
  whitelist length 39 verified via API.
- Lessons: (1) universe quality > universe size — curate by current liquidity;
  (2) young listings (<1.5y) are toxic for 15m mean-reversion — exclude pairs
  younger than ~18 months at addition time.

### Next
- MeanRevLong (doubled ROI, 39 pairs) dry-run observation; expectation: ~56% WR,
  ~1.1 trades/day, avg hold ~3h.
- Later R&D queue: funding arb WITH spot hedge, funding-rate entry filter.
- Pair-list hygiene: monthly delisting check + young-listing rule (≥18mo).
