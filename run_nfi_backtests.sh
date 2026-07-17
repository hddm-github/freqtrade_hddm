#!/bin/bash
# NFI X1-X7 回测脚本
# 用法: bash run_nfi_backtests.sh

set -e

STRATEGIES=(
  "NostalgiaForInfinityX"
  "NostalgiaForInfinityX2"
  "NostalgiaForInfinityX3"
  "NostalgiaForInfinityX4"
  "NostalgiaForInfinityX5"
  "NostalgiaForInfinityX6"
  "NostalgiaForInfinityX7"
)

TIMERANGE="20250101-"
CONFIG="user_data/backtest_nfi_config.json"
RESULTS_DIR="user_data/backtest_results"
mkdir -p "$RESULTS_DIR"

echo "========================================="
echo "  NFI X1 ~ X7 回测"
echo "  时间: 2025-01-01 ~ 至今"
echo "  时间框架: 5m (15m/1h/4h/1d 信息框)"
echo "========================================="

for strat in "${STRATEGIES[@]}"; do
  echo ""
  echo "========================================="
  echo "  正在回测: $strat"
  echo "========================================="

  freqtrade backtesting \
    --strategy "$strat" \
    --strategy-path user_data/strategies/ \
    --config "$CONFIG" \
    --timerange "$TIMERANGE" \
    --timeframe 5m \
    --export signals \
    --export-filename "$RESULTS_DIR/backtest-result-$strat"

  echo ""
  echo "  $strat 完成 ✅"
done

echo ""
echo "========================================="
echo "  全部回测完成！"
echo "  结果在: $RESULTS_DIR/"
echo "========================================="
