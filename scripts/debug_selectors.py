"""调试抖音页面选择器"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

PROFILE_DIR = Path.home() / '.workbuddy/skills/douyin-creator/profile'

async def debug():
    p = await async_playwright().start()
    browser = await p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
        viewport={'width': 1280, 'height': 800}
    )
    page = browser.pages[0] if browser.pages else await browser.new_page()
    
    try:
        # 搜索韩国医美
        await page.goto('https://www.douyin.com/', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        
        # 输入搜索
        search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=5000)
        await search_input.click()
        await asyncio.sleep(1)
        await page.keyboard.type('韩国医美', delay=100)
        await asyncio.sleep(1)
        await page.keyboard.press('Enter')
        await asyncio.sleep(4)
        
        # 悬浮筛选
        filter_btn = await page.wait_for_selector('xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/span', timeout=5000)
        await filter_btn.hover()
        await asyncio.sleep(1)
        
        # 点击图文
        image_btn = await page.wait_for_selector('xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/div/div[5]/span[3]', timeout=5000)
        await image_btn.click()
        await asyncio.sleep(1)
        
        # 悬浮筛选再次
        await filter_btn.hover()
        await asyncio.sleep(1)
        
        # 点击一周内
        week_btn = await page.wait_for_selector('text=一周内', timeout=5000)
        await week_btn.click()
        await asyncio.sleep(3)
        
        # 截图
        await page.screenshot(path='debug_page.png', full_page=True)
        print('截图已保存到 debug_page.png')
        
        # 查找卡片 - 尝试各种选择器
        print("\n=== 测试选择器 ===")
        
        selectors = [
            'li[data-e2e="search-common-video"]',
            'li[data-e2e="search-common-image"]',
            'li[data-e2e]',
            'ul[data-e2e="search-list"] > li',
            'ul li',
            'div[class*="search-result"] li',
            'div[class*="card"]',
            'div[class*="item"]',
            'a[href*="/note/"]',
        ]
        
        for selector in selectors:
            try:
                els = await page.query_selector_all(selector)
                print(f'{selector}: {len(els)} 个')
            except Exception as e:
                print(f'{selector}: 错误 - {e}')
        
        # 获取第一个搜索结果的HTML
        print("\n=== 尝试获取第一个卡片 ===")
        first_card = await page.query_selector('ul li:first-child')
        if first_card:
            html = await first_card.inner_html()
            print(f"第一个卡片HTML (前500字符): {html[:500]}")
        else:
            print("未找到第一个卡片")
        
        # 等待用户观察
        print("\n浏览器将保持打开60秒，可以手动检查...")
        await asyncio.sleep(60)
        
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
