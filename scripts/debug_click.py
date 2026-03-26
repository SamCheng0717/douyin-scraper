"""
调试脚本：手动指导点击筛选
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROFILE_DIR = SKILL_DIR / "profile"


async def debug_click():
    async with async_playwright() as p:
        print("[启动] 打开浏览器...")
        
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={'width': 1280, 'height': 800},
            locale='zh-CN',
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # 打开抖音首页
        print("[首页] 打开抖音...")
        await page.goto("https://www.douyin.com/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # 搜索
        print("[搜索] 输入关键词...")
        search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=10000)
        await search_input.click()
        await asyncio.sleep(1)
        
        await page.keyboard.type("韩国医美", delay=100)
        await asyncio.sleep(1)
        
        print("[搜索] 按回车...")
        await page.keyboard.press('Enter')
        await asyncio.sleep(4)
        
        print(f"\n{'='*60}")
        print("已到达搜索结果页")
        print("请告诉我：")
        print("  1. 筛选按钮的位置（左边还是右边？）")
        print("  2. 或者直接用浏览器开发者工具查看筛选按钮的属性")
        print("  3. 然后手动点击筛选 -> 图文，我会观察")
        print(f"{'='*60}\n")
        
        # 保持浏览器打开，让你操作
        input("按回车继续...")
        
        # 截图最终状态
        await page.screenshot(path=str(SKILL_DIR / "debug_manual.png"))
        print(f"[截图] 已保存: debug_manual.png")
        
        # 打印当前 URL
        print(f"[URL] {page.url}")
        
        input("按回车关闭浏览器...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_click())
