"""调试抖音卡片结构"""
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
        # 搜索
        await page.goto('https://www.douyin.com/', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=5000)
        await search_input.click()
        await asyncio.sleep(1)
        await page.keyboard.type('韩国医美', delay=100)
        await asyncio.sleep(1)
        await page.keyboard.press('Enter')
        await asyncio.sleep(4)
        
        # 筛选图文和一周内
        filter_btn = await page.wait_for_selector('xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/span', timeout=5000)
        await filter_btn.hover()
        await asyncio.sleep(1)
        image_btn = await page.wait_for_selector('xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/div/div[5]/span[3]', timeout=5000)
        await image_btn.click()
        await asyncio.sleep(1)
        await filter_btn.hover()
        await asyncio.sleep(1)
        week_btn = await page.wait_for_selector('text=一周内', timeout=5000)
        await week_btn.click()
        await asyncio.sleep(3)
        
        print("=== 查找搜索结果容器 ===")
        
        # 查找搜索结果容器
        containers = [
            'ul[data-e2e="search-list"]',
            'div[data-e2e="search-list"]',
            '[class*="search-result"]',
            '[class*="SearchList"]',
            'ul[class*="list"]',
        ]
        
        for selector in containers:
            try:
                els = await page.query_selector_all(selector)
                if els:
                    print(f'{selector}: {len(els)} 个')
            except:
                pass
        
        print("\n=== 查找搜索结果卡片 ===")
        
        # 获取第一个看起来像搜索结果的元素
        # 尝试找到包含图片和文字的卡片
        
        # 方法1：找所有有链接的卡片
        cards_with_links = await page.query_selector_all('ul li a[href*="note"], ul li a[href*="video"]')
        print(f'带note/video链接的卡片: {len(cards_with_links)} 个')
        
        # 方法2：找所有带图片的li
        cards_with_img = await page.query_selector_all('ul li:has(img)')
        print(f'带图片的li: {len(cards_with_img)} 个')
        
        # 方法3：获取搜索结果区域的HTML
        search_area = await page.query_selector('ul[class*="list"], div[class*="search"]')
        if search_area:
            html = await search_area.inner_html()
            # 保存前2000个字符
            with open('debug_search_area.html', 'w', encoding='utf-8') as f:
                f.write(html[:5000])
            print('\n搜索区域HTML已保存到 debug_search_area.html')
        
        # 方法4：直接用JavaScript获取所有搜索结果卡片
        print("\n=== 使用JS查找卡片 ===")
        card_info = await page.evaluate('''() => {
            const results = [];
            // 找所有可能的卡片
            const cards = document.querySelectorAll('ul li');
            
            for (let i = 0; i < Math.min(cards.length, 5); i++) {
                const card = cards[i];
                const link = card.querySelector('a[href]');
                const title = card.querySelector('h3, [class*="title"], [class*="Title"]');
                const author = card.querySelector('[class*="author"], [class*="Author"], [class*="name"]');
                const likes = card.querySelector('[class*="like"], [class*="Like"], [class*="digg"]');
                const img = card.querySelector('img');
                
                results.push({
                    index: i,
                    link: link ? link.href : null,
                    title: title ? title.textContent.trim() : null,
                    author: author ? author.textContent.trim() : null,
                    likes: likes ? likes.textContent.trim() : null,
                    hasImg: !!img,
                    className: card.className,
                    innerHTML: card.innerHTML.substring(0, 200)
                });
            }
            return results;
        }''')
        
        print("\n前5个卡片信息:")
        for card in card_info:
            print(f"\n卡片 {card['index']}:")
            print(f"  链接: {card['link']}")
            print(f"  标题: {card['title']}")
            print(f"  作者: {card['author']}")
            print(f"  点赞: {card['likes']}")
            print(f"  有图片: {card['hasImg']}")
            print(f"  类名: {card['className']}")
        
        await asyncio.sleep(60)
        
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
