"""生成市场情绪 & ETF 资金面板 HTML。

用法：
  export TUSHARE_TOKEN=你的token
  python build.py                      # 最新交易日
  python build.py --date 20251105      # 指定日期
  python build.py --opend              # 尾盘分钟数据改用本机 OpenD
  python build.py --demo               # 随机模拟数据，只验证页面
"""
import argparse
import datetime as dt
import json
import logging
import os
import sys
from pathlib import Path

import config as C
import metrics as M

HERE = Path(__file__).parent
log = logging.getLogger("build")


def shift(date, days):
    return (dt.datetime.strptime(date, "%Y%m%d") + dt.timedelta(days=days)).strftime("%Y%m%d")


def month_start(date, back):
    y, m = int(date[:4]), int(date[4:6]) - back
    while m <= 0:
        y, m = y - 1, m + 12
    return f"{y}{m:02d}01"


def build(src, today, tail_src, round_start=None):
    round_start = round_start or C.ROUND_START or shift(today, -C.ROUND_DAYS)
    flow_start = month_start(today, C.FLOW_MONTHS)
    monthly_start = month_start(today, C.MONTHLY_MONTHS - 1)
    start = min(monthly_start, flow_start, round_start)
    cal = src.trade_days(shift(start, -10), today)
    cal = [d for d in cal if d <= today]
    today = cal[-1]
    prev = cal[-2]
    log.info("交易日 %s（前一日 %s）", today, prev)

    # ---- ETF ----
    etfs = sorted(set(C.FIXED_BROAD + C.SH11 + C.BROAD10 + C.INDUSTRY6))
    log.info("拉取 %d 只 ETF 份额与日线", len(etfs))
    share = src.etf_share(etfs, cal[0], today)
    edaily = src.etf_daily(etfs, cal[0], today)
    names = src.etf_names(C.SH11)
    flow_days = [d for d in cal if d >= flow_start]
    idx = src.index_daily(C.DIVERGENCE_INDEX, flow_days[0], today)
    flow = M.flow_panel(share, edaily, C.SH11, flow_days, idx, names)
    rnd = M.round_panel(share, edaily, C.FIXED_BROAD, [d for d in cal if d >= min(monthly_start, round_start)],
                        today, round_start, monthly_start)

    tail_t = tail_src.tail_ratio(C.CORE5, today, C.TAIL_START) if tail_src else None
    tail_p = tail_src.tail_ratio(C.CORE5, prev, C.TAIL_START) if tail_src else None
    fp = M.fingerprint(edaily, today, prev, tail_t, tail_p)

    # ---- 个股：体温 + 浓度 ----
    need = C.TEMP_WINDOW + C.AMOUNT_MA + 2
    stock_days = cal[-need:]
    log.info("拉取 %d 个交易日全市场日线", len(stock_days))
    sd = {}
    for d in stock_days:
        df = src.stock_daily(d)
        if not df.empty:
            sd[d] = df
    basic = src.stock_basic()
    temp_rows = M.temperature(sd, stock_days, basic)

    log.info("拉取资金流向（今日/昨日）")
    mf_t, mf_p = src.moneyflow(today), src.moneyflow(prev)
    sw = src.sw_members()
    mem_t = M.sector_members(basic, sw, M.recent_limit_up(sd, stock_days, basic, today))
    mem_p = M.sector_members(basic, sw, M.recent_limit_up(sd, stock_days, basic, prev))
    conc = M.concentration(mf_t, mf_p if not mf_p.empty else None, mem_t, mem_p)
    temp = M.temperature_panel(temp_rows, conc["market"])

    return {
        "date": f"{today[:4]}-{today[4:6]}-{today[6:]}",
        "date_short": f"{int(today[4:6])}/{int(today[6:])}",
        "source": src.name,
        "sector_source": "申万2021行业" if not sw.empty else "stock_basic.industry",
        "tail_source": getattr(tail_src, "name", "OpenD") if tail_src else "无",
        "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "temp": temp, "conc": conc, "flow": flow, "round": rnd, "fp": fp,
    }


def render(data, out):
    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    Path(out).write_text(tpl.replace("/*__DATA__*/null", payload), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=dt.date.today().strftime("%Y%m%d"))
    ap.add_argument("--out", default="dashboard.html")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--round-start", help="本轮净申赎统计起点 YYYYMMDD")
    ap.add_argument("--opend", action="store_true", help="尾盘分钟数据用 OpenD")
    ap.add_argument("--opend-host", default="127.0.0.1")
    ap.add_argument("--opend-port", type=int, default=11111)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if a.demo:
        from demo import DemoSource
        src = DemoSource()
        tail = src
    else:
        token = os.environ.get("TUSHARE_TOKEN")
        if not token:
            sys.exit("请先设置环境变量 TUSHARE_TOKEN")
        from sources import OpenDTail, TushareSource
        src = TushareSource(token)
        tail = OpenDTail(a.opend_host, a.opend_port) if a.opend else src
    data = build(src, a.date, tail, a.round_start)
    render(data, a.out)
    log.info("已生成 %s", Path(a.out).resolve())


if __name__ == "__main__":
    main()
