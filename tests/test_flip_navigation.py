#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""翻頁導航回歸測試（Playwright）。

回測的 bug：向回翻一個月後，再按「下月」或點月份跳轉全部失效。
根因：留在舞台上的那頁帶著 anim-prev，下一輪加上 anim-next 時被樣式表後面的
.anim-prev 規則蓋掉，動畫名稱未變 → animationend 不再觸發 → 收尾不回調、
animating 永久卡死。

執行：
    pip install playwright && playwright install chromium
    python3 tests/test_flip_navigation.py [http://127.0.0.1:8000/index.html]
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES = []
CHROME_CANDIDATES = [
    os.environ.get("CHROME_PATH"),
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def launch(pw):
    """優先使用 playwright 自帶 browser；沒有就退回系統 Chrome。"""
    args = ["--no-sandbox", "--disable-dev-shm-usage"]
    try:
        return pw.chromium.launch(args=args)
    except Exception:
        for cand in CHROME_CANDIDATES:
            if cand and os.path.exists(cand):
                print("(使用系統 Chrome：" + cand + ")")
                return pw.chromium.launch(executable_path=cand, args=args)
        raise


def check(tag, got, want):
    good = got == want
    if not good:
        FAILURES.append("%s: got %r want %r" % (tag, got, want))
    print(("PASS  " if good else "FAIL  ") + tag + " -> " + repr(got))


def run(url):
    with sync_playwright() as p:
        browser = launch(p)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url)
        page.wait_for_timeout(900)

        pos = lambda: page.inner_text("#pos").strip()

        check("開啟即今天所在月", pos(), "2026 · 11 / 12")

        # 使用者回報的失敗序列
        page.click("#prev"); page.wait_for_timeout(950)
        check("上月", pos(), "2026 · 10 / 12")
        page.click("#next"); page.wait_for_timeout(950)
        check("回翻後再按下月", pos(), "2026 · 11 / 12")

        page.click("#prev"); page.wait_for_timeout(950)
        page.click("#prev"); page.wait_for_timeout(950)
        check("連續向上翻兩次", pos(), "2026 · 9 / 12")
        page.click("#next"); page.wait_for_timeout(950)
        check("接著向下翻", pos(), "2026 · 10 / 12")

        page.get_by_role("button", name="十二月", exact=True).click()
        page.wait_for_timeout(950)
        check("跳月", pos(), "2026 · 12 / 12")
        page.click("#next"); page.wait_for_timeout(950)
        check("12 月再下月跨入隔年", pos(), "2027 · 1 / 12")
        page.click("#prev"); page.wait_for_timeout(950)
        check("1 月再上月退回上年", pos(), "2026 · 12 / 12")

        page.click("#yearNext"); page.wait_for_timeout(650)
        check("年份切換保留當月", pos(), "2027 · 12 / 12")
        page.click("#next"); page.wait_for_timeout(950)
        check("跨入推估年份", pos(), "2028 · 1 / 12")
        page.get_by_role("button", name="十月", exact=True).click()
        page.wait_for_timeout(950)
        check("推估年仍可跳月", pos(), "2028 · 10 / 12")

        # 連點之後不能卡死
        page.click("#next"); page.click("#next"); page.click("#prev")
        page.wait_for_timeout(1600)
        before = pos()
        page.click("#next"); page.wait_for_timeout(950)
        if pos() == before:
            FAILURES.append("連點後導航仍然卡死")
            print("FAIL  連點後仍能再翻")
        else:
            print("PASS  連點後仍能再翻 -> " + repr(pos()))

        left = page.eval_on_selector_all(".sheet", "els => els.length")
        check("舞台只剩一頁", left, 1)
        dirty = page.eval_on_selector_all(
            ".sheet",
            "els => els.filter(e => /anim-|fade-in/.test(e.className)).length",
        )
        check("沒有殘留動畫 class", dirty, 0)

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(url)
        mobile.wait_for_timeout(800)
        mobile.click("#prev"); mobile.wait_for_timeout(950)
        mobile.click("#next"); mobile.wait_for_timeout(950)
        check("手機尺寸同樣可翻", mobile.inner_text("#pos").strip(), "2026 · 11 / 12")

        if errors:
            FAILURES.append("頁面報錯：" + "; ".join(errors))
        print("pageerrors:", errors)
        browser.close()


def main():
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        server = subprocess.Popen(
            [sys.executable, "-m", "http.server", "8123"],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        try:
            run("http://127.0.0.1:8123/index.html")
        finally:
            server.terminate()

    if FAILURES:
        print("\n=== FAILED ===")
        for f in FAILURES:
            print(" -", f)
        return 1
    print("\n=== ALL PASS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
