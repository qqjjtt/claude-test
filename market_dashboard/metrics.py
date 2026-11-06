"""把原始数据算成面板需要的指标。纯函数，不做 IO。"""
import math

import numpy as np
import pandas as pd

import config as C


def _num(x, nd=2):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(float(x), nd)


def _int(x):
    v = _num(x, 0)
    return None if v is None else int(v)


# ======================= ETF 净申赎 =======================
def etf_net_flow(share, daily):
    """逐日净申赎(亿元) = Δ份额(亿份) × 当日收盘价。缺值保持 NaN，不填 0。"""
    sh = share.pivot_table(index="trade_date", columns="ts_code", values="share").sort_index()
    px = daily.pivot_table(index="trade_date", columns="ts_code", values="close").sort_index()
    px = px.reindex(index=sh.index, columns=sh.columns)
    return sh.diff() * px, sh


def flow_panel(share, daily, codes, days, idx, names):
    """「资金流向与指数背离」面板：单日 / 累计 / 单只份额 三个视图。"""
    s = share[share.ts_code.isin(codes)]
    d = daily[daily.ts_code.isin(codes)]
    net, sh = etf_net_flow(s, d)
    net = net.reindex(days)
    daily_sum = net.sum(axis=1, min_count=1)
    # 当日有任一只份额缺失 → 视为未披露完整，置空
    complete = net.notna().sum(axis=1) >= max(1, int(0.8 * len(net.columns)))
    daily_sum[~complete] = np.nan
    cum = daily_sum.fillna(0).cumsum().where(daily_sum.notna())
    idx = idx.set_index("trade_date")["close"].reindex(days)
    shares = {names.get(c, c): [_num(v) for v in sh.reindex(days)[c]] for c in sh.columns}
    return {
        "dates": [f"{x[4:6]}-{x[6:]}" for x in days],
        "daily": [_num(v) for v in daily_sum],
        "cum": [_num(v) for v in cum],
        "index": [_num(v) for v in idx],
        "index_name": "沪深300",
        "shares": shares,
        "count": int(len(net.columns)),
    }


def round_panel(share, daily, codes, days, today, round_start, monthly_start):
    """「29 只固定宽基本轮逐日净申赎」：本轮累计、近三日单日、月度柱。"""
    s = share[share.ts_code.isin(codes)]
    d = daily[daily.ts_code.isin(codes)]
    net, _ = etf_net_flow(s, d)
    net = net.reindex(days)
    n_codes = len(net.columns)
    daily_sum = net.sum(axis=1, min_count=1)
    complete = net.notna().sum(axis=1) >= max(1, int(0.8 * n_codes))
    daily_sum[~complete] = np.nan

    rnd = daily_sum[daily_sum.index >= round_start]
    disclosed = rnd.dropna()
    total = disclosed.sum()
    lo, hi = total * C.ATTRIBUTION[0], total * C.ATTRIBUTION[1]

    last3 = [x for x in days if x <= today][-3:]
    cards = [{"label": f"{int(x[4:6])}/{int(x[6:])} 单日",
              "value": _num(daily_sum.get(x))} for x in last3[::-1]]

    m = daily_sum[daily_sum.index >= monthly_start]
    months = []
    for ym, grp in m.groupby(m.index.str[:6]):
        months.append({"label": f"{int(ym[4:])}月", "days": int(len(grp)),
                       "value": _num(grp.sum(min_count=1), 0)})
    return {
        "count": n_codes,
        "start": disclosed.index.min() if len(disclosed) else None,
        "end": disclosed.index.max() if len(disclosed) else None,
        "total": _num(total),
        "attr_lo": _num(lo, 0), "attr_hi": _num(hi, 0), "attr_mid": _num((lo + hi) / 2, 0),
        "attr_pct": [int(C.ATTRIBUTION[0] * 100), int(C.ATTRIBUTION[1] * 100)],
        "cards": cards,
        "months": months,
    }


# ======================= 成交指纹 =======================
def fingerprint(daily, today, prev, tail_today, tail_prev):
    a = daily.pivot_table(index="trade_date", columns="ts_code", values="amount")
    groups = [("核心五通道", C.CORE5), ("宽基十只", C.BROAD10),
              ("行业对照六只", C.INDUSTRY6), ("全部十六只", C.BROAD10 + C.INDUSTRY6)]
    rows = []
    for name, codes in groups:
        cols = [c for c in codes if c in a.columns]
        t = a.loc[today, cols].sum(min_count=1) if today in a.index else np.nan
        p = a.loc[prev, cols].sum(min_count=1) if prev in a.index else np.nan
        ratio = t / p if p and not np.isnan(p) else np.nan
        rows.append({"name": f"{name}（{len(cols)} 只）" if name == "核心五通道" else name,
                     "short": name, "today": _num(t), "prev": _num(p),
                     "chg": _int((ratio - 1) * 100), "ratio": _int(ratio * 100)})
    r = {x["short"]: x for x in rows}
    broad, ind, core = r["宽基十只"]["chg"], r["行业对照六只"]["chg"], r["核心五通道"]["chg"]
    if broad is not None and ind is not None:
        if broad < -10 and ind > 0:
            text = (f"宽基通道明显降温、行业 ETF 反而 {ind:+d}%——托底的钱在收手，进攻的钱在换标的。"
                    "但成交降温 ≠ 净赎回，方向要等份额回填才能定。")
        elif broad > 10 and ind < 0:
            text = f"宽基放量 {broad:+d}%、行业 ETF 缩量——资金往宽基集中，留意托底/护盘迹象，待份额确认。"
        elif broad > 10 and ind > 10:
            text = f"宽基 {broad:+d}%、行业 {ind:+d}% 同步放量——整体活跃度上升，结合份额判断是申购还是换手。"
        elif broad < -10 and ind < -10:
            text = f"宽基 {broad:+d}%、行业 {ind:+d}% 同步缩量——ETF 通道整体降温，观望为主。"
        else:
            text = f"宽基 {broad:+d}%、行业 {ind:+d}%，变化不大，无明显方向。"
        headline = f"{broad:+d}%"
        sub = f"核心五通道 {core:+d}%" if core is not None else ""
    else:
        text, headline, sub = "数据不足，无法比较。", "—", ""
    above = [x["short"] for x in rows if x["ratio"] and x["ratio"] > 100]
    foot = ("只有" + "、".join(above) + "越过了 100%，其余全部低于 100%。") if above else "四组全部低于 100%。"
    return {"rows": rows, "tail_today": _num(tail_today * 100 if tail_today else None),
            "tail_prev": _num(tail_prev * 100 if tail_prev else None),
            "headline": headline, "sub": sub, "text": text, "foot": foot}


# ======================= 涨停 / 体温 =======================
def _limit_pct(code, name):
    if isinstance(name, str) and "ST" in name.upper():
        return 5.0
    if code.startswith(("300", "301", "688", "689")):
        return 20.0
    return 10.0


def tag_limits(df, basic):
    """标记涨停 / 跌停（按涨跌幅近似，北交所剔除）。"""
    df = df[~df.ts_code.str.endswith(".BJ")].copy()
    names = basic.set_index("ts_code")["name"] if not basic.empty else pd.Series(dtype=str)
    lim = np.array([_limit_pct(c, names.get(c)) for c in df.ts_code])
    df["lu"] = df["pct_chg"].astype(float) >= lim - 0.2
    df["ld"] = df["pct_chg"].astype(float) <= -(lim - 0.2)
    return df


def temperature(stock_daily, days, basic):
    """五维体温，每维 0–100，等权平均：
    1 上涨家数占比  2 涨跌幅中位数(±4% 映射到 0/100)  3 涨停/(涨停+跌停)
    4 成交额 ÷ 20 日均额(±50% 映射到 0/100)  5 昨日涨停今日上涨比例(赚钱效应)
    """
    rows, amounts = [], []
    tagged = {d: tag_limits(stock_daily[d], basic) for d in days if d in stock_daily}
    for i, d in enumerate(days):
        if d not in tagged:
            continue
        df = tagged[d]
        pct = df["pct_chg"].astype(float)
        amt = df["amount"].sum()
        amounts.append(amt)
        up = (pct > 0).mean() * 100
        med = float(np.clip(50 + pct.median() * 12.5, 0, 100))
        lu, ld = int(df.lu.sum()), int(df.ld.sum())
        lim = lu / (lu + ld) * 100 if lu + ld else 50.0
        hist = amounts[-C.AMOUNT_MA - 1:-1]
        vol = float(np.clip(50 + (amt / np.mean(hist) - 1) * 100, 0, 100)) if len(hist) >= 5 else None
        prev = days[i - 1] if i > 0 else None
        if prev in tagged:
            yl = set(tagged[prev].loc[tagged[prev].lu, "ts_code"])
            sub = df[df.ts_code.isin(yl)]
            earn = (sub["pct_chg"].astype(float) > 0).mean() * 100 if len(sub) else 50.0
        else:
            earn = None
        dims = [up, med, lim, vol, earn]
        if any(x is None for x in dims):
            continue
        rows.append({"date": d, "score": float(np.mean(dims)), "dims": dims, "lu": lu, "ld": ld})
    return rows


def temperature_panel(rows, market_conc_today):
    rows = rows[-C.TEMP_WINDOW:]
    if not rows:
        return None
    s = pd.Series([r["score"] for r in rows], index=[r["date"] for r in rows])
    today, prev = s.iloc[-1], (s.iloc[-2] if len(s) > 1 else np.nan)
    mean = s.mean()
    rank = int((s > today).sum() + 1)
    beat = (s < today).sum() / max(1, len(s) - 1) * 100
    imax, imin = s.idxmax(), s.idxmin()
    six = (today * 5 + market_conc_today) / 6 if market_conc_today is not None else None
    diff = today - prev
    move = "几乎没动" if abs(diff) < 2 else ("明显升温" if diff > 0 else "明显降温")
    dev = today - mean
    mood = "明显偏热" if dev > 15 else "偏热" if dev > 5 else "明显偏冷" if dev < -15 else "偏冷" if dev < -5 else "接近均值"
    names = ["上涨家数", "涨跌中位数", "涨停/跌停", "量能", "赚钱效应"]
    fmt = lambda d: f"{int(d[4:6])}/{int(d[6:])}"
    return {
        "today": _num(today, 1), "prev": _num(prev, 1), "diff": _num(diff, 1), "move": move,
        "six": _num(six, 1), "mean": _num(mean, 1), "dev": _num(dev, 1), "mood": mood,
        "rank": rank, "n": len(s), "beat": int(round(beat)),
        "max": _num(s.max(), 1), "max_date": fmt(imax), "min": _num(s.min(), 1), "min_date": fmt(imin),
        "dates": [fmt(d) for d in s.index], "scores": [_num(v, 1) for v in s],
        "dims": [{"name": n, "value": _num(v, 1)} for n, v in zip(names, rows[-1]["dims"])],
        "lu": rows[-1]["lu"], "ld": rows[-1]["ld"],
        "range": f"{fmt(s.index[0])}—{fmt(s.index[-1])}",
    }


# ======================= 韭菜浓度 =======================
def _retail_share(mf):
    lv = ["sm", "md", "lg", "elg"]
    cols = {l: [f"buy_{l}_amount", f"sell_{l}_amount"] for l in lv}
    mf = mf.copy()
    mf["retail"] = sum(mf[c].astype(float) for l in C.RETAIL_LEVELS for c in cols[l])
    mf["total"] = sum(mf[c].astype(float) for l in lv for c in cols[l])
    return mf[["ts_code", "retail", "total"]]


def sector_members(basic, sw, recent_lu):
    """返回 {板块名: set(ts_code)}。"""
    out = {}
    if not sw.empty:
        lab = sw.set_index("ts_code")[["l1_name", "l2_name", "l3_name"]].fillna("").astype(str)
        lab = lab.apply(lambda col: col.str.replace("Ⅱ", "").str.replace("Ⅲ", ""))
        text = lab["l1_name"] + "|" + lab["l2_name"] + "|" + lab["l3_name"]
    for sec in C.SECTORS:
        if sec.get("special") == "recent_limit_up":
            out[sec["name"]] = set(recent_lu)
            continue
        if not sw.empty:
            mask = text.apply(lambda t: any(k in t for k in sec["sw"]))
            out[sec["name"]] = set(text[mask].index)
        else:
            out[sec["name"]] = set(basic.loc[basic.industry.isin(sec["basic"]), "ts_code"])
    return out


def concentration(mf_today, mf_prev, members_today, members_prev):
    a = _retail_share(mf_today).set_index("ts_code")
    b = _retail_share(mf_prev).set_index("ts_code") if mf_prev is not None else None
    market = a["retail"].sum() / a["total"].sum() * 100
    rows = []
    for sec in C.SECTORS:
        name = sec["name"]
        codes = [c for c in members_today.get(name, ()) if c in a.index]
        if not codes:
            continue
        v = a.loc[codes, "retail"].sum() / a.loc[codes, "total"].sum() * 100
        pv = None
        if b is not None:
            pc = [c for c in members_prev.get(name, ()) if c in b.index]
            if pc:
                pv = b.loc[pc, "retail"].sum() / b.loc[pc, "total"].sum() * 100
        rows.append({"name": name, "icon": sec["icon"], "n": len(codes), "today": _num(v),
                     "prev": _num(pv), "chg": _num(v - pv) if pv is not None else None})
    rows.sort(key=lambda r: -r["today"])
    # 颜色分三档：前 1/3 红、中 1/3 橙、后 1/3 蓝
    n = len(rows)
    for i, r in enumerate(rows):
        r["tier"] = "hot" if i < n / 3 else ("warm" if i < 2 * n / 3 else "cool")
    return {"rows": rows, "market": _num(market)}


def recent_limit_up(stock_daily, days, basic, today):
    window = [d for d in days if d <= today][-C.RECENT_LIMIT_UP_DAYS:]
    codes = set()
    for d in window:
        if d in stock_daily:
            t = tag_limits(stock_daily[d], basic)
            codes |= set(t.loc[t.lu, "ts_code"])
    return codes
