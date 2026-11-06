"""数据源适配：tushare（主）、OpenD（可选，尾盘分钟成交）。

所有方法返回统一列名的 DataFrame，单位已换算：
  份额 = 亿份，金额 = 亿元，价格 = 元。
"""
import logging
import time

import pandas as pd

log = logging.getLogger(__name__)


class TushareSource:
    name = "tushare"

    def __init__(self, token: str):
        import tushare as ts
        self.pro = ts.pro_api(token)

    def _call(self, api, **kw):
        for i in range(4):
            try:
                df = getattr(self.pro, api)(**kw)
                return df if df is not None else pd.DataFrame()
            except Exception as e:  # 频控 / 网络抖动
                if i == 3:
                    raise
                log.warning("%s 调用失败(%s)，%ss 后重试", api, e, 2 ** (i + 1))
                time.sleep(2 ** (i + 1))

    # ---------- 日历 ----------
    def trade_days(self, start, end):
        df = self._call("trade_cal", exchange="SSE", start_date=start, end_date=end, is_open="1")
        return sorted(df["cal_date"].astype(str).tolist())

    # ---------- ETF ----------
    def etf_share(self, codes, start, end):
        """ETF 场内份额。fund_share.fd_share 单位万份 → 亿份。"""
        out = []
        for c in codes:
            df = self._call("fund_share", ts_code=c, start_date=start, end_date=end)
            if df.empty:
                log.warning("fund_share 无数据：%s", c)
                continue
            df = df[["ts_code", "trade_date", "fd_share"]].drop_duplicates(["ts_code", "trade_date"])
            df["share"] = df["fd_share"].astype(float) / 1e4
            out.append(df[["ts_code", "trade_date", "share"]])
        return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["ts_code", "trade_date", "share"])

    def etf_daily(self, codes, start, end):
        """ETF 日线。amount 千元 → 亿元。"""
        out = []
        for c in codes:
            df = self._call("fund_daily", ts_code=c, start_date=start, end_date=end)
            if df.empty:
                log.warning("fund_daily 无数据：%s", c)
                continue
            df["amount"] = df["amount"].astype(float) / 1e5
            out.append(df[["ts_code", "trade_date", "close", "amount"]])
        return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["ts_code", "trade_date", "close", "amount"])

    def etf_names(self, codes):
        df = self._call("fund_basic", market="E", fields="ts_code,name")
        m = dict(zip(df["ts_code"], df["name"])) if not df.empty else {}
        return {c: m.get(c, c) for c in codes}

    def index_daily(self, code, start, end):
        df = self._call("index_daily", ts_code=code, start_date=start, end_date=end)
        return df[["trade_date", "close"]].sort_values("trade_date")

    # ---------- 个股 ----------
    def stock_basic(self):
        return self._call("stock_basic", exchange="", list_status="L", fields="ts_code,name,industry,market")

    def sw_members(self):
        """申万 2021 行业成分（需较高积分）。失败返回空表，调用方退回 stock_basic.industry。"""
        try:
            frames, offset = [], 0
            while True:
                df = self._call("index_member_all", is_new="Y", limit=3000, offset=offset)
                if df.empty:
                    break
                frames.append(df)
                if len(df) < 3000:
                    break
                offset += 3000
            if not frames:
                return pd.DataFrame()
            df = pd.concat(frames, ignore_index=True)
            return df[["ts_code", "l1_name", "l2_name", "l3_name"]].drop_duplicates("ts_code")
        except Exception as e:
            log.warning("申万成分不可用(%s)，退回 stock_basic.industry", e)
            return pd.DataFrame()

    def stock_daily(self, date):
        """全市场个股日线：ts_code, pct_chg, amount(亿元)。"""
        df = self._call("daily", trade_date=date, fields="ts_code,trade_date,pct_chg,amount")
        df["amount"] = df["amount"].astype(float) / 1e5
        return df

    def moneyflow(self, date):
        """全市场个股资金流向（万元），四档买卖成交额。"""
        return self._call("moneyflow", trade_date=date)

    # ---------- 分钟 ----------
    def tail_ratio(self, codes, date, tail_start):
        """尾盘成交占比；stk_mins 需单独权限，失败返回 None。"""
        d = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        tail = total = 0.0
        try:
            for c in codes:
                df = self._call("stk_mins", ts_code=c, freq="1min",
                                start_date=f"{d} 09:00:00", end_date=f"{d} 15:01:00")
                if df.empty:
                    return None
                t = df["trade_time"].astype(str).str[11:16]
                total += df["amount"].sum()
                tail += df.loc[t > tail_start, "amount"].sum()
            return tail / total if total else None
        except Exception as e:
            log.warning("stk_mins 不可用(%s)", e)
            return None


class OpenDTail:
    """富途 OpenD：只用来补尾盘分钟成交占比。需本机运行 OpenD 并 pip install futu-api。"""

    def __init__(self, host="127.0.0.1", port=11111):
        self.host, self.port = host, port

    @staticmethod
    def _code(ts_code):
        num, ex = ts_code.split(".")
        return f"{ex}.{num}"

    def tail_ratio(self, codes, date, tail_start):
        try:
            from futu import KLType, OpenQuoteContext, RET_OK
        except ImportError:
            log.warning("未安装 futu-api，跳过 OpenD")
            return None
        d = f"{date[:4]}-{date[4:6]}-{date[6:]}"
        ctx = OpenQuoteContext(host=self.host, port=self.port)
        tail = total = 0.0
        try:
            for c in codes:
                ret, data, _ = ctx.request_history_kline(self._code(c), start=d, end=d,
                                                         ktype=KLType.K_1M, max_count=1000)
                if ret != RET_OK or data.empty:
                    log.warning("OpenD 分钟线失败 %s：%s", c, data)
                    return None
                t = data["time_key"].astype(str).str[11:16]
                total += data["turnover"].sum()
                tail += data.loc[t > tail_start, "turnover"].sum()
            return tail / total if total else None
        finally:
            ctx.close()
