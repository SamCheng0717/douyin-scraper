"""调试脚本：打印搜索结果页的元素结构"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROFILE_DIR = SKILL_DIR / "profile"


async def debug_elements():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={'width': 1280, 'height': 800},
            locale='zh-CN',
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # 打开抖音
        await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        # 搜索
        search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=10000)
        await search_input.click()
        await page.keyboard.type("韩国医美")
        await page.keyboard.press('Enter')
        
        # 等待跳转
        await asyncio.sleep(5)
        
        # 打印页面 URL
        print(f"\n当前 URL: {page.url}\n")
        
        # 打印所有按钮文本
        print("=== 所有按钮 ===")
        buttons = await page.query_selector_all('button')
        for btn in buttons[:20]:
            text = await btn.inner_text()
            if text.strip():
                print(f"  - {text.strip()}")
        
        # 打印所有可点击元素
        print("\n=== 所有可点击元素（div/span/a）===")
        clickables = await page.query_selector_all('div[class], span[class], a[class]')
        for el in clickables[:50]:
            text = await el.inner_text()
            class_name = await el.get_attribute('class') or ""
            tag = await el.evaluate('el => el.tagName')
            if text.strip() and len(text.strip()) < 50:
                print(f"  <{tag.lower()}> {text.strip()[:30]} | class: {class_name[:50]}")
        
        # 找包含"筛选"的元素
        print("\n=== 包含'筛选'的元素 ===")
        filter_elements = await page.query_selector_all('text=筛选')
        for el in filter_elements:
            tag = await el.evaluate('el => el.tagName')
            class_name = await el.get_attribute('class') or ""
            parent = await el.evaluate('el => el.parentElement?.tagName')
            print(f"  <{tag.lower()}> | class: {class_name[:50]} | parent: {parent}")
        
        # 找包含"图文"的元素
        print("\n=== 包含'图文'的元素 ===")
        image_elements = await page.query_selector_all('text=图文')
        for el in image_elements:
            tag = await el.evaluate('el => el.tagName')
            class_name = await el.get_attribute('class') or ""
            print(f"  <{tag.lower()}> | class: {class_name[:50]}")
        
        # 找搜索结果卡片
        print("\n=== 搜索结果卡片 ===")
        card_selectors = [
            'li',
            'div[class*="item"]',
            'div[class*="card"]',
            'a[href*="/note/"]',
        ]
        
        for selector in card_selectors:
            cards = await page.query_selector_all(selector)
            if cards:
                print(f"  {selector}: {len(cards)} 个")
                if len(cards) <= 30:
                    for card in cards[:5]:
                        class_name = await card.get_attribute('class') or ""
                        href = await card.get_attribute('href') or ""
                        text = await card.inner_text()
                        print(f"    - class: {class_name[:40]}")
                        if href:
                            print(f"      href: {href[:50]}")
                        if text.strip():
                            print(f"      text: {text.strip()[:50]}")
        
        # 截图
        await page.screenshot(path=str(SKILL_DIR / "debug_full.png"), full_page=True)
        print(f"\n截图保存到: debug_full.png")
        
        # 自动关闭
        await asyncio.sleep(2)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_elements())
