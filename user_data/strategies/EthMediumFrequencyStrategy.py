"""ETH 永续合约 5m 中高频趋势回踩策略。

设计目标：
- 5m 产生交易信号，1h EMA 趋势用于过滤逆势交易。
- 同时支持做多和做空，默认使用 1 倍杠杆。
- 使用 EMA、RSI、ADX、ATR 和成交量过滤低质量信号。
- 使用反向信号、ROI、固定止损和移动止盈管理退出。

本策略仅用于研究和回测，不构成投资建议。
"""

from pandas import DataFrame
import talib.abstract as ta

from freqtrade.strategy import DecimalParameter, IStrategy, IntParameter, informative
from technical import qtpylib


class EthMediumFrequencyStrategy(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = True
    process_only_new_candles = True
    startup_candle_count = 220

    # 逐步降低收益要求；4 小时后允许接近保本退出，避免中频策略长期占仓。
    minimal_roi = {
        "0": 0.018,
        "30": 0.012,
        "90": 0.006,
        "240": 0.0,
    }

    stoploss = -0.03

    trailing_stop = True
    trailing_stop_positive = 0.007
    trailing_stop_positive_offset = 0.012
    trailing_only_offset_is_reached = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    # 可供 Hyperopt 后续优化的参数。
    entry_adx = IntParameter(15, 35, default=20, space="buy")
    long_rsi_min = IntParameter(38, 52, default=45, space="buy")
    long_rsi_max = IntParameter(58, 72, default=68, space="buy")
    short_rsi_min = IntParameter(28, 42, default=32, space="sell")
    short_rsi_max = IntParameter(48, 62, default=55, space="sell")
    volume_factor = DecimalParameter(0.5, 1.5, default=0.8, decimals=1, space="buy")

    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """1h 只负责判断大级别趋势，不直接产生交易信号。"""
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_9"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)

        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["volume_mean_20"] = dataframe["volume"].rolling(20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 排除几乎不波动和极端波动的 K 线，并要求成交量不显著低于近期均值。
        market_is_tradeable = (
            (dataframe["volume"] > 0)
            & (dataframe["volume"] > dataframe["volume_mean_20"] * self.volume_factor.value)
            & (dataframe["atr_pct"] > 0.001)
            & (dataframe["atr_pct"] < 0.03)
            & (dataframe["adx"] > self.entry_adx.value)
        )

        # 大趋势向上时，等待 5m 回踩 EMA9 后重新站上，避免追高。
        dataframe.loc[
            market_is_tradeable
            & (dataframe["ema_50_1h"] > dataframe["ema_200_1h"])
            & (dataframe["rsi_1h"] > 48)
            & (dataframe["close"] > dataframe["ema_50"])
            & (dataframe["ema_9"] > dataframe["ema_21"])
            & qtpylib.crossed_above(dataframe["close"], dataframe["ema_9"])
            & (dataframe["rsi"] > self.long_rsi_min.value)
            & (dataframe["rsi"] < self.long_rsi_max.value),
            ["enter_long", "enter_tag"],
        ] = (1, "趋势回踩做多")

        # 大趋势向下时，等待反弹至 EMA9 后重新跌破。
        dataframe.loc[
            market_is_tradeable
            & (dataframe["ema_50_1h"] < dataframe["ema_200_1h"])
            & (dataframe["rsi_1h"] < 52)
            & (dataframe["close"] < dataframe["ema_50"])
            & (dataframe["ema_9"] < dataframe["ema_21"])
            & qtpylib.crossed_below(dataframe["close"], dataframe["ema_9"])
            & (dataframe["rsi"] > self.short_rsi_min.value)
            & (dataframe["rsi"] < self.short_rsi_max.value),
            ["enter_short", "enter_tag"],
        ] = (1, "趋势反弹做空")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 快线反向穿越慢线，或 RSI 到达极端区域后开始转弱/转强时退出。
        dataframe.loc[
            (dataframe["volume"] > 0)
            & (
                qtpylib.crossed_below(dataframe["ema_9"], dataframe["ema_21"])
                | ((dataframe["rsi"] > 78) & (dataframe["rsi"] < dataframe["rsi"].shift(1)))
            ),
            ["exit_long", "exit_tag"],
        ] = (1, "多头动量退出")

        dataframe.loc[
            (dataframe["volume"] > 0)
            & (
                qtpylib.crossed_above(dataframe["ema_9"], dataframe["ema_21"])
                | ((dataframe["rsi"] < 22) & (dataframe["rsi"] > dataframe["rsi"].shift(1)))
            ),
            ["exit_short", "exit_tag"],
        ] = (1, "空头动量退出")

        return dataframe

    def leverage(
        self,
        pair: str,
        current_time,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        """默认保持 1 倍杠杆，先验证策略本身，不用杠杆美化收益。"""
        return 1.0

    plot_config = {
        "main_plot": {
            "ema_9": {"color": "#2ecc71"},
            "ema_21": {"color": "#f1c40f"},
            "ema_50": {"color": "#3498db"},
        },
        "subplots": {
            "RSI": {"rsi": {"color": "#9b59b6"}},
            "ADX": {"adx": {"color": "#e67e22"}},
            "ATR %": {"atr_pct": {"color": "#95a5a6"}},
        },
    }
