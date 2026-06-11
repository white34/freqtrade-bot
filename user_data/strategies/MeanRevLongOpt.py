# ============================================================
#  MeanRevLongOpt — hyperopt sandbox copy of archived PhDStrategy_v12 (validated champion)
#
#  Signal: mean-reversion long. Buy oversold dips (BB lower + RSI<32,
#  ADX>=20) on 15m, gated by BTC 4h bull regime. Single entry tag.
#  Logic identical to the archived v12 (which passed all gates in
#  May 2026); only this header is new.
#
#  Archived benchmarks (5y 2021→2026-05, 29-30 pairs, 5x):
#    Full: +237.98% / Sharpe 1.21 / Calmar 8.43 / DD 28.01% / WR 63.5% / 1529 trades
#    OOS 22mo (2024-07→2026-05): +109.82% / Sharpe 1.82 / DD 17.41% / WR 69%
#
#  RISK MODEL at 5x leverage (METHODOLOGY.md §1 — ratios are
#  LEVERAGED stake ratios, NOT price moves):
#    stoploss -0.07  = -1.4% price = -7% of stake ≈ -0.9% of wallet
#                      (stake ≈ 12.5% of capital at 8 slots)
#    ROI 0.10/0.05/0.025/0.012/0.005
#                    = +2.0% / +1.0% / +0.5% / +0.24% / +0.1% price
#    trailing: arms at 0.18 (=3.6% price), trails 0.122 (=2.44% price)
#  This is a tight-stop scalper by design — that IS the validated
#  system. Do not "widen the stop to -35%" expecting old behavior.
# ============================================================

from datetime import datetime
from typing import Optional

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    informative,
    merge_informative_pair,
)


class MeanRevLongOpt(IStrategy):

    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = False

    minimal_roi = {
        "0":   0.10,
        "60":  0.05,
        "180": 0.025,
        "480": 0.012,
        "960": 0.005,
    }

    stoploss = -0.07
    use_custom_stoploss = False

    trailing_stop = True
    trailing_stop_positive = 0.122
    trailing_stop_positive_offset = 0.18
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    startup_candle_count = 300
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    position_adjustment_enable = True
    max_entry_position_adjustment = 1

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 96,
                "trade_limit": 20,
                "stop_duration_candles": 24,
                "max_allowed_drawdown": 0.22,
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
                "trade_limit": 8,
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

    rsi_buy        = IntParameter(20, 45, default=32, space="buy")
    rsi_sell       = IntParameter(60, 80, default=70, space="sell")
    bb_mult        = DecimalParameter(1.8, 2.4, default=2.0, decimals=1, space="buy")
    dca_dip        = DecimalParameter(-0.06, -0.02, default=-0.058, decimals=3, space="buy")
    trend_rsi_min  = IntParameter(35, 55, default=36, space="buy")
    trend_rsi_max  = IntParameter(58, 75, default=58, space="buy")
    min_adx        = IntParameter(15, 30, default=20, space="buy")

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
        return dataframe

    @informative("4h")
    def populate_indicators_4h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema21"]  = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema50"]  = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"]    = ta.RSI(dataframe, timeperiod=14)
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

        # BTC-only regime (4h close > ema50, ema50 > ema200, ema50 sloping up)
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
        regime_ok = (dataframe["btc_regime_up_4h"] == 1)

        bbrsi = (
            regime_ok &
            (dataframe["adx"] >= self.min_adx.value) &
            (dataframe["ema55"] > dataframe["ema200"]) &
            (dataframe["close"] > dataframe["ema200"]) &
            (dataframe["close"] <= dataframe["bb_lower"]) &
            (dataframe["rsi"] < self.rsi_buy.value) &
            (dataframe["volume"] > dataframe["vol_sma20"] * 0.5) &
            (dataframe["volume"] > 0)
        )

        dataframe.loc[bbrsi, "enter_long"] = 1
        dataframe.loc[bbrsi, "enter_tag"]  = "bbrsi"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        exits = (
            (dataframe["close"] >= dataframe["bb_upper"]) |
            (dataframe["rsi"] > self.rsi_sell.value) |
            (
                (dataframe["close"] < dataframe["ema55"]) &
                (dataframe["close"].shift(1) >= dataframe["ema55"].shift(1)) &
                (dataframe["volume"] > dataframe["vol_sma20"])
            )
        )
        dataframe.loc[exits, "exit_long"] = 1
        return dataframe

    def adjust_trade_position(
        self, trade: Trade, current_time: datetime,
        current_rate: float, current_profit: float,
        min_stake: Optional[float], max_stake: float,
        current_entry_rate: float, current_exit_rate: float,
        current_entry_profit: float, current_exit_profit: float,
        **kwargs,
    ) -> Optional[float]:
        if trade.nr_of_successful_entries > 1:
            return None
        # current_profit is the leveraged ratio; -0.058*3 = -17.4% of stake (~-3.5% price at 5x)
        dca_threshold = float(self.dca_dip.value) * 3.0
        if current_profit > dca_threshold:
            return None
        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        if dataframe is None or dataframe.empty:
            return None
        last = dataframe.iloc[-1]
        if int(last.get("btc_regime_up_4h", 0)) != 1:
            return None
        try:
            initial_stake = trade.stake_amount / max(trade.nr_of_successful_entries, 1)
        except Exception:
            initial_stake = trade.stake_amount
        if min_stake is not None and initial_stake < min_stake:
            initial_stake = min_stake
        if initial_stake > max_stake:
            initial_stake = max_stake
        return initial_stake
