# ============================================================
#  ShortTrend — shorts retest with DELIBERATE stop sizing
#
#  The old project's three shorts attempts all failed, but every one
#  was designed under the wrong leverage model (METHODOLOGY.md §1).
#  v11's "-5% price stop" was actually -1% price at 5x — no room for
#  routine squeeze noise. This is the ONE corrected retest before
#  shorts are declared dead until a sustained bear regime.
#
#  Entry logic: v11's trend-following breakdown (the least-bad of the
#  three old attempts: +52% but DD 63% with the accidental -1% stop).
#  Enter confirmed breakdowns (structure broken, ADX>30), never fade
#  tops. Bear-regime gated (BTC 4h down + pair 4h down).
#
#  RISK MODEL at 3x leverage (deliberate, designed price-first):
#    Shorts need squeeze room: 4% price stop chosen from crypto
#    bear-rally behavior. Lower leverage (3x not 5x) because shorts
#    carry squeeze tail-risk.
#    stoploss -0.12  = -4.0% price = -12% of stake ≈ -1.5% of wallet
#    ROI ladder (price-designed: 4%/2%/1%/0.5%/0.25% price):
#      0: 0.12, 60: 0.06, 180: 0.03, 480: 0.015, 960: 0.0075
#    trailing: arms at 0.09 (=3% price), trails 0.036 (=1.2% price)
#  No DCA — averaging into a losing short is how accounts die.
#
#  Gate G8: must be profitable on 2022 alone (the bear year).
#  If it can't make money there, it has no reason to exist.
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


class ShortTrend(IStrategy):

    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = True

    # Price-designed ladder (see header): ratios at 3x leverage
    minimal_roi = {
        "0":   0.12,
        "60":  0.06,
        "180": 0.03,
        "480": 0.015,
        "960": 0.0075,
    }

    stoploss = -0.12
    use_custom_stoploss = False

    trailing_stop = True
    trailing_stop_positive = 0.036
    trailing_stop_positive_offset = 0.09
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
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 96,
                "trade_limit": 20,
                "stop_duration_candles": 24,
                "max_allowed_drawdown": 0.15,
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 48,
                "trade_limit": 3,
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
                "trade_limit": 4,
                "stop_duration_candles": 48,
                "required_profit": -0.01,
            },
        ]

    bb_mult            = DecimalParameter(1.8, 2.4, default=2.0, decimals=1, space="buy")
    short_adx_min      = IntParameter(25, 40, default=30, space="buy")
    short_rsi_min      = IntParameter(30, 45, default=35, space="buy")
    short_rsi_max      = IntParameter(50, 60, default=55, space="buy")
    short_dist_ema200  = DecimalParameter(0.005, 0.04, default=0.010, decimals=3, space="buy")
    rsi_exit_oversold  = IntParameter(20, 35, default=25, space="sell")
    adx_exit_dying     = IntParameter(15, 25, default=22, space="sell")

    def leverage(
        self, pair: str, current_time: datetime, current_rate: float,
        proposed_leverage: float, max_leverage: float, side: str, **kwargs,
    ) -> float:
        return min(3.0, max_leverage)

    def informative_pairs(self):
        if self.dp:
            pairs = self.dp.current_whitelist()
        else:
            pairs = []
        infs = [(p, "1h") for p in pairs] + [(p, "4h") for p in pairs]
        if ("BTC/USDT:USDT", "4h") not in infs:
            infs.append(("BTC/USDT:USDT", "4h"))
        return infs

    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema21"]  = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema55"]  = ta.EMA(dataframe, timeperiod=55)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"]    = ta.RSI(dataframe, timeperiod=14)
        dataframe["trend_down"] = (
            (dataframe["ema21"] < dataframe["ema55"]) &
            (dataframe["ema55"] < dataframe["ema200"]) &
            (dataframe["close"] < dataframe["ema21"])
        ).astype(int)
        return dataframe

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema21"]  = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema50"]  = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"]    = ta.RSI(dataframe, timeperiod=14)
        dataframe["trend_stacked_down"] = (
            (dataframe["ema21"] < dataframe["ema50"]) &
            (dataframe["ema50"] < dataframe["ema200"]) &
            (dataframe["close"] < dataframe["ema21"])
        ).astype(int)
        dataframe["trend_down"] = (
            (dataframe["ema50"] < dataframe["ema200"]) &
            (dataframe["close"] < dataframe["ema50"])
        ).astype(int)
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

        dataframe["vol_sma20"] = dataframe["volume"].rolling(20).mean()
        dataframe["atr"]       = ta.ATR(dataframe, timeperiod=14)

        # BTC bear regime: 4h close < ema50 < ema200, ema50 sloping down.
        if self.dp and metadata["pair"] != "BTC/USDT:USDT":
            btc = self.dp.get_pair_dataframe("BTC/USDT:USDT", "4h")
            if btc is not None and not btc.empty:
                btc = btc.copy()
                btc["btc_ema50"]  = ta.EMA(btc, timeperiod=50)
                btc["btc_ema200"] = ta.EMA(btc, timeperiod=200)
                btc["btc_ema50_slope_down"] = btc["btc_ema50"] < btc["btc_ema50"].shift(3)
                btc["btc_regime_down"] = (
                    (btc["close"] < btc["btc_ema50"]) &
                    (btc["btc_ema50"] < btc["btc_ema200"]) &
                    btc["btc_ema50_slope_down"]
                ).astype(int)
                btc = btc[["date", "btc_regime_down"]]
                dataframe = merge_informative_pair(
                    dataframe, btc, self.timeframe, "4h", ffill=True,
                )
            else:
                dataframe["btc_regime_down_4h"] = 0
        else:
            dataframe["btc_regime_down_4h"] = dataframe.get("trend_down_4h", 0)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bear_regime = (
            (dataframe["btc_regime_down_4h"] == 1) &
            (dataframe["trend_down_4h"] == 1)
        )

        short_dist_ok = (
            (dataframe["ema200"] - dataframe["close"]) / dataframe["ema200"]
            >= float(self.short_dist_ema200.value)
        )

        trend_short = (
            bear_regime &
            (dataframe["ema21"] < dataframe["ema55"]) &
            (dataframe["ema55"] < dataframe["ema200"]) &
            (dataframe["close"] < dataframe["ema21"]) &
            short_dist_ok &
            (dataframe["adx"] > self.short_adx_min.value) &
            (dataframe["rsi"] >= self.short_rsi_min.value) &
            (dataframe["rsi"] <= self.short_rsi_max.value) &
            (dataframe["close"] < dataframe["bb_mid"]) &
            (dataframe["volume"] > dataframe["vol_sma20"] * 0.7) &
            (dataframe["volume"] > 0)
        )

        dataframe.loc[trend_short, "enter_short"] = 1
        dataframe.loc[trend_short, "enter_tag"]   = "trend_short"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        short_exits = (
            (dataframe["close"] <= dataframe["bb_lower"]) |
            (dataframe["rsi"] < self.rsi_exit_oversold.value) |
            (
                (dataframe["adx"] < self.adx_exit_dying.value) &
                (dataframe["adx"].shift(1) >= self.adx_exit_dying.value)
            ) |
            (
                (dataframe["close"] > dataframe["ema55"]) &
                (dataframe["close"].shift(1) <= dataframe["ema55"].shift(1)) &
                (dataframe["volume"] > dataframe["vol_sma20"])
            )
        )
        dataframe.loc[short_exits, "exit_short"] = 1
        return dataframe
