#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""產生 data/holidays.json：澳門公眾假期、公務員補假、特許假期。

- 2026、2027：使用《澳門特別行政區公報》已刊佈的官方日期表（來源標 official）。
- 其他年份：依《第 60/2000 號行政命令》的 20 天公眾假期，加上「補假規則」推算（來源標 inferred）。

補假規則（公共行政工作人員，經 2026/2027 官方日期表逐條校驗）：
  公眾假期碰上星期六或星期日 → 順延至之後第一個「平日」；
  該平日若已是公眾假期或已被其他補假佔用 → 再往後顺延，如此類推。

需要依賴：cnlunar（農曆 + 二十四氣）。僅在新增年份資料時執行，
GitHub Action 的定時任務不需要跑這個腳本。

    pip install cnlunar==0.2.5
    python3 scripts/build_holidays.py --start 2024 --end 2035
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

import cnlunar
from cnlunar import solar24

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "holidays.json")

SHORT = {
    "元旦": "元旦",
    "農曆正月初一": "初一",
    "農曆正月初二": "初二",
    "農曆正月初三": "初三",
    "耶穌受難日": "受難日",
    "復活節前日": "復活前",
    "清明節": "清明",
    "勞動節": "勞動節",
    "佛誕節": "佛誕",
    "端午節": "端午",
    "中秋節翌日": "中秋翌",
    "中華人民共和國國慶日": "國慶",
    "中華人民共和國國慶日翌日": "國慶翌",
    "重陽節": "重陽",
    "追思節": "追思節",
    "聖母無原罪瞻禮": "無原罪",
    "澳門特別行政區成立紀念日": "回歸日",
    "冬至": "冬至",
    "聖誕節前日": "平安夜",
    "聖誕節": "聖誕",
    "農曆除夕": "除夕",
    "除夕": "除夕",
}

# 公報已刊佈的官方日期表：(日期, 名稱, 類別)  類別 P=公眾假期 C=補假 T=特許假期(下午)
OFFICIAL = {
    2026: [
        ("2026-01-01", "元旦", "P"),
        ("2026-02-16", "農曆除夕", "T"),
        ("2026-02-17", "農曆正月初一", "P"),
        ("2026-02-18", "農曆正月初二", "P"),
        ("2026-02-19", "農曆正月初三", "P"),
        ("2026-04-03", "耶穌受難日", "P"),
        ("2026-04-04", "復活節前日", "P"),
        ("2026-04-05", "清明節", "P"),
        ("2026-04-06", "復活節前日的補假", "C"),
        ("2026-04-07", "清明節的補假", "C"),
        ("2026-05-01", "勞動節", "P"),
        ("2026-05-24", "佛誕節", "P"),
        ("2026-05-25", "佛誕節的補假", "C"),
        ("2026-06-19", "端午節", "P"),
        ("2026-09-26", "中秋節翌日", "P"),
        ("2026-09-28", "中秋節翌日的補假", "C"),
        ("2026-10-01", "中華人民共和國國慶日", "P"),
        ("2026-10-02", "中華人民共和國國慶日翌日", "P"),
        ("2026-10-18", "重陽節", "P"),
        ("2026-10-19", "重陽節的補假", "C"),
        ("2026-11-02", "追思節", "P"),
        ("2026-12-08", "聖母無原罪瞻禮", "P"),
        ("2026-12-20", "澳門特別行政區成立紀念日", "P"),
        ("2026-12-21", "澳門特別行政區成立紀念日的補假", "C"),
        ("2026-12-22", "冬至", "P"),
        ("2026-12-24", "聖誕節前日", "P"),
        ("2026-12-25", "聖誕節", "P"),
        ("2026-12-31", "除夕", "T"),
    ],
    2027: [
        ("2027-01-01", "元旦", "P"),
        ("2027-02-05", "農曆除夕", "T"),
        ("2027-02-06", "農曆正月初一", "P"),
        ("2027-02-07", "農曆正月初二", "P"),
        ("2027-02-08", "農曆正月初三", "P"),
        ("2027-02-09", "農曆正月初一的補假", "C"),
        ("2027-02-10", "農曆正月初二的補假", "C"),
        ("2027-03-26", "耶穌受難日", "P"),
        ("2027-03-27", "復活節前日", "P"),
        ("2027-03-29", "復活節前日的補假", "C"),
        ("2027-04-05", "清明節", "P"),
        ("2027-05-01", "勞動節", "P"),
        ("2027-05-03", "勞動節的補假", "C"),
        ("2027-05-13", "佛誕節", "P"),
        ("2027-06-09", "端午節", "P"),
        ("2027-09-16", "中秋節翌日", "P"),
        ("2027-10-01", "中華人民共和國國慶日", "P"),
        ("2027-10-02", "中華人民共和國國慶日翌日", "P"),
        ("2027-10-04", "中華人民共和國國慶日翌日的補假", "C"),
        ("2027-10-08", "重陽節", "P"),
        ("2027-11-02", "追思節", "P"),
        ("2027-12-08", "聖母無原罪瞻禮", "P"),
        ("2027-12-20", "澳門特別行政區成立紀念日", "P"),
        ("2027-12-22", "冬至", "P"),
        ("2027-12-24", "聖誕節前日", "P"),
        ("2027-12-25", "聖誕節", "P"),
        ("2027-12-27", "聖誕節的補假", "C"),
        ("2027-12-31", "除夕", "T"),
    ],
}


def easter(year):
    """Anonymous Gregorian computus -> Easter Sunday."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return datetime.date(year, month, day + 1)


_SCAN_CACHE = {}


def year_scan(year):
    """一次遍歷全年：同時取得農曆對應表、正月初一、清明與冬至。"""
    if year in _SCAN_CACHE:
        return _SCAN_CACHE[year]

    table = {}
    cny = None
    terms = {}
    d = datetime.date(year, 1, 1)
    stop = datetime.date(year, 12, 31)
    probe = datetime.datetime(year, 1, 1, 12, 0)
    while d <= stop:
        ln = cnlunar.Lunar(probe)
        month_cn = ln.lunarMonthCn
        if "閏" not in month_cn and "润" not in month_cn:
            key = (ln.lunarMonth, ln.lunarDay)
            table.setdefault(key, d)
            if key == (1, 1) and cny is None:
                cny = d
        try:
            t = ln.get_todaySolarTerms()
            t = (t() if callable(t) else t)
            t = str(t).strip()[:2] if t else ""
        except Exception:
            t = ""
        if t in ("清明", "冬至"):
            terms.setdefault(t, d)
        d += datetime.timedelta(days=1)
        probe = datetime.datetime(d.year, d.month, d.day, 12, 0)

    _SCAN_CACHE[year] = (table, cny, terms)
    return _SCAN_CACHE[year]


def lunar_lookup(year):
    table, cny, _terms = year_scan(year)
    return table, cny


def solar_terms(year):
    _table, _cny, terms = year_scan(year)
    ok = (terms.get("清明") and terms["清明"].month == 4 and 3 <= terms["清明"].day <= 7
          and terms.get("冬至") and terms["冬至"].month == 12 and 20 <= terms["冬至"].day <= 23)
    if not ok:
        raise SystemExit("節氣推算異常：%s -> %s" % (year, {k: str(v) for k, v in terms.items()}))
    return terms


def compute_year(year):
    terms = solar_terms(year)
    lunar, cny = lunar_lookup(year)
    e = easter(year)

    days = []

    def add(d, name, kind):
        days.append({"d": d.isoformat(), "s": SHORT.get(name, name[:3]), "n": name, "k": kind})

    add(datetime.date(year, 1, 1), "元旦", "P")
    if cny:
        add(cny, "農曆正月初一", "P")
        add(cny + datetime.timedelta(days=1), "農曆正月初二", "P")
        add(cny + datetime.timedelta(days=2), "農曆正月初三", "P")
        add(cny - datetime.timedelta(days=1), "農曆除夕", "T")
    add(e - datetime.timedelta(days=2), "耶穌受難日", "P")
    add(e - datetime.timedelta(days=1), "復活節前日", "P")
    if "清明" in terms:
        add(terms["清明"], "清明節", "P")
    add(datetime.date(year, 5, 1), "勞動節", "P")
    for key, name in [((4, 8), "佛誕節"), ((5, 5), "端午節"), ((8, 16), "中秋節翌日"), ((9, 9), "重陽節")]:
        if key in lunar:
            add(lunar[key], name, "P")
    add(datetime.date(year, 10, 1), "中華人民共和國國慶日", "P")
    add(datetime.date(year, 10, 2), "中華人民共和國國慶日翌日", "P")
    add(datetime.date(year, 11, 2), "追思節", "P")
    add(datetime.date(year, 12, 8), "聖母無原罪瞻禮", "P")
    add(datetime.date(year, 12, 20), "澳門特別行政區成立紀念日", "P")
    if "冬至" in terms:
        add(terms["冬至"], "冬至", "P")
    add(datetime.date(year, 12, 24), "聖誕節前日", "P")
    add(datetime.date(year, 12, 25), "聖誕節", "P")
    add(datetime.date(year, 12, 31), "除夕", "T")

    holidays = {}
    for item in days:
        holidays[datetime.date.fromisoformat(item["d"])] = item
    taken = set(holidays)

    # 補假：週六/週日的公眾假期順延至之後第一個未佔用的平日
    extra = []
    for d in sorted(holidays):
        item = holidays[d]
        if item["k"] != "P":
            continue
        if d.weekday() >= 5:
            cand = d + datetime.timedelta(days=1)
            while cand.weekday() >= 5 or cand in taken:
                cand += datetime.timedelta(days=1)
            taken.add(cand)
            extra.append({"d": cand.isoformat(), "s": "補假", "n": "%s的補假" % item["n"], "k": "C"})

    days.extend(extra)
    days.sort(key=lambda x: x["d"])
    return days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2024)
    ap.add_argument("--end", type=int, default=2035)
    ap.add_argument("--check", action="store_true", help="只校驗推算規則能否重現官方日期表")
    args = ap.parse_args()

    years = {}

    # 先驗證：推算結果必須與公報官方表完全一致
    mismatch = []
    for y in OFFICIAL:
        got = [(x["d"], x["k"]) for x in compute_year(y)]
        want = sorted([(d, k) for d, n, k in OFFICIAL[y]])
        if got != want:
            only_calc = [g for g in got if g not in want]
            only_off = [w for w in want if w not in got]
            mismatch.append((y, only_calc, only_off))
    if mismatch:
        for y, a, b in mismatch:
            print("MISMATCH %d  推算多: %s  官方多: %s" % (y, a, b))
        print("推算規則與公報不一致，停止輸出。")
        return 1
    print("校驗通過：推算規則可完整重現 2026、2027 官方日期表")

    if args.check:
        return 0

    for y in range(args.start, args.end + 1):
        if y in OFFICIAL:
            days = [{"d": d, "s": SHORT.get(n, n[:3]), "n": n, "k": k} for d, n, k in OFFICIAL[y]]
            days.sort(key=lambda x: x["d"])
            years[str(y)] = {"source": "official", "days": days}
        else:
            years[str(y)] = {"source": "inferred", "days": compute_year(y)}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"place": "澳門", "rule": "第60/2000號行政命令 + 週末假期順延補假",
                   "years": years}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    for y in sorted(years):
        n = len([x for x in years[y]["days"] if x["k"] == "P"])
        c = len([x for x in years[y]["days"] if x["k"] == "C"])
        print(y, years[y]["source"], "公眾假期", n, "補假", c)
    print("wrote", os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
