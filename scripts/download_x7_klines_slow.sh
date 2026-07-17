#!/usr/bin/env bash

set -uo pipefail

ROOT_DIR="${ROOT_DIR:-$(pwd)}"
CONFIG="${CONFIG:-user_data/config.json}"
PAIR_FILE="${PAIR_FILE:-user_data/x7-usdt-futures-pairs.txt}"
LOG_DIR="${LOG_DIR:-user_data/logs}"
PAIR_SLEEP="${PAIR_SLEEP:-3}"
BATCH_SLEEP="${BATCH_SLEEP:-60}"
BATCH_SIZE="${BATCH_SIZE:-20}"
CANDLE_TYPES="${CANDLE_TYPES:-futures}"

mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/download_x7_klines_slow_$(date +%Y%m%d_%H%M%S).log"

cd "$ROOT_DIR" || exit 1

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*" | tee -a "$LOG_FILE"
}

if ! command -v freqtrade >/dev/null 2>&1; then
  if [ -x ".venv/bin/freqtrade" ]; then
    FREQTRADE=".venv/bin/freqtrade"
  else
    log "找不到 freqtrade 命令，也找不到 .venv/bin/freqtrade"
    exit 1
  fi
else
  FREQTRADE="freqtrade"
fi

if [ ! -f "$CONFIG" ]; then
  log "找不到配置文件: $CONFIG"
  exit 1
fi

if [ ! -s "$PAIR_FILE" ]; then
  log "生成 Binance USDT 合约交易对列表: $PAIR_FILE"
  "$FREQTRADE" list-pairs \
    --config "$CONFIG" \
    --trading-mode futures \
    --quote USDT \
    -1 \
    > "$PAIR_FILE"
fi

mapfile -t PAIRS < <(grep -E '^[A-Z0-9]+/USDT:USDT$' "$PAIR_FILE" | sort -u)

if [ "${#PAIRS[@]}" -eq 0 ]; then
  log "交易对列表为空，请检查 $PAIR_FILE"
  exit 1
fi

download_timeframe() {
  local timeframe="$1"
  local days="$2"
  local index=0
  local failed=0

  log "开始下载 ${timeframe}, days=${days}, pairs=${#PAIRS[@]}, candle_types=${CANDLE_TYPES}"

  for pair in "${PAIRS[@]}"; do
    index=$((index + 1))
    log "下载 ${timeframe} ${index}/${#PAIRS[@]} ${pair}"

    if "$FREQTRADE" download-data \
      --config "$CONFIG" \
      --trading-mode futures \
      --pairs "$pair" \
      --timeframes "$timeframe" \
      --days "$days" \
      --candle-types "$CANDLE_TYPES" \
      --no-parallel-download \
      >> "$LOG_FILE" 2>&1; then
      log "完成 ${timeframe} ${pair}"
    else
      failed=$((failed + 1))
      log "失败 ${timeframe} ${pair}，继续下一个。详细错误看 $LOG_FILE"
    fi

    sleep "$PAIR_SLEEP"

    if [ $((index % BATCH_SIZE)) -eq 0 ]; then
      log "已处理 ${index} 个交易对，暂停 ${BATCH_SLEEP}s 限流"
      sleep "$BATCH_SLEEP"
    fi
  done

  log "结束下载 ${timeframe}，失败 ${failed} 个"
}

log "日志文件: $LOG_FILE"
log "交易对文件: $PAIR_FILE"
log "限流参数: PAIR_SLEEP=${PAIR_SLEEP}s, BATCH_SIZE=${BATCH_SIZE}, BATCH_SLEEP=${BATCH_SLEEP}s"

download_timeframe 5m 4
download_timeframe 15m 10
download_timeframe 1h 35
download_timeframe 4h 140
download_timeframe 1d 810

log "全部下载任务结束"
