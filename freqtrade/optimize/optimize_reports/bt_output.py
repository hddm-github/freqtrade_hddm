import logging
import re
from typing import Any, Literal

from rich.text import Text

from freqtrade.constants import UNLIMITED_STAKE_AMOUNT, Config
from freqtrade.ft_types import BacktestResultType
from freqtrade.optimize.optimize_reports.optimize_reports import generate_periodic_breakdown_stats
from freqtrade.util import decimals_per_coin, fmt_coin, print_rich_table


logger = logging.getLogger(__name__)

__EMPTY_LINE = ("", "")

_DISPLAY_VALUE_ZH = {
    "TOTAL": "合计",
    "OTHER": "其他",
    "roi": "收益目标",
    "stop_loss": "止损",
    "stoploss_on_exchange": "交易所止损",
    "trailing_stop_loss": "移动止损",
    "liquidation": "强制平仓",
    "exit_signal": "退出信号",
    "force_exit": "强制退出",
    "emergency_exit": "紧急退出",
    "custom_exit": "自定义退出",
    "partial_exit": "部分退出",
    "sold_on_exchange": "交易所已卖出",
    "trend_pullback_long": "趋势回踩做多",
    "trend_pullback_short": "趋势反弹做空",
    "momentum_exit_long": "多头动量退出",
    "momentum_exit_short": "空头动量退出",
}

_PERIOD_ZH = {
    "day": "日期",
    "week": "周",
    "month": "月份",
    "year": "年份",
    "weekday": "星期",
}


def _display_value(value: Any) -> Any:
    """只转换终端展示值，不修改回测结果 JSON 中的机器字段。"""
    return _DISPLAY_VALUE_ZH.get(value, value)


def _trading_mode_zh(trading_mode: str, margin_mode: str | None) -> str:
    mode = {
        "spot": "现货",
        "margin": "保证金交易",
        "futures": "永续合约",
    }.get(trading_mode, trading_mode)
    margin = {"isolated": "逐仓", "cross": "全仓"}.get(margin_mode or "", "")
    return f"{margin} {mode}".strip()


def _duration_zh(value: Any) -> Any:
    """汉化人类可读的时长文本，不改动结果文件中的原始值。"""
    if value is None:
        return value
    if not isinstance(value, str):
        value = str(value)
    value = re.sub(r"(?<!\w)(-?\d+)\s+days?\b", r"\1 天", value)
    return re.sub(r"(?<!\w)(-?\d+)d\s+", r"\1 天 ", value)


def _get_line_floatfmt(stake_currency: str) -> list[str]:
    """
    Generate floatformat (goes in line with _generate_result_line())
    """
    return ["s", "d", ".2f", f".{decimals_per_coin(stake_currency)}f", ".2f", "d", "s", "s"]


def _get_line_header(
    first_column: str | list[str], stake_currency: str, direction: str = "交易次数"
) -> list[str]:
    """
    Generate header lines (goes in line with _generate_result_line())
    """
    return [
        *([first_column] if isinstance(first_column, str) else first_column),
        direction,
        "平均收益率 %",
        f"累计收益 {stake_currency}",
        "累计收益率 %",
        "平均持仓时长",
        "盈利  持平  亏损  胜率%",
    ]


def generate_wins_draws_losses(wins, draws, losses):
    if wins > 0 and losses == 0:
        wl_ratio = "100"
    elif wins == 0:
        wl_ratio = "0"
    else:
        wl_ratio = f"{100.0 / (wins + draws + losses) * wins:.1f}" if losses > 0 else "100"
    return f"{wins:>4}  {draws:>4}  {losses:>4}  {wl_ratio:>4}"


def text_table_bt_results(
    pair_results: list[dict[str, Any]], stake_currency: str, title: str
) -> None:
    """
    Generates and returns a text table for the given backtest data and the results dataframe
    :param pair_results: List of Dictionaries - one entry per pair + final TOTAL row
    :param stake_currency: stake-currency - used to correctly name headers
    :param title: Title of the table
    """

    headers = _get_line_header("交易对", stake_currency, "交易次数")
    output = [
        [
            _display_value(t["key"]),
            t["trades"],
            t["profit_mean_pct"],
            f"{t['profit_total_abs']:.{decimals_per_coin(stake_currency)}f}",
            t["profit_total_pct"],
            t["duration_avg"],
            generate_wins_draws_losses(t["wins"], t["draws"], t["losses"]),
        ]
        for t in pair_results
    ]
    # Ignore type as floatfmt does allow tuples but mypy does not know that
    print_rich_table(output, headers, summary=title)


def text_table_tags(
    tag_type: Literal["enter_tag", "exit_tag", "mix_tag"],
    tag_results: list[dict[str, Any]],
    stake_currency: str,
) -> None:
    """
    Generates and returns a text table for the given backtest data and the results dataframe
    :param pair_results: List of Dictionaries - one entry per pair + final TOTAL row
    :param stake_currency: stake-currency - used to correctly name headers
    """
    floatfmt = _get_line_floatfmt(stake_currency)
    fallback: str = ""
    is_list = False
    if tag_type == "enter_tag":
        title = "入场标签"
        headers = _get_line_header(title, stake_currency, "入场次数")
    elif tag_type == "exit_tag":
        title = "退出原因"
        headers = _get_line_header(title, stake_currency, "退出次数")
        fallback = "exit_reason"
    else:
        # Mix tag
        title = "入场与退出组合"
        headers = _get_line_header(["入场标签", "退出原因"], stake_currency, "交易次数")
        floatfmt.insert(0, "s")
        is_list = True

    output = [
        [
            *(
                (
                    [_display_value(value) for value in t["key"]]
                    if isinstance(t["key"], list | tuple)
                    else [_display_value(t["key"]), ""]
                    if is_list
                    else [_display_value(t["key"])]
                )
                if t.get("key") is not None and len(str(t["key"])) > 0
                else [_display_value(t.get(fallback, "OTHER"))]
            ),
            t["trades"],
            t["profit_mean_pct"],
            f"{t['profit_total_abs']:.{decimals_per_coin(stake_currency)}f}",
            t["profit_total_pct"],
            t.get("duration_avg"),
            generate_wins_draws_losses(t["wins"], t["draws"], t["losses"]),
        ]
        for t in tag_results
    ]
    # Ignore type as floatfmt does allow tuples but mypy does not know that
    print_rich_table(output, headers, summary=f"{title}统计")


def text_table_periodic_breakdown(
    days_breakdown_stats: list[dict[str, Any]], stake_currency: str, period: str
) -> None:
    """
    Generate small table with Backtest results by days
    :param days_breakdown_stats: Days breakdown metrics
    :param stake_currency: Stakecurrency used
    """
    period_label = _PERIOD_ZH.get(period, period)
    headers = [
        period_label,
        "交易次数",
        f"累计收益 {stake_currency}",
        "盈利因子",
        "盈利  持平  亏损  胜率%",
    ]
    output = [
        [
            d["date"],
            d.get("trades", "无数据"),
            fmt_coin(d["profit_abs"], stake_currency, False),
            round(d["profit_factor"], 2) if "profit_factor" in d else "无数据",
            generate_wins_draws_losses(d["wins"], d["draws"], d.get("losses", d.get("loses", 0))),
        ]
        for d in days_breakdown_stats
    ]
    print_rich_table(output, headers, summary=f"按{period_label}拆分统计")


def text_table_strategy(strategy_results, stake_currency: str, title: str):
    """
    Generate summary table per strategy
    :param strategy_results: Dict of <Strategyname: DataFrame> containing results for all strategies
    :param stake_currency: stake-currency - used to correctly name headers
    """
    headers = _get_line_header("策略", stake_currency, "交易次数")
    # _get_line_header() is also used for per-pair summary. Per-pair drawdown is mostly useless
    # therefore we slip this column in only for strategy summary here.
    headers.append("最大回撤")

    # Align drawdown string on the center two space separator.
    if "max_drawdown_account" in strategy_results[0]:
        drawdown = [f"{t['max_drawdown_account'] * 100:.2f}" for t in strategy_results]
    else:
        # Support for prior backtest results
        drawdown = [f"{t['max_drawdown_per']:.2f}" for t in strategy_results]

    dd_pad_abs = max([len(t["max_drawdown_abs"]) for t in strategy_results])
    dd_pad_per = max([len(dd) for dd in drawdown])
    drawdown = [
        f"{t['max_drawdown_abs']:>{dd_pad_abs}} {stake_currency}  {dd:>{dd_pad_per}}%"
        for t, dd in zip(strategy_results, drawdown, strict=False)
    ]

    output = [
        [
            t["key"],
            t["trades"],
            f"{t['profit_mean_pct']:.2f}",
            f"{t['profit_total_abs']:.{decimals_per_coin(stake_currency)}f}",
            t["profit_total_pct"],
            t["duration_avg"],
            generate_wins_draws_losses(t["wins"], t["draws"], t["losses"]),
            drawdown,
        ]
        for t, drawdown in zip(strategy_results, drawdown, strict=False)
    ]
    print_rich_table(output, headers, summary=title)


def text_table_add_metrics(strat_results: dict) -> None:
    stake = strat_results["stake_currency"]
    if len(strat_results["trades"]) > 0:
        best_trade = max(strat_results["trades"], key=lambda x: x["profit_ratio"])
        worst_trade = min(strat_results["trades"], key=lambda x: x["profit_ratio"])

        short_metrics = (
            [
                __EMPTY_LINE,  # Empty line to improve readability
                (
                    "多头 / 空头交易次数",
                    f"{strat_results.get('trade_count_long', 'total_trades')} / "
                    f"{strat_results.get('trade_count_short', 0)}",
                ),
                (
                    "多头 / 空头收益率 %",
                    f"{strat_results['profit_total_long']:.2%} / "
                    f"{strat_results['profit_total_short']:.2%}",
                ),
                (
                    f"多头 / 空头收益 {stake}",
                    f"{strat_results['profit_total_long_abs']:.{decimals_per_coin(stake)}f} / "
                    f"{strat_results['profit_total_short_abs']:.{decimals_per_coin(stake)}f}",
                ),
            ]
            if strat_results.get("trade_count_short", 0) > 0
            else []
        )

        drawdown_metrics: list[tuple[str | Text, str | Text]] = []
        if "max_relative_drawdown" in strat_results:
            # Compatibility to show old hyperopt results
            drawdown_metrics.append(
                ("账户最大浮亏比例", f"{strat_results['max_relative_drawdown']:.2%}")
            )
        drawdown_account = (
            strat_results["max_drawdown_account"]
            if "max_drawdown_account" in strat_results
            else strat_results["max_drawdown"]
        )
        drawdown_metrics.extend(
            [
                (
                    "绝对回撤",
                    f"{fmt_coin(strat_results['max_drawdown_abs'], stake)} "
                    f"({drawdown_account:.2%})",
                ),
                (
                    "回撤持续时间",
                    _duration_zh(strat_results["drawdown_duration"])
                    if "drawdown_duration" in strat_results
                    else "无数据",
                ),
                (
                    "回撤开始时累计收益",
                    fmt_coin(strat_results["max_drawdown_high"], stake),
                ),
                (
                    "回撤结束时累计收益",
                    fmt_coin(strat_results["max_drawdown_low"], stake),
                ),
                ("回撤开始时间", strat_results["drawdown_start"]),
                ("回撤结束时间", strat_results["drawdown_end"]),
            ]
        )

        entry_adjustment_metrics = (
            [
                ("取消的交易入场", strat_results.get("canceled_trade_entries", "无数据")),
                ("取消的入场订单", strat_results.get("canceled_entry_orders", "无数据")),
                ("替换的入场订单", strat_results.get("replaced_entry_orders", "无数据")),
            ]
            if strat_results.get("canceled_entry_orders", 0) > 0
            else []
        )

        trading_mode = (
            (
                [
                    (
                        "交易模式",
                        _trading_mode_zh(
                            strat_results.get("trading_mode", "spot"),
                            strat_results.get("margin_mode"),
                        ),
                    )
                ]
            )
            if "trading_mode" in strat_results
            else []
        )
        wallet_metrics: list[tuple[str, str]] = [
            (
                "最低/最高余额（已平仓）",
                f"{fmt_coin(strat_results['csum_min'], stake)} / "
                f"{fmt_coin(strat_results['csum_max'], stake)}",
            ),
        ]
        wallet_stats = strat_results.get("wallet_stats", {})
        if wallet_stats:
            drawdown_metrics.extend(
                [
                    __EMPTY_LINE,  # Empty line to improve readability
                    (Text("钱包余额指标", style="bold"), ""),
                    (
                        "最低/最高余额（钱包）",
                        f"{fmt_coin(wallet_stats['low_balance'], stake)} / "
                        f"{fmt_coin(wallet_stats['high_balance'], stake)}",
                    ),
                    (
                        "最低/最高余额日期（钱包）",
                        f"{wallet_stats['low_date']} / {wallet_stats['high_date']}",
                    ),
                ]
            )
            if "max_drawdown_abs" in wallet_stats:
                # Assume that if sharpe is there, all others are there as well.
                drawdown_metrics.extend(
                    [
                        (
                            "账户最大浮亏比例（钱包）",
                            f"{wallet_stats['max_relative_drawdown']:.2%}",
                        ),
                        (
                            "绝对回撤（钱包）",
                            f"{fmt_coin(wallet_stats['max_drawdown_abs'], stake)} "
                            f"({wallet_stats['max_drawdown_account']:.2%})",
                        ),
                        (
                            "回撤持续时间",
                            _duration_zh(wallet_stats["drawdown_duration"])
                            if "drawdown_duration" in wallet_stats
                            else "无数据",
                        ),
                        (
                            "回撤开始时累计收益",
                            fmt_coin(wallet_stats["max_drawdown_high"], stake),
                        ),
                        (
                            "回撤结束时累计收益",
                            fmt_coin(wallet_stats["max_drawdown_low"], stake),
                        ),
                        ("回撤开始时间", wallet_stats["drawdown_start"]),
                        ("回撤结束时间", wallet_stats["drawdown_end"]),
                        (
                            "夏普比率（每日钱包余额）",
                            f"{wallet_stats['sharpe']:.2f}"
                            if wallet_stats and "sharpe" in wallet_stats
                            else "无数据",
                        ),
                        (
                            "索提诺比率（每日钱包余额）",
                            f"{wallet_stats['sortino']:.2f}"
                            if wallet_stats and "sortino" in wallet_stats
                            else "无数据",
                        ),
                        (
                            "卡玛比率（每日钱包余额）",
                            f"{wallet_stats['calmar']:.2f}"
                            if wallet_stats and "calmar" in wallet_stats
                            else "无数据",
                        ),
                    ]
                )

        # Newly added fields should be ignored if they are missing in strat_results. hyperopt-show
        # command stores these results and newer version of freqtrade must be able to handle old
        # results with missing new fields.
        metrics = [
            ("回测开始时间", strat_results["backtest_start"]),
            ("回测结束时间", strat_results["backtest_end"]),
            *trading_mode,
            ("最大同时持仓数", strat_results["max_open_trades"]),
            __EMPTY_LINE,  # Empty line to improve readability
            (
                "总交易次数 / 日均交易次数",
                f"{strat_results['total_trades']} / {strat_results['trades_per_day']}",
            ),
            (
                "初始余额",
                fmt_coin(strat_results["starting_balance"], stake),
            ),
            (
                "最终余额",
                fmt_coin(strat_results["final_balance"], stake),
            ),
            (
                "绝对收益",
                fmt_coin(strat_results["profit_total_abs"], stake),
            ),
            ("总收益率 %", f"{strat_results['profit_total']:.2%}"),
            (
                "年复合增长率（CAGR）%",
                f"{strat_results['cagr']:.2%}" if "cagr" in strat_results else "无数据",
            ),
            (
                "夏普比率（已平仓）",
                f"{strat_results['sharpe']:.2f}" if "sharpe" in strat_results else "无数据",
            ),
            (
                "索提诺比率（已平仓）",
                f"{strat_results['sortino']:.2f}" if "sortino" in strat_results else "无数据",
            ),
            (
                "卡玛比率（已平仓）",
                f"{strat_results['calmar']:.2f}" if "calmar" in strat_results else "无数据",
            ),
            (
                "系统质量指数（SQN）",
                f"{strat_results['sqn']:.2f}" if "sqn" in strat_results else "无数据",
            ),
            (
                "平均收益 p 值",
                (
                    f"{strat_results['p_value']:.4g}"
                    if "p_value" in strat_results
                    else "无数据"
                ),
            ),
            (
                "盈利因子",
                (
                    f"{strat_results['profit_factor']:.2f}"
                    if "profit_factor" in strat_results
                    else "无数据"
                ),
            ),
            (
                "期望收益（比率）",
                (
                    f"{strat_results['expectancy']:.2f} ({strat_results['expectancy_ratio']:.2f})"
                    if "expectancy_ratio" in strat_results
                    else "无数据"
                ),
            ),
            (
                "日均收益",
                fmt_coin(
                    (strat_results["profit_total_abs"] / strat_results["backtest_days"]),
                    stake,
                ),
            ),
            (
                "平均每笔投入",
                fmt_coin(strat_results["avg_stake_amount"], stake),
            ),
            ("同期市场涨跌", f"{strat_results['market_change']:.2%}"),
            (
                "累计交易额",
                fmt_coin(strat_results["total_volume"], stake),
            ),
            *short_metrics,
            __EMPTY_LINE,  # Empty line to improve readability
            (
                "最佳交易对",
                f"{strat_results['best_pair']['key']} "
                f"{strat_results['best_pair']['profit_total']:.2%}",
            ),
            (
                "最差交易对",
                f"{strat_results['worst_pair']['key']} "
                f"{strat_results['worst_pair']['profit_total']:.2%}",
            ),
            ("最佳单笔交易", f"{best_trade['pair']} {best_trade['profit_ratio']:.2%}"),
            ("最差单笔交易", f"{worst_trade['pair']} {worst_trade['profit_ratio']:.2%}"),
            (
                "最佳单日收益",
                fmt_coin(strat_results["backtest_best_day_abs"], stake),
            ),
            (
                "最差单日收益",
                fmt_coin(strat_results["backtest_worst_day_abs"], stake),
            ),
            (
                "盈利 / 持平 / 亏损天数",
                f"{strat_results['winning_days']} / "
                f"{strat_results['draw_days']} / {strat_results['losing_days']}",
            ),
            (
                "盈利交易持仓时长（最短/最长/平均）",
                f"{_duration_zh(strat_results.get('winner_holding_min', '无数据'))} / "
                f"{_duration_zh(strat_results.get('winner_holding_max', '无数据'))} / "
                f"{_duration_zh(strat_results.get('winner_holding_avg', '无数据'))}",
            ),
            (
                "亏损交易持仓时长（最短/最长/平均）",
                f"{_duration_zh(strat_results.get('loser_holding_min', '无数据'))} / "
                f"{_duration_zh(strat_results.get('loser_holding_max', '无数据'))} / "
                f"{_duration_zh(strat_results.get('loser_holding_avg', '无数据'))}",
            ),
            (
                "最大连续盈利 / 亏损次数",
                (
                    (
                        f"{strat_results['max_consecutive_wins']} / "
                        f"{strat_results['max_consecutive_losses']}"
                    )
                    if "max_consecutive_losses" in strat_results
                    else "无数据"
                ),
            ),
            ("被拒绝的入场信号", strat_results.get("rejected_signals", "无数据")),
            (
                "入场 / 退出订单超时次数",
                f"{strat_results.get('timedout_entry_orders', '无数据')} / "
                f"{strat_results.get('timedout_exit_orders', '无数据')}",
            ),
            *entry_adjustment_metrics,
            __EMPTY_LINE,  # Empty line to improve readability
            *wallet_metrics,
            *drawdown_metrics,
        ]
        print_rich_table(metrics, ["指标", "数值"], summary="汇总指标", justify="left")

    else:
        start_balance = fmt_coin(strat_results["starting_balance"], stake)
        stake_amount = (
            fmt_coin(strat_results["stake_amount"], stake)
            if strat_results["stake_amount"] != UNLIMITED_STAKE_AMOUNT
            else "不限额"
        )

        message = (
            "本次回测没有产生交易。"
            f"初始余额为 {start_balance}，"
            f"每笔投入为 {stake_amount}。"
        )
        print(message)


def _show_tag_subresults(results: dict[str, Any], stake_currency: str):
    """
    Print tag subresults (enter_tag, exit_reason_summary, mix_tag_stats)
    """
    if (enter_tags := results.get("results_per_enter_tag")) is not None:
        text_table_tags("enter_tag", enter_tags, stake_currency)

    if (exit_reasons := results.get("exit_reason_summary")) is not None:
        text_table_tags("exit_tag", exit_reasons, stake_currency)

    if (mix_tag := results.get("mix_tag_stats")) is not None:
        text_table_tags("mix_tag", mix_tag, stake_currency)


def show_backtest_result(
    strategy: str, results: dict[str, Any], stake_currency: str, backtest_breakdown: list[str]
):
    """
    Print results for one strategy
    """
    # Print results
    print(f"策略 {strategy} 的回测结果")
    text_table_bt_results(
        results["results_per_pair"], stake_currency=stake_currency, title="回测总览"
    )
    text_table_bt_results(
        results["left_open_trades"], stake_currency=stake_currency, title="回测结束时未平仓交易"
    )

    _show_tag_subresults(results, stake_currency)

    for period in backtest_breakdown:
        if period in results.get("periodic_breakdown", {}):
            days_breakdown_stats = results["periodic_breakdown"][period]
        else:
            days_breakdown_stats = generate_periodic_breakdown_stats(
                trade_list=results["trades"], period=period
            )
        text_table_periodic_breakdown(
            days_breakdown_stats=days_breakdown_stats, stake_currency=stake_currency, period=period
        )

    text_table_add_metrics(results)

    print()


def show_backtest_results(config: Config, backtest_stats: BacktestResultType):
    stake_currency = config["stake_currency"]

    for strategy, results in backtest_stats["strategy"].items():
        show_backtest_result(
            strategy, results, stake_currency, config.get("backtest_breakdown", [])
        )

    if len(backtest_stats["strategy"]) > 0:
        # Print Strategy summary table

        print(
            f"回测区间 {results['backtest_start']} -> {results['backtest_end']} |"
            f" 最大同时持仓数：{results['max_open_trades']}"
        )
        text_table_strategy(
            backtest_stats["strategy_comparison"], stake_currency, "策略对比汇总"
        )


def show_sorted_pairlist(config: Config, backtest_stats: BacktestResultType):
    if config.get("backtest_show_pair_list", False):
        for strategy, results in backtest_stats["strategy"].items():
            print(f"策略 {strategy} 按平均收益排序后的交易对：\n[")
            for result in results["results_per_pair"]:
                if result["key"] != "TOTAL":
                    print(f'"{result["key"]}",  // {result["profit_mean"]:.2%}')
            print("]")
