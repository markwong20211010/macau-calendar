# 澳門假期翻曆 · 天氣

一個純靜態的翻頁月曆（2026–2027 澳門公眾假期），附今日與未來七天天氣。
天氣資料由 **GitHub Actions 每 3 小時跑一次 Python** 抓取並 commit 回倉庫，
GitHub Pages 自動更新；前端可安裝成手機／電腦 App（PWA），離線可用。

## 檔案結構

```
index.html                   單檔前端（假期、翻頁、天氣、紀錄）
manifest.webmanifest         PWA 清單
sw.js                        離線快取（資料檔走網路優先）
icon-*.png, apple-touch-icon 圖示
data/weather.json            即時天氣 + 未來 16 天預報（Action 產生）
data/history.json            逐日高低溫紀錄（Action 累積）
data/holidays.json           2024–2035 澳門假期（官方 + 推估）
scripts/fetch_weather.py     抓取程式（只用標準庫，無需安裝依賴）
scripts/build_holidays.py    假期產生器（需要 cnlunar，僅新增年份時執行）
.github/workflows/weather.yml 定時任務
```

## 假期資料怎麼來的

`data/holidays.json` 分兩種來源，頁面會明確標示：

- `official`：2026、2027 年，直接採用《澳門特別行政區公報》刊佈的日期表。
- `inferred`：其他年份，官方尚未公佈，依《第 60/2000 號行政命令》的 20 天公眾假期，
  再加「補假規則」推算：公眾假期碰到星期六或星期日 → 順延到之後第一個平日；
  該平日若已是假期或已被其他補假佔用 → 再往後順延，如此類推。

這條規則是先拿 2026、2027 的官方日期表逐條反推校驗過的——腳本每次執行都會先跑這個
校驗（`校驗通過：推算規則可完整重現 2026、2027 官方日期表`），對不上就直接中止、不輸出。

等某一年的官方名單公佈後（通常在前一年的 11–12 月），把它填進
`scripts/build_holidays.py` 的 `OFFICIAL` 字典再重跑即可：

```bash
pip install cnlunar==0.2.5
python3 scripts/build_holidays.py --check            # 只跑校驗
python3 scripts/build_holidays.py --start 2024 --end 2035
```

推估年份在月曆頁會標「（推估）」，年份列右側顯示「依規則推估」，下方另有文字提醒
「正式日期以公報為準」。

## 部署步驟

1. 在 GitHub 建一個公開倉庫，把本資料夾全部內容推到 `main` 分支
   （注意 `.github/` 是隱藏資料夾，上傳時別漏掉）。
2. 倉庫 **Settings → Pages**：Source 選 `Deploy from a branch`，Branch 選 `main` / `(root)`。
3. 倉庫 **Settings → Actions → General → Workflow permissions**：
   選 **Read and write permissions**，儲存。否則 Action 無法 commit 資料。
4. 到 **Actions** 分頁，選 `Update Macau weather` → `Run workflow` 手動跑一次，
   確認 `data/weather.json` 有更新。
5. 開啟 `https://<你的帳號>.github.io/<倉庫名>/`：
   - 電腦 Chrome／Edge：網址欄右側安裝圖示，或頁面「安裝到桌面」
   - Android Chrome：選單 →「安裝應用程式」
   - iPhone Safari：分享 →「加入主畫面」

## 定時頻率

`.github/workflows/weather.yml` 內：

```yaml
schedule:
  - cron: "5 */3 * * *"   # UTC，每 3 小時（澳門時間 +8）
```

可改成 `"0 * * * *"`（每小時）。注意 GitHub 對免費帳戶的排程任務在高峰期
可能延遲數分鐘至數十分鐘，不會精確到秒。

## 本機執行

```bash
python3 scripts/fetch_weather.py                  # 更新預報 + 記錄今天
python3 scripts/fetch_weather.py --backfill 365   # 補齊過去一年歷史
python3 scripts/fetch_weather.py --dry-run        # 不寫檔，只看結果
```

只需要 Python 3.9+，不裝任何第三方套件。

## 資料來源

- 假期推算：農曆與二十四氣用 `cnlunar`；復活節用匿名格里戈里算法（預報 `api.open-meteo.com`、歷史 `archive-api.open-meteo.com`），
  座標 22.1987, 113.5439，時區 Asia/Macau，免費且無需 API key。
- 假期：第 60/2000 號行政命令、行政公職局 2026／2027 年度假期通告。

## 幾點實話

- 純網頁做不到 iOS／Android 的桌面小工具（Widget），能做到最接近的就是這個 PWA。
- 歷史天氣用 Open-Meteo 的再分析資料補齊，約有 5–6 天延遲；之後由每日 Action 續寫。
- 前端仍保留本機 localStorage 記錄，即使沒部署後端也能自己累積。
