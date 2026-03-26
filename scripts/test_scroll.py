"""测试：滚动后查找搜索结果"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

PROFILE_DIR = Path.home() / '.workbuddy/skills/douyin-creator/profile'

async def test():
    p = await async_playwright().start()
    browser = await p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
        viewport={'width': 1280, 'height': 800}
    )
    page = browser.pages[0] if browser.pages else await browser.new_page()
    
    try:
        # 搜索
        await page.goto('https://www.douyin.com/', wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=5000)
        await search_input.click()
        await asyncio.sleep(1)
        await page.keyboard.type('韩国医美', delay=100)
        await asyncio.sleep(1)
        await page.keyboard.press('Enter')
        await asyncio.sleep(5)
        
        print("=== 滚动前 ===")
        before = await page.evaluate('document.querySelectorAll("a").length')
        print(f"页面链接数: {before}")
        
        # 滚动多次
        print("\n=== 开始滚动 ===")
        for i in range(5):
            await page.mouse.wheel(0, 800)
            await asyncio.sleep(2)
            print(f"滚动 {i+1}/5")
        
        await page.screenshot(path='after_scroll.png', full_page=True)
        
        print("\n=== 滚动后 ===")
        after = await page.evaluate('document.querySelectorAll("a").length')
        print(f"页面链接数: {after}")
        
        # 查找视频/笔记链接
        results = await page.evaluate('''() => {
            const items = [];
            const links = document.querySelectorAll('a[href]');
            
            links.forEach(link => {
                const href = link.href;
                // 抖音视频/笔记的URL特征：包含modal_id或长数字ID
                if (href.includes('modal_id') || href.match(/\\/\\d{15,}/)) {
                    const text = link.textContent.trim().substring(0, 50);
                    items.push({
                        href: href,
                        text: text || '(无文字)'
                    });
                }
            });
            
            return items;
        }''')
        
        print(f"\n找到 {len(results)} 个视频/笔记链接:")
        for i, item in enumerate(results[:20], 1):
            print(f"{i}. {item['text']}")
            print(f"   {item['href']}")
        
        if not results:
            print("\n还是没有找到结果！")
            print("让我看看页面上所有带class的div:")
            
            divs = await page.evaluate('''() => {
                const divs = [];
                document.querySelectorAll('div[class]').forEach(div => {
                    if (div.className && div.className.length < 50) {
                        divs.push({
                            class: div.className,
                            text: div.textContent.trim().substring(0, 30)
                        });
                    }
                });
                return divs.slice(0, 30);
            }''')
            
            for div in divs:
                if 'card' in div['class'].lower() or 'item' in div['class'].lower() or 'list' in div['class'].lower():
                    print(f"  {div['class']}: {div['text']}")
        
        print("\n\n浏览器保持打开...")
        await asyncio.sleep(120)
        
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
