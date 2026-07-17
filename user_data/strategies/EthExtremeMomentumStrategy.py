"""ETH/USDT 永续合约 15 分钟极端动量策略。

核心逻辑：
1. 8 小时涨幅首次越过 5% 时顺势做多。
2. UTC 13:00—16:59 内，16 小时跌幅首次越过 2.5% 时顺势做空。
3. 每笔交易最多持有 6 小时，硬止损为 5%，固定使用 1 倍杠杆。

阈值使用已经收盘的 K 线计算，crossed_above/crossed_below 只在首次越界时
发出信号，避免同一段行情反复追单。策略仅用于研究和模拟交易，不构成投资建议。
"""

from datetime import timedelta

from pandas import DataFrame
import talib.abstract as ta

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy
from technical import qtpylib


class EthExtremeMomentumStrategy(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "15m"
    can_short = True
    process_only_new_candles = True
    startup_candle_count = 240

    # 禁用常规 ROI 提前退出，由 custom_exit 在六小时后统一平仓。
    minimal_roi = {"0": 100.0}
    stoploss = -0.05
    trailing_stop = False
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

    long_momentum_threshold = 0.050
    short_momentum_threshold = -0.025
    short_entry_utc_hours = (13, 14, 15, 16)
    hold_minutes = 360

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["return_8h"] = dataframe["close"].pct_change(32)
        dataframe["return_16h"] = dataframe["close"].pct_change(64)
        dataframe["atr_pct"] = ta.ATR(dataframe, timeperiod=14) / dataframe["close"]
        dataframe["utc_hour"] = dataframe["date"].dt.hour
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        market_is_tradeable = (
            (dataframe["volume"] > 0)
            & (dataframe["atr_pct"] > 0.0015)
            & (dataframe["atr_pct"] < 0.030)
        )

        dataframe.loc[
            market_is_tradeable
            & qtpylib.crossed_above(
                dataframe["return_8h"], self.long_momentum_threshold
            ),
            ["enter_long", "enter_tag"],
        ] = (1, "八小时极端上涨延续")

        dataframe.loc[
            market_is_tradeable
            & dataframe["utc_hour"].isin(self.short_entry_utc_hours)
            & qtpylib.crossed_below(
                dataframe["return_16h"], self.short_momentum_threshold
            ),
            ["enter_short", "enter_tag"],
        ] = (1, "欧美时段极端下跌延续")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 实际退出由 custom_exit 的固定持仓时间以及 stoploss 控制。
        return dataframe

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        if current_time - trade.open_date_utc >= timedelta(minutes=self.hold_minutes):
            return "六小时到期退出"
        return None

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
        return 1.0

    plot_config = {
        "subplots": {
            "区间涨跌幅": {
                "return_8h": {"color": "#2ecc71"},
                "return_16h": {"color": "#e74c3c"},
            },
            "ATR 占比": {"atr_pct": {"color": "#3498db"}},
        }
    }
