"""测试：不筛选，直接看搜索结果"""
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
        
        # 不筛选，直接看有什么
        print("=== 不筛选，直接查看搜索结果 ===")
        
        await page.screenshot(path='no_filter.png', full_page=True)
        
        # 查找所有视频/笔记卡片
        results = await page.evaluate('''() => {
            const items = [];
            
            // 查找所有有链接的元素
            const links = document.querySelectorAll('a[href]');
            
            links.forEach(link => {
                const href = link.href;
                // 过滤掉导航、下载等链接
                if (href.includes('douyin.com') && 
                    !href.includes('download') && 
                    !href.includes('creator') &&
                    !href.includes('live') &&
                    !href.includes('user') &&
                    !href.includes('jingxuan') &&
                    !href.includes('recommend') &&
                    !href.includes('follow') &&
                    !href.includes('friend') &&
                    !href.includes('aisearch') &&
                    !href.includes('from_nav')) {
                    
                    const text = link.textContent.trim().substring(0, 50);
                    const parent = link.closest('li') || link.closest('[class*="card"]') || link.closest('[class*="item"]');
                    
                    items.push({
                        href: href,
                        text: text || '(无文字)',
                        parentTag: parent ? parent.tagName : 'unknown',
                        parentClass: parent ? parent.className.substring(0, 50) : ''
                    });
                }
            });
            
            return items;
        }''')
        
        print(f"\n找到 {len(results)} 个可能的搜索结果:")
        for i, item in enumerate(results[:15], 1):
            print(f"{i}. {item['text']}")
            print(f"   {item['href']}")
            print(f"   容器: {item['parentTag']}.{item['parentClass']}")
        
        print("\n\n浏览器保持打开，可以手动检查...")
        await asyncio.sleep(120)
        
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
