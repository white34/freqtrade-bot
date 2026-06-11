# ============================================================
#  SqueezeBreakout — ported from archived PhDStrategy_v14_squeeze
#
#  Signal: volatility-expansion breakout. BB width compresses to a
#  multi-day low (squeeze), then price breaks above the upper band
#  with volume + rising ADX → enter long. The opposite trade class
#  to MeanRevLong (which buys dips); runs as a SEPARATE bot.
#
#  Archived benchmarks (5y 2021→2026-05, 29-30 pairs, 5x):
#    Full: +57.67% / Sharpe 0.64 / Calmar 1.89 / DD 30% / WR 54.2% / 2432 trades
#    Complementary: fired on 105 trading days MeanRevLong missed in the
#    OOS window (+90.83% sum-of-returns on those quiet days).
#    Value is COMPLEMENTARY coverage, not standalone metrics.
#
#  RISK MODEL at 5x leverage (METHODOLOGY.md §1 — ratios are
#  LEVERAGED stake ratios, NOT price moves):
#    stoploss -0.05  = -1.0% price = -5% of stake ≈ -0.6% of wallet
#    ROI 0.08/0.04/0.02/0.01 = +1.6% / +0.8% / +0.4% / +0.2% price
#    trailing: arms at 0.030 (=0.6% price), trails 0.015 (=0.3% price)
#  No DCA — averaging into a failed breakout is how accounts die.
# ============================================================

from datetime import datetime

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    informative,
    merge_informative_pair,
)


class SqueezeBreakout(IStrategy):

    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = False

    minimal_roi = {
        "0":   0.08,
        "60":  0.04,
        "180": 0.02,
        "480": 0.01,
    }

    stoploss = -0.05
    use_custom_stoploss = False

    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.030
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    startup_candle_count = 300
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    position_adjustment_enable = False

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 4},
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 96,
                "trade_limit": 15,
                "stop_duration_candles": 24,
                "max_allowed_drawdown": 0.18,
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
                "trade_limit": 5,
                "stop_duration_candles": 12,
                "only_per_pair": False,
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 192,
                "trade_limit": 3,
                "stop_duration_candles": 48,
                "required_profit": -0.02,
            },
        ]

    bb_mult           = DecimalParameter(1.8, 2.4, default=2.0, decimals=1, space="buy")
    squeeze_pct       = DecimalParameter(0.10, 0.40, default=0.25, decimals=2, space="buy")
    squeeze_lookback  = IntParameter(48, 192, default=96, space="buy")
    breakout_vol_mult = DecimalParameter(1.0, 2.5, default=1.5, decimals=1, space="buy")
    min_adx           = IntParameter(20, 35, default=25, space="buy")
    rsi_max_entry     = IntParameter(60, 80, default=72, space="buy")
    rsi_exit_overbought = IntParameter(70, 85, default=80, space="sell")

    def leverage(
        self, pair: str, current_time: datetime, current_rate: float,
        proposed_leverage: float, max_leverage: float, side: str, **kwargs,
    ) -> float:
        return min(5.0, max_leverage)

    def informative_pairs(self):
        if self.dp:
            pairs = self.dp.current_whitelist()
        else:
            pairs = []
        infs = [(p, "4h") for p in pairs]
        if ("BTC/USDT:USDT", "4h") not in infs:
            infs.append(("BTC/USDT:USDT", "4h"))
        return infs

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema50"]  = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema21"]  = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema55"]  = ta.EMA(dataframe, timeperiod=55)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        bb = ta.BBANDS(
            dataframe, timeperiod=20,
            nbdevup=float(self.bb_mult.value),
            nbdevdn=float(self.bb_mult.value), matype=0,
        )
        dataframe["bb_upper"] = bb["upperband"]
        dataframe["bb_mid"]   = bb["middleband"]
        dataframe["bb_lower"] = bb["lowerband"]

        dataframe["bb_width"] = (
            (dataframe["bb_upper"] - dataframe["bb_lower"]) / dataframe["bb_mid"]
        )

        lookback = int(self.squeeze_lookback.value)
        threshold_pct = float(self.squeeze_pct.value)
        dataframe["bb_width_quantile"] = (
            dataframe["bb_width"].rolling(lookback).quantile(threshold_pct)
        )
        dataframe["in_squeeze"] = (
            dataframe["bb_width"] <= dataframe["bb_width_quantile"]
        ).astype(int)
        dataframe["recently_squeezed"] = (
            dataframe["in_squeeze"].rolling(8).max().fillna(0).astype(bool)
        )

        dataframe["vol_sma20"] = dataframe["volume"].rolling(20).mean()

        dataframe["adx_rising"] = dataframe["adx"] > dataframe["adx"].shift(2)

        # BTC-only regime (same as MeanRevLong)
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
            dataframe["btc_regime_up_4h"] = 1

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        squeeze_breakout = (
            (dataframe["btc_regime_up_4h"] == 1) &
            dataframe["recently_squeezed"] &
            (dataframe["in_squeeze"] == 0) &
            (dataframe["close"] > dataframe["bb_upper"]) &
            (dataframe["volume"] > dataframe["vol_sma20"] * float(self.breakout_vol_mult.value)) &
            (dataframe["adx"] > self.min_adx.value) &
            dataframe["adx_rising"] &
            (dataframe["rsi"] < self.rsi_max_entry.value) &
            (dataframe["close"] > dataframe["ema200"]) &
            (dataframe["ema21"] > dataframe["ema55"])
        )

        dataframe.loc[squeeze_breakout, "enter_long"] = 1
        dataframe.loc[squeeze_breakout, "enter_tag"]  = "squeeze_breakout"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        exits = (
            (dataframe["rsi"] > self.rsi_exit_overbought.value) |
            (
                (dataframe["close"] < dataframe["ema21"]) &
                (dataframe["close"].shift(1) >= dataframe["ema21"].shift(1)) &
                (dataframe["volume"] > dataframe["vol_sma20"])
            ) |
            (dataframe["in_squeeze"] == 1)
        )
        dataframe.loc[exits, "exit_long"] = 1
        return dataframe
