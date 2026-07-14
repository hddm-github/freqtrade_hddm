# Freqtrade 加密货币量化交易框架（中文使用指南）

本仓库是 [Freqtrade](https://www.freqtrade.io/) 的完整源码仓库。Freqtrade 是一个使用 Python 编写的开源加密货币交易机器人，支持历史数据下载、策略开发、回测、参数优化、模拟交易、实盘交易、FreqAI、Web UI、Telegram 和 REST API。

> 风险提示：本项目仅适合学习、研究和自行承担风险的交易实验。回测收益不代表未来收益。新策略必须先回测，再经过足够时间的模拟交易（Dry-run）验证，不要直接投入实盘资金。

## 先看懂这个仓库

这个仓库同时包含两类内容：

- `freqtrade/`：Freqtrade 框架自身的 Python 源码，适合阅读、调试或开发框架功能。
- `user_data/`：用户自己的配置、策略、历史数据、回测结果和交易数据库，日常使用主要操作这里。

当前 `docker-compose.yml` 使用 `freqtradeorg/freqtrade:stable` 官方镜像。因此：

- 修改 `user_data/` 会通过目录挂载立即提供给容器。
- 修改本仓库的 `freqtrade/` 源码不会影响 Compose 中运行的机器人。
- 如果要测试本地框架源码，请使用[本地源码开发](#本地源码开发)，或取消 Compose 中的 `build` 配置注释并构建自定义镜像。

## 主要功能

| 功能 | 作用 | 常用入口 |
| --- | --- | --- |
| 历史数据 | 从交易所下载 K 线、成交数据、合约标记价格和资金费率数据 | `download-data`、`list-data` |
| 策略开发 | 使用指标、入场/出场信号、ROI、止损、仓位管理等描述策略 | `user_data/strategies/*.py` |
| 回测 | 在历史行情上模拟策略表现，统计收益、回撤、胜率和交易明细 | `backtesting`、`backtesting-show` |
| 参数优化 | 使用 Hyperopt 搜索入场、出场、ROI、止损等参数 | `hyperopt` |
| 模拟/实盘 | 使用相同策略进行 Dry-run 前向测试或连接交易所实盘 | `trade` |
| 偏差检查 | 检查未来函数和递归指标偏差 | `lookahead-analysis`、`recursive-analysis` |
| 可视化与控制 | 使用 FreqUI、REST API、Telegram 查看和控制机器人 | `webserver`、`trade` |
| 机器学习 | 使用 FreqAI 训练自适应预测模型 | `freqtrade/freqai/`、`config_examples/config_freqai.example.json` |

## 目录说明

```text
.
├── docker-compose.yml          # 默认 Docker 运行方式
├── freqtrade/                  # Freqtrade 框架源码，不是日常策略目录
├── user_data/
│   ├── config.json             # 机器人配置，首次初始化后生成
│   ├── strategies/             # 自定义策略应放在这里
│   ├── data/                   # 下载的历史行情
│   ├── backtest_results/       # 回测结果
│   ├── hyperopts/              # 自定义 Hyperopt loss 等内容
│   ├── freqaimodels/           # FreqAI 模型
│   └── logs/                   # 运行日志
├── config_examples/            # 现货、合约、FreqAI 等配置示例
├── docs/                       # 项目完整文档源码
├── tests/                      # 框架测试
└── scripts/                    # REST/WebSocket 客户端示例
```

初次克隆时，`user_data/` 通常只有空目录占位文件，需要先生成配置和策略。

## Docker 快速开始（推荐）

以下命令都在仓库根目录执行。

### 1. 拉取镜像并初始化用户目录

```bash
docker compose pull
docker compose run --rm freqtrade create-userdir --userdir user_data
```

### 2. 生成配置

```bash
docker compose run --rm freqtrade new-config --config user_data/config.json
```

该命令会交互式询问交易所、计价币、模拟交易、API 服务等选项。生成后重点检查：

- `dry_run`：初次使用必须为 `true`。
- `exchange.name`：交易所名称。
- `exchange.pair_whitelist`：允许交易的交易对。
- `stake_currency`、`stake_amount`：计价币和每笔资金。
- `max_open_trades`：最大同时持仓数。
- `trading_mode`：`spot` 或 `futures`。
- `api_server`：需要 FreqUI 时启用，并设置强用户名和密码。

可以查看解析后的最终配置：

```bash
docker compose run --rm freqtrade show-config --config user_data/config.json
```

不要把交易所 API Key、Secret、Telegram Token 或带密码的配置提交到 Git。本仓库的 `.gitignore` 默认忽略 `config*.json`。

### 3. 创建策略

```bash
docker compose run --rm freqtrade new-strategy \
  --strategy MyStrategy \
  --template full
```

生成文件位于：

```text
user_data/strategies/MyStrategy.py
```

策略命令使用的是 Python 类名 `MyStrategy`，不只是文件名。默认模板仅用于展示接口，不代表它可以盈利。

`--template` 可选：

- `minimal`：最简骨架，适合从零实现。
- `full`：带常见指标和配置示例。
- `advanced`：包含更多回调和高级能力。

### 4. 让 Compose 使用你的策略

打开 `docker-compose.yml`，把最后一行：

```yaml
--strategy SampleStrategy
```

改为：

```yaml
--strategy MyStrategy
```

如果不修改，`docker compose up` 会继续使用 `create-userdir` 生成的 `SampleStrategy`。它只是接口示例，不应直接用于模拟盘或实盘。

## 策略写在哪里、怎么生效

日常策略必须写在 `user_data/strategies/`，不要写进 `freqtrade/strategy/`。后者是框架的策略接口与加载器源码。

一个策略通常包含：

- `timeframe`：主 K 线周期，例如 `5m`、`15m`、`1h`。
- `populate_indicators()`：计算 RSI、EMA、MACD、布林带等指标。
- `populate_entry_trend()`：产生 `enter_long` / `enter_short` 入场信号。
- `populate_exit_trend()`：产生 `exit_long` / `exit_short` 出场信号。
- `minimal_roi`：持仓时间对应的最低收益退出条件。
- `stoploss`：最大允许亏损。
- `trailing_stop`：可选的移动止损。
- `can_short = True`：合约策略需要做空时启用。
- 自定义回调：动态止损、仓位调整、杠杆、订单价格等高级逻辑。

修改策略文件后：

- 下一次回测会直接加载新代码。
- 正在运行的交易容器需要重启：`docker compose restart freqtrade`。
- 如果修改了策略类名，还要同步修改 `docker-compose.yml` 中的 `--strategy`。

策略计算应使用 pandas 向量化表达式和 `shift()`，不要在回测数据上用 `iloc[-1]` 读取“当前最后一根”，否则容易产生未来函数。

> 版本控制提醒：当前 `.gitignore` 会忽略 `user_data/*` 下的大部分文件，包括新建策略。需要保存策略到 Git 时，可以调整忽略规则，或明确执行 `git add -f user_data/strategies/MyStrategy.py`。不要同时强制提交 `config.json`、数据库、日志和交易所密钥。

## 拉取回测数据

### 方式一：按配置拉取（最常用）

使用 `config.json` 中的交易所、交易模式和白名单交易对：

```bash
docker compose run --rm freqtrade download-data \
  --config user_data/config.json \
  --timeframes 5m 15m 1h \
  --timerange 20250101-
```

`20250101-` 表示从 2025 年 1 月 1 日下载到当前可用时间。再次执行时会保留已有数据并增量补齐。

如果只是日常更新已有交易对，通常不需要再写日期：

```bash
docker compose run --rm freqtrade download-data \
  --config user_data/config.json \
  --timeframes 5m 15m 1h
```

新加入白名单、但还没有历史数据的交易对，可以限制首次下载天数：

```bash
docker compose run --rm freqtrade download-data \
  --config user_data/config.json \
  --timeframes 5m 15m 1h \
  --new-pairs-days 365
```

### 方式二：不依赖配置，明确拉取现货数据

```bash
docker compose run --rm freqtrade download-data \
  --exchange binance \
  --trading-mode spot \
  --pairs BTC/USDT ETH/USDT \
  --timeframes 5m 15m 1h \
  --timerange 20250101-
```

### 方式三：拉取永续合约数据

```bash
docker compose run --rm freqtrade download-data \
  --exchange binance \
  --trading-mode futures \
  --pairs BTC/USDT:USDT ETH/USDT:USDT \
  --timeframes 5m 15m 1h \
  --timerange 20250101-
```

合约交易对使用 `BTC/USDT:USDT` 形式。选择 `futures` 后，Freqtrade 会自动下载回测所需的合约、标记价格和资金费率等 K 线类型。

### 查看本地已有数据

```bash
docker compose run --rm freqtrade list-data \
  --config user_data/config.json \
  --show-timerange
```

历史数据默认保存在 `user_data/data/<exchange>/`，默认格式是 Feather。

### 时间范围写法

| 写法 | 含义 |
| --- | --- |
| `--days 90` | 最近 90 天 |
| `--timerange 20250101-` | 2025-01-01 至今 |
| `--timerange 20250101-20250630` | 固定区间 |
| `--prepend --timerange 20240101-20250101` | 向已有数据前方补更早历史 |

谨慎使用 `--erase`，它会先删除所选范围对应的已有数据。策略如果使用 5 分钟主周期和 1 小时/4 小时 informative 周期，所有这些周期都要下载。还要为 `startup_candle_count` 预留足够的前置 K 线。

## 如何回测一个策略

假设策略类名为 `MyStrategy`，主周期为 `5m`，先确认已经下载对应交易对和周期的数据，然后执行：

```bash
docker compose run --rm freqtrade backtesting \
  --config user_data/config.json \
  --strategy MyStrategy \
  --timeframe 5m \
  --timerange 20250101-20250630 \
  --dry-run-wallet 1000 \
  --export trades \
  --breakdown month
```

临时只回测指定交易对：

```bash
docker compose run --rm freqtrade backtesting \
  --config user_data/config.json \
  --strategy MyStrategy \
  --pairs BTC/USDT ETH/USDT \
  --timeframe 5m \
  --timerange 20250101-20250630 \
  --cache none
```

合约配置中的交易对要写为 `BTC/USDT:USDT`。`--cache none` 适合频繁修改策略后强制重新计算；正常使用可以省略。

对比多个策略：

```bash
docker compose run --rm freqtrade backtesting \
  --config user_data/config.json \
  --strategy-list StrategyA StrategyB StrategyC \
  --timeframe 5m \
  --timerange 20250101-20250630
```

回测结果默认写入 `user_data/backtest_results/`。查看某个已保存结果：

```bash
docker compose run --rm freqtrade backtesting-show \
  --config user_data/config.json \
  --backtest-filename backtest-result.json \
  --show-pair-list \
  --breakdown month
```

把 `backtest-result.json` 换成 `user_data/backtest_results/` 中的实际结果文件名。

### 回测重点看什么

不要只看 `Total profit`，至少同时检查：

- 总收益和年化收益。
- 最大绝对/相对回撤。
- 交易次数是否足够，是否只依赖少数偶然交易。
- 胜率、盈亏比、平均持仓时间。
- 不同交易对、月份和多空方向是否稳定。
- 手续费、滑点、最小下单量是否符合真实交易条件。
- 训练区间之外的样本外数据是否仍然有效。

回测通常按下一根 K 线成交，无法完全复现盘口深度、网络延迟和实盘滑点。回测结果好只是继续验证的起点。

## 回测前的策略质量检查

检查未来函数：

```bash
docker compose run --rm freqtrade lookahead-analysis \
  --config user_data/config.json \
  --strategy MyStrategy \
  --timeframe 5m \
  --timerange 20250101-20250630
```

检查递归指标偏差：

```bash
docker compose run --rm freqtrade recursive-analysis \
  --config user_data/config.json \
  --strategy MyStrategy \
  --timeframe 5m \
  --timerange 20250101-20250630
```

策略进入模拟盘或实盘前，建议两项都执行。

## Hyperopt 参数优化

只有使用 `IntParameter`、`DecimalParameter`、`CategoricalParameter` 等声明为可优化的参数，Hyperopt 才能搜索对应空间。

```bash
docker compose run --rm freqtrade hyperopt \
  --config user_data/config.json \
  --strategy MyStrategy \
  --timeframe 5m \
  --timerange 20250101-20250630 \
  --spaces buy sell roi stoploss trailing \
  --hyperopt-loss MultiMetricHyperOptLoss \
  --epochs 200 \
  --random-state 42 \
  --min-trades 50
```

优化结果好不等于策略可靠。应使用独立的样本外时间段重新回测，避免反复调参造成过拟合。

## 启动模拟交易和 FreqUI

启动前确认：

1. `user_data/config.json` 中 `dry_run` 为 `true`。
2. 白名单、计价币、每笔金额和最大持仓数正确。
3. `docker-compose.yml` 中 `--strategy` 指向你的策略类名。
4. 策略已完成回测、偏差检查，并准备好所需启动 K 线。

启动：

```bash
docker compose up -d
```

查看状态和日志：

```bash
docker compose ps
docker compose logs -f freqtrade
```

持久日志位于 `user_data/logs/freqtrade.log`，模拟/实盘交易数据库默认位于 `user_data/tradesv3.sqlite`。

如果生成配置时启用了 API/FreqUI，可以访问：

```text
http://127.0.0.1:8080
```

当前 Compose 只把 8080 端口绑定到本机回环地址，这是更安全的默认值。远程服务器不要直接把 FreqUI 暴露到公网，建议通过 SSH 隧道或 VPN 访问。

停止并移除容器：

```bash
docker compose down
```

### 从模拟盘切换到实盘

实盘前需要配置只具备必要交易权限、禁止提币的交易所 API Key，并将 `dry_run` 改为 `false`。切换会使用真实资金，修改后应再次检查完整配置、当前余额、策略、交易对、杠杆、止损和最大持仓数，再重启容器。

## 本地源码开发

如果目的是修改和调试本仓库的 `freqtrade/` 框架源码，而不是只开发用户策略：

```bash
./setup.sh --install
source .venv/bin/activate
python -m freqtrade --version
```

之后可把前文命令中的：

```text
docker compose run --rm freqtrade
```

替换成：

```text
python -m freqtrade
```

例如：

```bash
python -m freqtrade backtesting \
  --config user_data/config.json \
  --strategy MyStrategy \
  --timerange 20250101-20250630
```

运行测试：

```bash
python -m pytest
```

Compose 默认使用官方镜像，因此本地源码修改不要只用 `docker compose restart` 验证。

## 常用命令速查

| 目标 | 命令 |
| --- | --- |
| 生成配置 | `docker compose run --rm freqtrade new-config --config user_data/config.json` |
| 创建策略 | `docker compose run --rm freqtrade new-strategy --strategy MyStrategy` |
| 列出策略 | `docker compose run --rm freqtrade list-strategies --config user_data/config.json` |
| 拉取历史数据 | `docker compose run --rm freqtrade download-data --config user_data/config.json --timeframes 5m 1h --days 365` |
| 查看数据范围 | `docker compose run --rm freqtrade list-data --config user_data/config.json --show-timerange` |
| 回测 | `docker compose run --rm freqtrade backtesting --config user_data/config.json --strategy MyStrategy --timerange 20250101-20250630` |
| 参数优化 | `docker compose run --rm freqtrade hyperopt --config user_data/config.json --strategy MyStrategy --epochs 100` |
| 启动机器人 | `docker compose up -d` |
| 查看日志 | `docker compose logs -f freqtrade` |
| 重启机器人 | `docker compose restart freqtrade` |
| 停止机器人 | `docker compose down` |

## 常见问题

### `Impossible to load Strategy 'MyStrategy'`

检查以下内容：

- 文件是否在 `user_data/strategies/` 且扩展名为 `.py`。
- `--strategy` 使用的是类名，大小写完全一致。
- 策略导入的第三方依赖是否存在于官方镜像。
- 用 `list-strategies` 查看加载错误。

### 回测提示没有数据

交易所、交易模式、交易对格式、时间周期和时间范围必须与下载数据时一致。现货 `BTC/USDT` 与合约 `BTC/USDT:USDT` 是两套不同数据。

### 修改策略后机器人没有变化

回测命令会重新加载策略；常驻交易容器需要执行：

```bash
docker compose restart freqtrade
```

### 为什么本地修改 `freqtrade/` 后 Docker 中没有变化

因为 `docker-compose.yml` 使用预构建的官方 `stable` 镜像，只挂载了 `./user_data`。本地框架开发请用 Python 源码方式运行，或者构建自定义 Docker 镜像。

### 下载数据时出现权限错误

容器创建的文件可能属于容器用户。Linux 上可以把 `user_data` 所有权调整为当前用户：

```bash
sudo chown -R "$UID:$GID" user_data
```

## 进一步阅读

- [Freqtrade 官方文档](https://www.freqtrade.io/)
- [Docker 快速开始](https://www.freqtrade.io/en/stable/docker_quickstart/)
- [策略开发](https://www.freqtrade.io/en/stable/strategy-customization/)
- [历史数据下载](https://www.freqtrade.io/en/stable/data-download/)
- [回测](https://www.freqtrade.io/en/stable/backtesting/)
- [Hyperopt](https://www.freqtrade.io/en/stable/hyperopt/)
- [FreqAI](https://www.freqtrade.io/en/stable/freqai/)
- [交易所特别说明](https://www.freqtrade.io/en/stable/exchanges/)

## 许可证

Freqtrade 使用 GPLv3 许可证。详见 [LICENSE](LICENSE)。
