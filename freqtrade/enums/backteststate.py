from enum import Enum


class BacktestState(Enum):
    """
    Bot application states
    """

    STARTUP = 1
    DATALOAD = 2
    ANALYZE = 3
    CONVERT = 4
    BACKTEST = 5

    def __str__(self):
        return self.name.lower()

    @property
    def display_name(self) -> str:
        """面向终端用户的中文阶段名称。"""
        return {
            self.STARTUP: "初始化",
            self.DATALOAD: "加载数据",
            self.ANALYZE: "计算指标与信号",
            self.CONVERT: "整理数据",
            self.BACKTEST: "执行回测",
        }[self]

    @classmethod
    def api_value_from_display_name(cls, value: str) -> str:
        """将终端显示名称还原为稳定的 API 阶段标识。"""
        return next((str(state) for state in cls if state.display_name == value), value)
