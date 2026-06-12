# ============================================================
#  PanicRev1d — daily-timeframe capitulation buyer (long-only)
#
#  *** VERDICT 2026-06-12: DEAD — DO NOT DEPLOY ***
#  Full 2021→2026-06: -89.00% / 814 trades / WR 49.0% / avg -1.73%.
#  Daily-bar "dips in uptrends" in crypto keep falling; the Connors
#  edge does not transfer at this timeframe/universe. See RESEARCH_LOG.
#
#  CONCEPT (Connors RSI(2/3) family, adapted to crypto):
#  Buy multi-day panic selloffs inside intact long-term uptrends;
#  exit on the first sign of strength. Decades of evidence in
#  equities for short-horizon reversal after compressed selloffs;
#  crypto reversal at short horizons is academically confirmed
#  (RESEARCH_LOG 2026-06-11 literature sweep).
#
#  ROLE: horizon-decorrelated sibling of MeanRevLong. MeanRevLong
#  scalps intraday dips (15m, holds ~2h); this holds multi-day
#  swings (1d, holds ~2-7 days). Separate bot if deployed.
#
#  Mechanics:
#    Entry (1d close): RSI(3) < 25 (compressed multi-day selloff)
#      AND close > EMA200 (long-term uptrend intact)
#      AND close < SMA10 (actually stretched below the mean)
#    Exit: RSI(3) > 60 (bounce played out) OR close > prior day's
#      high (breakout strength = take it) OR 8 days in trade.
#    No ROI ladder. No DCA. No shorts.
#
#  RISK MODEL at 2x leverage (METHODOLOGY.md §1 — ratios are
#  LEVERAGED stake ratios, NOT price moves):
#    stoploss -0.18 = -9.0% price = -18% of stake ≈ -2.2% of wallet
#      at ~12.5% allocation. Wide on purpose: daily-bar panic dips
#      need room; the exit signals are the working exits.
# ============================================================

from datetime import datetime
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
)


class PanicRev1d(IStrategy):

    INTERFACE_VERSION = 3
    timeframe = "1d"
    can_short = False

    minimal_roi = {"0": 100}

    stoploss = -0.18
    use_custom_stoploss = False

    trailing_stop = False

    process_only_new_candles = True
    startup_candle_count = 210
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    position_adjustment_enable = False

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 1},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 7,
                "trade_limit": 2,
                "stop_duration_candles": 3,
                "only_per_pair": True,
            },
        ]

    rsi_entry  = IntParameter(15, 35, default=25, space="buy")
    rsi_exit   = IntParameter(50, 75, default=60, space="sell")
    max_days   = IntParameter(5, 12, default=8, space="sell")

    def leverage(
        self, pair: str, current_time: datetime, current_rate: float,
        proposed_leverage: float, max_leverage: float, side: str, **kwargs,
    ) -> float:
        return min(2.0, max_leverage)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi3"]   = ta.RSI(dataframe, timeperiod=3)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["sma10"]  = ta.SMA(dataframe, timeperiod=10)
        dataframe["prev_high"] = dataframe["high"].shift(1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        panic = (
            (dataframe["rsi3"] < self.rsi_entry.value) &
            (dataframe["close"] > dataframe["ema200"]) &
            (dataframe["close"] < dataframe["sma10"]) &
            (dataframe["volume"] > 0)
        )
        dataframe.loc[panic, "enter_long"] = 1
        dataframe.loc[panic, "enter_tag"]  = "panic_dip"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        strength = (
            (dataframe["rsi3"] > self.rsi_exit.value) |
            (dataframe["close"] > dataframe["prev_high"])
        )
        dataframe.loc[strength, "exit_long"] = 1
        return dataframe

    def custom_exit(
        self, pair: str, trade: Trade, current_time: datetime,
        current_rate: float, current_profit: float, **kwargs,
    ) -> Optional[str]:
        # Time stop: reversion thesis is stale after max_days
        if (current_time - trade.open_date_utc).days >= int(self.max_days.value):
            return "time_stop"
        return None
