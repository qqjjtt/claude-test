"""演示数据源：接口与 TushareSource 一致，数据随机生成，只用于验证页面和计算链路。"""
import numpy as np
import pandas as pd

import config as C


class DemoSource:
    name = "demo（随机模拟数据）"

    def __init__(self, seed=7, n_stocks=1500):
        self.rng = np.random.default_rng(seed)
        self.n = n_stocks
        self._basic = None
        self._sw = None
        self._daily_cache = {}

    def trade_days(self, start, end):
        d = pd.bdate_range(pd.to_datetime(start), pd.to_datetime(end))
        return [x.strftime("%Y%m%d") for x in d]

    def _days(self, start, end):
        return self.trade_days(start, end)

    def etf_share(self, codes, start, end):
        days = self._days(start, end)
        out = []
        for c in codes:
            r = np.random.default_rng(abs(hash(c)) % 2**32)
            base = r.uniform(20, 900)
            drift = np.where(np.array(days) >= "20251015", 0.004, 0.0002)
            steps = r.normal(drift, 0.006, len(days))
            share = base * np.exp(np.cumsum(steps))
            out.append(pd.DataFrame({"ts_code": c, "trade_date": days, "share": share}))
        df = pd.concat(out, ignore_index=True)
        # 最后一天深市未披露，模拟「待披露」
        last = days[-1]
        return df[~((df.trade_date == last) & df.ts_code.str.endswith(".SZ"))]

    def etf_daily(self, codes, start, end):
        days = self._days(start, end)
        out = []
        for c in codes:
            r = np.random.default_rng(abs(hash(c + "p")) % 2**32)
            px = r.uniform(1, 5) * np.exp(np.cumsum(r.normal(0.0005, 0.012, len(days))))
            amt = r.uniform(5, 80) * np.exp(r.normal(0, 0.25, len(days)))
            out.append(pd.DataFrame({"ts_code": c, "trade_date": days, "close": px, "amount": amt}))
        return pd.concat(out, ignore_index=True)

    def etf_names(self, codes):
        return {c: c for c in codes}

    def index_daily(self, code, start, end):
        days = self._days(start, end)
        v = 3900 * np.exp(np.cumsum(self.rng.normal(0.0004, 0.009, len(days))))
        return pd.DataFrame({"trade_date": days, "close": v})

    def stock_basic(self):
        if self._basic is None:
            codes = [f"{600000 + i}.SH" if i % 3 else f"{300000 + i}.SZ" for i in range(self.n)]
            self._basic = pd.DataFrame({"ts_code": codes, "name": [f"S{i}" for i in range(self.n)],
                                        "industry": "其他", "market": "主板"})
        return self._basic

    def sw_members(self):
        if self._sw is None:
            kws = [k for s in C.SECTORS for k in s.get("sw", [])]
            b = self.stock_basic()
            l3 = self.rng.choice(kws, len(b))
            self._sw = pd.DataFrame({"ts_code": b.ts_code, "l1_name": "", "l2_name": "", "l3_name": l3})
        return self._sw

    def stock_daily(self, date):
        if date not in self._daily_cache:
            r = np.random.default_rng(int(date))
            b = self.stock_basic()
            mkt = r.normal(0.1, 1.2)
            pct = np.clip(r.normal(mkt, 2.6, len(b)), -10, 10)
            lim = np.where(b.ts_code.str.startswith("300"), 20, 10)
            pct = np.where(r.random(len(b)) < 0.02, lim, pct)
            pct = np.clip(pct, -lim, lim)
            self._daily_cache[date] = pd.DataFrame({
                "ts_code": b.ts_code, "trade_date": date, "pct_chg": pct,
                "amount": r.lognormal(0, 0.8, len(b)) * (1 + mkt / 10)})
        return self._daily_cache[date]

    def moneyflow(self, date):
        r = np.random.default_rng(int(date) + 1)
        b = self.stock_basic()
        sw = self.sw_members().set_index("ts_code")["l3_name"]
        bias = {k: r.normal(0, 0.08) for k in sw.unique()}
        tilt = np.array([bias[sw[c]] for c in b.ts_code])
        tot = r.lognormal(8, 0.8, len(b))
        retail = np.clip(0.62 + tilt + r.normal(0, 0.05, len(b)), 0.3, 0.9)
        df = pd.DataFrame({"ts_code": b.ts_code})
        for side in ("buy", "sell"):
            df[f"{side}_sm_amount"] = tot * retail * 0.5 * 0.5
            df[f"{side}_md_amount"] = tot * retail * 0.5 * 0.5
            df[f"{side}_lg_amount"] = tot * (1 - retail) * 0.5 * 0.6
            df[f"{side}_elg_amount"] = tot * (1 - retail) * 0.5 * 0.4
        return df

    def tail_ratio(self, codes, date, tail_start):
        return float(np.random.default_rng(int(date)).uniform(0.11, 0.18))
