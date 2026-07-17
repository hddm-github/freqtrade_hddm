# GitHub Freqtrade 策略项目对比与 NFI 回测指南

更新时间：2026-07-16

本文针对当前项目的目标进行整理：Binance USDT 永续、5 分钟/15 分钟、多交易对筛选、中频日内交易，并兼顾收益、回撤、维护状态和可复现性。排名不是按作者展示的收益率直接比较，因为各项目使用的交易对、年份、手续费、资金规模和杠杆不同。

## 一、综合对比

评分主要考虑：维护活跃度 25%、回测与验证透明度 20%、社区认可度 15%、策略与风险管理完整度 20%、对当前目标的适配度 20%。分数是用于筛选研究优先级的主观综合分，不代表未来收益。

| 排名 | 项目 | 综合分 | 主要周期/思路 | 期货与做空 | 优点 | 主要风险 | 对当前项目的建议 |
|---:|---|---:|---|---|---|---|---|
| 1 | [NostalgiaForInfinity](https://github.com/iterativv/NostalgiaForInfinity) | 86 | 5m 主周期，15m/1h/4h/1d 多周期过滤，多模式、多交易对 | 最新推荐的 X7 支持期货和做空 | 维护活跃、社区规模大、明确建议使用大交易对池、过滤和保护逻辑丰富 | 单文件极其庞大，参数和模式很多；默认 3 倍杠杆；存在加仓、Grinding；难以审计，容易错误配置 | 第一优先级研究。先原版小规模回测，再抽取核心逻辑做精简永续版，不直接实盘 |
| 2 | [TheoBrigitte/freqtrade](https://github.com/TheoBrigitte/freqtrade) | 78 | 收集 BinHV45、Cluc、NFI 衍生策略和多种配置 | 取决于具体策略，多数经典策略原本偏现货做多 | 同时保留回测、Dry-run、交易对列表，并使用 lookahead-analysis 检查 | 是策略集合，不同来源质量差异较大；很多策略需要迁移 | 用作第二候选池，优先测试 BinHV45，并做当前接口和期货适配 |
| 3 | [nateemma/strategies](https://github.com/nateemma/strategies) | 76 | DWT、FFT、Kalman、PCA、神经网络和异常检测 | 取决于具体策略，不能默认认为支持永续双向 | 研究深度高；包含简单基线和复杂模型；作者认为 DWT 系列表现相对较好 | 模型训练、归一化和依赖较复杂；50 个交易对会显著增加资源占用 | 第三候选。先研究 DWT/异常检测作为过滤器，不先上完整神经网络 |
| 4 | [freqtrade/freqtrade-strategies](https://github.com/freqtrade/freqtrade-strategies) | 74 | RSI、EMA、MACD、布林带等传统指标策略 | 大部分是较早的现货/做多示例 | 官方维护、接口参考价值高、适合作为基线 | 仓库展示的许多回测来自 2018 年短区间，不能当成当前收益预期 | 用于接口写法和基准对照，不作为最终主策略 |
| 5 | [Freqtrade Ultimate](https://github.com/titouannwtt/freqtrade-ultimate) | 71 | VWAP、KAC Index、趋势/均值回归，强调 Walk-forward、CPCV、PBO | 面向 Hyperliquid 永续 | 抗过拟合方法、Walk-forward 和回撤验证思路较现代 | 是修改过的 Freqtrade 分叉，主要针对 Hyperliquid；不能保证直接兼容当前 Binance 上游版本 | 借鉴验证方法，不直接替换当前 Freqtrade 引擎 |
| 6 | [BB_RPB_TSL](https://github.com/jilv220/BB_RPB_TSL) | 54 | 5m 布林带、回调抄底、拖尾买入，融合部分 NFI 条件 | 原版偏现货做多 | 历史知名度较高，入场条件有研究价值 | 长期未维护；作者明确提示不要直接实盘、可能对 KuCoin 过拟合、使用动态成交量列表需谨慎 | 只提取个别入场条件用于对照，不部署原版 |
| 7 | [freqtrade-strategies-that-work](https://github.com/paulcpk/freqtrade-strategies-that-work) | 45 | 1h EMA/MACD/RSI 趋势策略 | 偏现货做多 | 简单，容易理解和复现 | 回测集中在 2018—2020 年；不符合当前 5m/15m 中频目标 | 仅作为简单趋势基线 |

## 二、工具类项目（不直接作为策略排名）

| 项目 | 用途 | 建议 |
|---|---|---|
| [GeneTrader](https://github.com/imsatoshi/GeneTrader) | 使用遗传算法生成、交叉、变异并回测 Freqtrade 策略 | 可作为后期参数与逻辑搜索工具；必须配合样本外验证，否则很容易自动寻找出过拟合策略 |
| Freqtrade Hyperopt | 优化策略参数、ROI、止损等 | 优先于引入复杂外部优化器；训练集、验证集、样本外区间必须分开 |

## 三、推荐研究顺序

1. NFI X7 原版：验证多交易对、多周期和不同市场模式的真实表现。
2. BinHV45 现代化版：作为结构简单、容易审计的均值回归候选。
3. DWT 精简版：作为预测型候选，重点验证样本外稳定性。
4. 当前 ETH 极端动量策略：保留为独立逻辑基准。
5. 官方简单策略：作为最低复杂度基线，判断复杂策略是否真的带来增益。

所有候选必须使用相同交易对、时间范围、手续费、资金和最大持仓数比较，至少检查：

- 总收益与年化收益
- 最大回撤和回撤持续时间
- Profit Factor、Expectancy、Sharpe、Sortino
- 每天/每月交易次数
- 多头与空头分别表现
- 每年、每季度和不同市场阶段的一致性
- Lookahead analysis 和 recursive analysis
- 样本外区间表现，而不是只看调参区间

## 四、NFI 能否只复制一个文件直接回测？

### 结论

**复制 `NostalgiaForInfinityX7.py` 后，Freqtrade 可以识别和加载策略；但仅复制这一个文件，还不足以立即完成有意义的回测。**

已在当前项目环境中实际检查：

| 检查项目 | 结果 |
|---|---|
| 当前 Freqtrade | `2026.7-dev` |
| 当前 Python | `3.14.2` |
| NFI 检查版本 | X7 `v17.4.411`，仓库提交 `c0919a4`（2026-07-15） |
| Freqtrade 策略发现 | 成功，`list-strategies` 能识别 `NostalgiaForInfinityX7` |
| `pandas_ta` | 已安装 |
| `rapidjson` | 已安装 |
| `technical` | 已安装 |
| TA-Lib | 已安装 |
| X7 文件规模 | 74,673 行，约 3.19 MB |

因此，当前环境不存在基础 Python 依赖障碍，但仍需补齐配置和数据。

### NFI X7 的关键要求

| 项目 | NFI X7 当前设置/要求 | 影响 |
|---|---|---|
| 主周期 | 5m | 回测命令不要覆盖成 15m |
| 辅助周期 | 15m、1h、4h、1d | 每个交易对都需要这些周期的数据 |
| BTC 市场辅助数据 | BTC 1h、4h、1d | 即使回测其他币，也必须有 BTC 对应数据 |
| 启动 K 线 | 800 根 5m K 线 | 回测起点前至少需要约 67 小时数据，实际还要考虑日线指标预热 |
| 交易对数量 | README 建议 40–80；当前官方成交量配置最终最多 100 个 | 不建议第一次就跑全量三年 |
| 示例最大持仓 | 6 | 与 `stake_amount: unlimited` 配套使用 |
| 期货杠杆 | 默认 3 倍 | 回测结果会显著受杠杆和止损影响 |
| 做空 | 期货/保证金模式下动态启用 `can_short`，包含做空入场条件 | 最新 X7 可以做多和做空 |
| 固定止损字段 | `stoploss = -0.99` | 不能把它理解成普通硬止损；策略依赖内部退出、阈值和仓位管理逻辑 |
| 仓位调整 | 已启用 | 可能发生加仓、再入场或降低风险操作，资金占用不是简单的一次开仓 |
| Grinding/Derisk | 默认启用 | 增加回测复杂度，也增加配置错误和实盘偏差风险 |

### 当前本地数据缺口

当前下载的前 50 个交易对主要有：

- 5m
- 15m
- 1h

但是 NFI X7 还需要 4h 和 1d。检查时，本地 1d 数据为 0，4h 数据也基本没有，因此现在直接运行完整 NFI 回测会缺少辅助周期数据。

另外，当前前 50 成交量列表混入了股票、ETF、商品等新型永续合约。NFI 自带 Binance 黑名单，包含代币化股票、商品、稳定币、低市值币和杠杆代币过滤规则。运行 NFI 时应采用或合并这份黑名单，而不是继续使用未清洗的 `top50_pairs.json`。

## 五、推荐的安全接入流程

### 阶段 1：只验证策略能运行

1. 复制最新版 `NostalgiaForInfinityX7.py` 到 `user_data/strategies/`。
2. 单独创建 NFI 回测配置，不覆盖现有 `config.json` 和 ETH 回测配置。
3. 先选择 BTC、ETH、SOL、XRP、DOGE 等 5–10 个历史数据完整的交易对。
4. 下载 5m、15m、1h、4h、1d 数据。
5. 只回测 1–3 个月，确认没有缺少数据、未来函数、递归指标或配置错误。

### 阶段 2：验证策略质量

1. 扩展到 20 个纯加密货币交易对。
2. 回测至少一个完整牛熊周期。
3. 执行 `lookahead-analysis` 和 `recursive-analysis`。
4. 分开统计多头、空头、入场标签和退出原因。
5. 检查 DCA/Grinding 后的最大实际资金占用。

### 阶段 3：多币种压力测试

1. 使用清洗后的静态 40–50 交易对列表，保证回测可复现。
2. 按年度或季度分段运行，避免一次性占用过多内存。
3. 比较 1 倍和 2 倍，不先使用原版默认 3 倍。
4. 至少运行数周模拟盘后，再讨论是否实盘。

## 六、建议的数据下载形式

NFI 数据至少需要：

```bash
./.venv/bin/python -m freqtrade download-data \
  --config user_data/nfi_backtest.json \
  --pairs-file user_data/nfi_pairs.json \
  --timeframes 5m 15m 1h 4h 1d \
  --timerange 20230701-20260715 \
  --trading-mode futures
```

上述命令中的 `nfi_backtest.json` 和 `nfi_pairs.json` 需要先按 NFI 的 Binance 黑名单和当前项目风险要求生成，不能直接用未清洗的前 50 列表。

## 七、最终建议

- NFI 是当前第一研究对象，但不是可以盲目复制实盘的成品。
- 最新推荐版本应使用 X7，而不是旧的 X/X6。
- 第一次不要使用 40–80 个交易对跑三年全量；先 5–10 个、短区间验证运行正确。
- 不要原样接受 3 倍杠杆、`-0.99` 止损、无限 stake 和仓位调整组合。
- 最终更适合当前项目的方案，是保留 NFI 的市场过滤、暴跌保护、多周期和多条件入场思想，重新实现一个可审计、止损明确、1–2 倍杠杆的精简永续版本。

