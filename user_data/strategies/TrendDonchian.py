# ============================================================
#  TrendDonchian — 4h Donchian-ensemble trend follower (long-only)
#
#  *** VERDICT 2026-06-11: FAILED G2 — DO NOT DEPLOY ***
#  v1 (no BTC gate): +170% full but -12.7% in 2022, DD ~48% at taker.
#  v2 (BTC gate): 2022 fixed (+3.2%) but OOS Sharpe 0.18 / PF 1.06.
#  v3 (strict 3/3 entry, 10d exit): OOS Sharpe 0.19 / PF 1.08.
#  Two structurally different variants, same OOS noise. The academic
#  edge (rotational vol-scaled portfolios) does not survive per-trade
#  breakout implementation in freqtrade. See RESEARCH_LOG.md.
#
#  EVIDENCE BASE (RESEARCH_LOG.md 2026-06-11):
#    - Crypto time-series momentum confirmed at 1-4 week horizons
#      (Dobrynskaya 2021; AUT TS/CS momentum paper)
#    - Donchian-ensemble + vol-scaled sizing on liquid coins:
#      Sharpe >1.5 (Zarattini/Pagani/Barbon, SSRN 5209907)
#    - Vol targeting improves Sharpe broadly (QuantPedia survey)
#
#  ROLE: medium-horizon trend rider, decorrelated complement to
#  MeanRevLong (short-horizon dip reversal). Separate bot.
#
#  Mechanics:
#    Entry: ensemble of breakout signals — close above the prior
#      7d / 14d / 28d highs (42/84/168 4h-candles). Enter when
#      >=2 of 3 are broken AND close > EMA200 AND BTC 4h regime up.
#      v1 had no BTC gate and lost -12.7% in 2022 buying bear
#      rallies (RESEARCH_LOG 2026-06-11); the gate fixed it.
#    Exit: close below prior 7d low (turtle exit) OR below the
#      chandelier line (22-bar highest high - 3*ATR22).
#    No ROI ceiling, no trailing — trends are allowed to run.
#    Stake: vol-scaled around freqtrade's base allocation
#      (clamped 0.5x-1.6x by ATR%), per vol-targeting literature.
#    No DCA, no shorts.
#
#  RISK MODEL at 2x leverage (METHODOLOGY.md §1 — ratios are
#  LEVERAGED stake ratios, NOT price moves):
#    stoploss -0.10 = -5.0% price = -10% of stake ≈ -1.2% of wallet
#      at the default ~12.5% allocation. Disaster stop only; the
#      working exits are the donchian-low / chandelier signals.
#    Funding cost while holding (~0.01%/8h typical) is real for
#      multi-day holds; included in backtests via funding data.
# ============================================================

from datetime import datetime
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    merge_informative_pair,
)


class TrendDonchian(IStrategy):

    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = False

    # No profit ceiling — trend exits handle it ("0": 100 is never hit)
    minimal_roi = {"0": 100}

    stoploss = -0.10
    use_custom_stoploss = False

    trailing_stop = False

    process_only_new_candles = True
    startup_candle_count = 260
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    position_adjustment_enable = False

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 1},
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 42,   # ~7 days of 4h
                "trade_limit": 8,
                "stop_duration_candles": 12,
                "max_allowed_drawdown": 0.20,
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 42,
                "trade_limit": 2,
                "stop_duration_candles": 12,
                "only_per_pair": True,
            },
        ]

    # Ensemble lookbacks in 4h candles (42/84/168 = 7/14/28 days)
    dc_fast   = IntParameter(30, 60,  default=42,  space="buy")
    dc_mid    = IntParameter(60, 120, default=84,  space="buy")
    dc_slow   = IntParameter(120, 240, default=168, space="buy")
    min_score = IntParameter(1, 3, default=3, space="buy")
    exit_lb   = IntParameter(30, 90, default=60, space="sell")
    chand_mult = DecimalParameter(2.0, 4.0, default=3.0, decimals=1, space="sell")

    # Vol-scaling reference: typical 4h ATR% midpoint for this universe
    ref_atr_pct = 0.018

    def leverage(
        self, pair: str, current_time: datetime, current_rate: float,
        proposed_leverage: float, max_leverage: float, side: str, **kwargs,
    ) -> float:
        return min(2.0, max_leverage)

    def informative_pairs(self):
        return [("BTC/USDT:USDT", "4h")]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["atr22"]  = ta.ATR(dataframe, timeperiod=22)
        dataframe["atr_pct"] = dataframe["atr22"] / dataframe["close"]

        # Prior-window extremes (shifted so the breakout candle isn't in its own window)
        dataframe["dc_high_fast"] = dataframe["high"].rolling(int(self.dc_fast.value)).max().shift(1)
        dataframe["dc_high_mid"]  = dataframe["high"].rolling(int(self.dc_mid.value)).max().shift(1)
        dataframe["dc_high_slow"] = dataframe["high"].rolling(int(self.dc_slow.value)).max().shift(1)
        dataframe["dc_low_exit"]  = dataframe["low"].rolling(int(self.exit_lb.value)).min().shift(1)

        dataframe["bull_score"] = (
            (dataframe["close"] > dataframe["dc_high_fast"]).astype(int)
            + (dataframe["close"] > dataframe["dc_high_mid"]).astype(int)
            + (dataframe["close"] > dataframe["dc_high_slow"]).astype(int)
        )

        # Chandelier line: highest high of last 22 bars minus 3*ATR(22)
        dataframe["chandelier"] = (
            dataframe["high"].rolling(22).max()
            - float(self.chand_mult.value) * dataframe["atr22"]
        )

        dataframe["vol_sma20"] = dataframe["volume"].rolling(20).mean()

        # BTC 4h regime gate (same construction as MeanRevLong; v1 without
        # it bled -12.7% in 2022 buying bear rallies)
        if self.dp and metadata["pair"] != "BTC/USDT:USDT":
            btc = self.dp.get_pair_dataframe("BTC/USDT:USDT", "4h")
            if btc is not None and not btc.empty:
                btc = btc.copy()
                btc["btc_ema50"]  = ta.EMA(btc, timeperiod=50)
                btc["btc_ema200"] = ta.EMA(btc, timeperiod=200)
                btc["btc_ema50_slope_up"] = btc["btc_ema50"] > btc["btc_ema50"].shift(3)
                btc["btc_regime_up"] = (
                    (btc["close"] > btc["btc_ema50"]) &
                    (btc["btc_ema50"] > btc["btc_ema200"]) &
                    btc["btc_ema50_slope_up"]
                ).astype(int)
                btc = btc[["date", "btc_regime_up"]]
                dataframe = merge_informative_pair(
                    dataframe, btc, self.timeframe, "4h", ffill=True,
                )
            else:
                dataframe["btc_regime_up_4h"] = 0
        else:
            btc_ema50 = ta.EMA(dataframe, timeperiod=50)
            btc_ema200 = ta.EMA(dataframe, timeperiod=200)
            dataframe["btc_regime_up_4h"] = (
                (dataframe["close"] > btc_ema50) &
                (btc_ema50 > btc_ema200) &
                (btc_ema50 > btc_ema50.shift(3))
            ).astype(int)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        breakout = (
            (dataframe["btc_regime_up_4h"] == 1) &
            (dataframe["bull_score"] >= int(self.min_score.value)) &
            (dataframe["close"] > dataframe["ema200"]) &
            (dataframe["volume"] > 0)
        )
        dataframe.loc[breakout, "enter_long"] = 1
        dataframe.loc[breakout, "enter_tag"]  = "donchian"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        exits = (
            (dataframe["close"] < dataframe["dc_low_exit"]) |
            (dataframe["close"] < dataframe["chandelier"])
        )
        dataframe.loc[exits, "exit_long"] = 1
        return dataframe

    def custom_stake_amount(
        self, pair: str, current_time: datetime, current_rate: float,
        proposed_stake: float, min_stake: Optional[float], max_stake: float,
        leverage: float, entry_tag: Optional[str], side: str, **kwargs,
    ) -> float:
        # Vol-scaled sizing: shrink stakes in high-vol names, grow in calm
        # ones, bounded so no position dominates (vol-targeting literature).
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return proposed_stake
        atr_pct = float(dataframe["atr_pct"].iloc[-1] or 0)
        if atr_pct <= 0:
            return proposed_stake
        mult = self.ref_atr_pct / atr_pct
        mult = max(0.5, min(1.6, mult))
        stake = proposed_stake * mult
        if min_stake is not None and stake < min_stake:
            stake = min_stake
        return min(stake, max_stake)
