#!/usr/bin/env python3
"""澳門天氣資料抓取。

寫出兩個檔案（給 GitHub Pages 的靜態前端讀取）：
  data/weather.json  即時天氣 + 未來 16 天預報
  data/history.json  逐日高低溫紀錄（持續累積）

用法：
  python3 scripts/fetch_weather.py                 # 更新預報，記錄今天
  python3 scripts/fetch_weather.py --backfill 365  # 先用 Open-Meteo Archive 補齊過去一年
  python3 scripts/fetch_weather.py --dry-run       # 只印結果，不寫檔
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

LATITUDE = 22.1987
LONGITUDE = 113.5439
TIMEZONE = "Asia/Macau"
TZ = timezone(timedelta(hours=8))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
WEATHER_PATH = os.path.join(DATA_DIR, "weather.json")
HISTORY_PATH = os.path.join(DATA_DIR, "history.json")

# WMO weather code -> 繁中描述 + 單字符號
WMO = {
    0: ("晴", "☀"), 1: ("晴間雲", "⛅"), 2: ("多雲", "⛅"), 3: ("陰", "☁"),
    45: ("霧", "≡"), 48: ("霧", "≡"),
    51: ("微雨", "☂"), 53: ("微雨", "☂"), 55: ("細雨", "☂"),
    61: ("小雨", "☂"), 63: ("中雨", "☂"), 65: ("大雨", "☂"),
    66: ("凍雨", "☂"), 67: ("凍雨", "☂"),
    71: ("小雪", "❄"), 73: ("中雪", "❄"), 75: ("大雪", "❄"), 77: ("雪粒", "❄"),
    80: ("驟雨", "☂"), 81: ("驟雨", "☂"), 82: ("強驟雨", "☂"),
    85: ("陣雪", "❄"), 86: ("陣雪", "❄"),
    95: ("雷雨", "⛈"), 96: ("雷雨", "⛈"), 99: ("雷雨", "⛈"),
}


def code_info(code):
    return WMO.get(int(code), ("—", "·"))


def http_json(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": "macau-calendar-weather/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build(params_base, **extra):
    params = dict(params_base)
    params.update(extra)
    return urllib.parse.urlencode(params, safe=",")


def fetch_forecast(days=16):
    base = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "past_days": 1,
        "forecast_days": days,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
    }
    url = "https://api.open-meteo.com/v1/forecast?" + build(base)
    return http_json(url)


def fetch_archive(start, end):
    base = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "timezone": TIMEZONE,
        "start_date": start,
        "end_date": end,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + build(base)
    return http_json(url)


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return {"place": "澳門", "days": {}}
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("days", {})
    return data


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def day_record(tmin, tmax, code):
    if tmin is None or tmax is None:
        return None
    return {"tmin": int(round(tmin)), "tmax": int(round(tmax)), "code": int(code or 0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", type=int, default=0, help="補齊過去 N 天歷史（0 = 不補）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    now = datetime.now(TZ)
    today_iso = now.date().isoformat()

    forecast = fetch_forecast()
    daily = forecast.get("daily") or {}
    times = daily.get("time") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    codes = daily.get("weather_code") or []

    days = []
    history = load_history()
    for i, d in enumerate(times):
        rec = day_record(lows[i], highs[i], codes[i])
        if not rec:
            continue
        days.append({"d": d, **rec})
        # 只把「今天及以前」寫進紀錄，預報不用來冒充實測
        if d <= today_iso:
            history["days"][d] = rec

    if args.backfill > 0:
        end = now.date() - timedelta(days=6)   # 再分析資料約有 5–6 天延遲
        start = end - timedelta(days=args.backfill)
        arch = fetch_archive(start.isoformat(), end.isoformat())
        ad = arch.get("daily") or {}
        added = 0
        for i, d in enumerate(ad.get("time") or []):
            if d in history["days"]:
                continue
            rec = day_record((ad.get("temperature_2m_min") or [None] * 9)[i],
                             (ad.get("temperature_2m_max") or [None] * 9)[i],
                             (ad.get("weather_code") or [None] * 9)[i])
            if rec:
                history["days"][d] = rec
                added += 1
        print("backfill added:", added)

    cur = forecast.get("current") or {}
    ctext, cglyph = code_info(cur.get("weather_code", 0))
    weather = {
        "place": "澳門",
        "updated": now.isoformat(timespec="seconds"),
        "stamp": now.strftime("%Y-%m-%d %H:%M") + " HKT",
        "source": "Open-Meteo · GitHub Action",
        "current": {
            "temp": int(round(cur.get("temperature_2m", 0))),
            "text": ctext,
            "glyph": cglyph,
            "humidity": int(round(cur.get("relative_humidity_2m", 0))),
            "wind": "風速 %s km/h" % round(cur.get("wind_speed_10m", 0), 1),
        },
        "days": days,
    }

    history["place"] = "澳門"
    history["updated"] = now.isoformat(timespec="seconds")
    history["days"] = dict(sorted(history["days"].items()))

    print("today:", today_iso, "| forecast days:", len(days), "| history days:", len(history["days"]))
    if args.dry_run:
        print(json.dumps(weather["current"], ensure_ascii=False))
        return 0

    save_json(WEATHER_PATH, weather)
    save_json(HISTORY_PATH, history)
    print("wrote", os.path.relpath(WEATHER_PATH, ROOT), "and", os.path.relpath(HISTORY_PATH, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
