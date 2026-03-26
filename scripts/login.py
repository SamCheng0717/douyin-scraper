#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音登录 - 状态保存到 profile/ 目录"""
import argparse
import shutil
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PROFILE_DIR = Path(__file__).parent.parent / "profile"


def clear():
    if PROFILE_DIR.exists():
        shutil.rmtree(PROFILE_DIR)
        print("已清除登录状态")
    else:
        print("无登录状态")


def login(timeout: int = 300):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("请安装: pip install playwright && playwright install chromium")
        sys.exit(1)

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    print("\n浏览器将打开抖音，请完成登录\n")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )

        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined })")

        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.douyin.com", wait_until="domcontentloaded", timeout=30000)

        print("请在浏览器中登录（扫码或密码）...\n")

        start = time.time()
        while time.time() - start < timeout:
            try:
                logged = page.evaluate("""
                    () => document.querySelector('[data-e2e="user-avatar"]') !== null ||
                           document.querySelector('.semi-avatar') !== null
                """)
                if logged:
                    print("登录成功！")
                    break
            except Exception:
                pass
            time.sleep(2)
        else:
            print("超时，请重试")
            ctx.close()
            return False

        time.sleep(3)
        ctx.close()

        print("\n登录完成，状态已保存到 profile/")
        return True


def main():
    parser = argparse.ArgumentParser(description="抖音登录")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--clear", action="store_true")

    args = parser.parse_args()

    if args.clear:
        clear()
        return

    sys.exit(0 if login(args.timeout) else 1)


if __name__ == "__main__":
    main()
