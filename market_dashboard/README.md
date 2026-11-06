# 市场情绪 · ETF 资金面板

用 tushare 数据复现视频里的 5 个面板，输出一个独立 HTML（图表用 ECharts CDN，打开时需联网）。

| 面板 | tushare 接口 | 口径 |
|---|---|---|
| 市场体温 | `daily`、`stock_basic` | 五维等权 0–100：上涨家数占比、涨跌中位数（±4%→0/100）、涨停/(涨停+跌停)、成交额÷20 日均额（±50%→0/100）、昨日涨停今日上涨比例 |
| 板块韭菜浓度 | `moneyflow`、`index_member_all`（申万，无权限退回 `stock_basic.industry`） | (小单+中单) 买卖额 ÷ 全档买卖额，按板块加权；竖刻度 = 昨日同口径 |
| 资金流向与指数背离 | `fund_share`、`fund_daily`、`index_daily` | 净申赎 = Δ份额 × 当日收盘价；三个视图：单日 / 累计 + 沪深300 / 单只份额 |
| 固定宽基本轮净申赎 | `fund_share`、`fund_daily` | 本轮累计、近 3 日、月度柱；归因比例 70–90% 为假设值 |
| 成交指纹 | `fund_daily`；尾盘用 `stk_mins` 或 OpenD | 分组成交额今日 vs 昨日；尾盘 = 14:30 后成交占比 |

## 运行

```bash
pip install -r requirements.txt
```

```bash
export TUSHARE_TOKEN=你的token
```

```bash
python build.py --out dashboard.html
```

常用参数：`--date 20261105` 指定交易日；`--round-start 20260928` 指定本轮起点；`--opend` 用本机 OpenD（需 `pip install futu-api` 并启动 OpenD）取尾盘分钟数据；`--demo` 用随机数据预览版式。

## 积分 / 权限

- `fund_share`、`moneyflow` 需要 2000 积分左右；`index_member_all` 要求更高，拿不到时自动退回 `stock_basic.industry`（光伏与锂电都落在「电气设备」，会重叠）。
- `stk_mins` 是单独权限，没有就加 `--opend`，两者都没有时尾盘占比显示「无分钟数据」。
- 当日 80% 以上成分 ETF 份额未披露时，该日记为「待披露」，不填 0。

## 改口径

全部在 `config.py`：ETF 名单（核心五通道 / 宽基十只 / 行业六只 / 沪市 11 只 / 固定 29 只）、板块关键词、归因比例、窗口长度。29 只名单是示例，取不到数据的代码会在日志里告警并被跳过。

视频没公开「韭菜浓度」和「体温」的具体算法，这里的口径是按截图数值量级反推的近似实现。
