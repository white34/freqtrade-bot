# ============================================================
#  CrashBounce — event-driven flash-capitulation buyer (long-only)
#
#  *** VERDICT 2026-06-12: DEAD — DECAYED EDGE, DO NOT DEPLOY ***
#  v1 (3x): full +840.5% BUT OOS 2024-07→ = -66.6% / DD 79.7%.
#  v2 (2x + chain-breakers): OOS -50.1% / DD 64.3%.
#  The edge was real 2021-2023 (+74.6% in 2022, Sharpe 2.94) and is
#  gone since 2024 — liquidation-bounce got arbitraged away. Risk
#  tweaks cannot fix a dead edge. See RESEARCH_LOG.md.
#
#  FUNDAMENTALLY DIFFERENT from MeanRevLong: no trend filter, no
#  BTC regime gate. Fires ONLY on violent panic candles — a ≥5%
#  drop within 1h on ≥2.5x volume with RSI pinned below 25. The
#  bet is the forced-liquidation rebound (non-fundamental selling
#  overshoots, then snaps back within hours).
#
#  Evidence basis: short-horizon crypto reversal is strongest after
#  extreme moves (liquidation cascades — see old roadmap idea #5);
#  unlike bbrsi this should fire in ALL regimes, including bears.
#  ACID TEST: must be profitable in 2022 standalone (gate G8-style).
#  Every regime-gated strategy here sat out 2022; a true diversifier
#  must catch capitulation wicks in a falling market.
#
#  RISK MODEL at 2x leverage (METHODOLOGY.md §1 — ratios are
#  LEVERAGED stake ratios, NOT price moves):
#    v2 (2026-06-12): v1 at 3x hit 79.5% max DD in systemic cascades
#    despite +840% total / +74.6% in 2022. v2 keeps identical PRICE
#    behavior at 2x and adds brutal chain-breakers (global guard
#    3 stops/6h, MaxDrawdown pause at 12%).
#    stoploss -0.09 = -4.5% price = -9% of stake ≈ -1.1% wallet
#    ROI 0.06/0.03/0.01/0.0 = +3.0% / +1.5% / +0.5% / breakeven
#      price targets at 0/1h/4h/12h — bounce is fast or it isn't real.
# ============================================================

from datetime import datetime

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
)


class CrashBounce(IStrategy):

    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = False

    # v2: 2x leverage, same PRICE targets as v1's 3x (+3%/+1.5%/+0.5%/BE)
    minimal_roi = {
        "0":   0.06,
        "60":  0.03,
        "240": 0.01,
        "720": 0.0,
    }

    stoploss = -0.09  # -4.5% price at 2x
    use_custom_stoploss = False

    trailing_stop = False

    process_only_new_candles = True
    startup_candle_count = 100
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    position_adjustment_enable = False

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 96,
                "trade_limit": 10,
                "stop_duration_candles": 24,
                "max_allowed_drawdown": 0.12,  # v2: brutal chain-breaker
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 48,
                "trade_limit": 2,
                "stop_duration_candles": 24,
                "only_per_pair": True,
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 24,
                "only_per_pair": False,
            },
        ]

    crash_ret_1h  = DecimalParameter(-0.10, -0.03, default=-0.05, decimals=3, space="buy")
    vol_mult      = DecimalParameter(1.5, 4.0, default=2.5, decimals=1, space="buy")
    rsi_max       = IntParameter(15, 35, default=25, space="buy")
    rsi_exit      = IntParameter(45, 70, default=55, space="sell")

    def leverage(
        self, pair: str, current_time: datetime, current_rate: float,
        proposed_leverage: float, max_leverage: float, side: str, **kwargs,
    ) -> float:
        return min(2.0, max_leverage)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        bb = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0)
        dataframe["bb_mid"] = bb["middleband"]
        dataframe["ret_1h"] = dataframe["close"] / dataframe["close"].shift(4) - 1
        dataframe["vol_sma20"] = dataframe["volume"].rolling(20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        crash = (
            (dataframe["ret_1h"] < float(self.crash_ret_1h.value)) &
            (dataframe["volume"] > dataframe["vol_sma20"] * float(self.vol_mult.value)) &
            (dataframe["rsi"] < self.rsi_max.value) &
            (dataframe["volume"] > 0)
        )
        dataframe.loc[crash, "enter_long"] = 1
        dataframe.loc[crash, "enter_tag"]  = "crash_bounce"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        exits = (
            (dataframe["rsi"] > self.rsi_exit.value) |
            (dataframe["close"] >= dataframe["bb_mid"])
        )
        dataframe.loc[exits, "exit_long"] = 1
        return dataframe
