"""深入调试抖音搜索结果"""
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
        await asyncio.sleep(5)
        
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
        await asyncio.sleep(5)  # 等待更长时间
        
        print("=== 截图 ===")
        await page.screenshot(path='debug_filtered.png', full_page=True)
        
        print("\n=== 使用JS深度查找卡片 ===")
        cards = await page.evaluate('''() => {
            const results = [];
            
            // 方法1：找所有包含抖音链接的a标签
            const allLinks = Array.from(document.querySelectorAll('a[href*="douyin.com"]'));
            const noteLinks = allLinks.filter(a => {
                const href = a.href;
                return href.includes('/note/') || 
                       href.includes('/video/') || 
                       href.includes('modal_id') ||
                       href.match(/\\/\\d{10,}/);  // 抖音笔记ID通常是长数字
            });
            
            console.log('找到笔记链接:', noteLinks.length);
            
            for (let i = 0; i < Math.min(noteLinks.length, 10); i++) {
                const link = noteLinks[i];
                // 找父级卡片
                let card = link.closest('li') || link.closest('[class*="card"]') || link.closest('[class*="item"]') || link.parentElement;
                
                if (card) {
                    const title = card.querySelector('h3, [class*="title"], [class*="Title"], [class*="desc"]');
                    const author = card.querySelector('[class*="author"], [class*="Author"], [class*="name"]');
                    const likes = card.querySelector('[class*="like"], [class*="Like"], [class*="digg"], [class*="count"]');
                    const img = card.querySelector('img');
                    
                    results.push({
                        link: link.href,
                        title: title ? title.textContent.trim().substring(0, 50) : null,
                        author: author ? author.textContent.trim() : null,
                        likes: likes ? likes.textContent.trim() : null,
                        hasImg: !!img,
                        cardClass: card.className
                    });
                }
            }
            
            return results;
        }''')
        
        print(f"\n找到 {len(cards)} 个卡片:")
        for i, card in enumerate(cards, 1):
            print(f"\n[{i}] 链接: {card['link']}")
            print(f"    标题: {card['title']}")
            print(f"    作者: {card['author']}")
            print(f"    点赞: {card['likes']}")
            print(f"    类名: {card['cardClass']}")
        
        # 尝试滚动后再找
        print("\n=== 滚动后重新查找 ===")
        await page.mouse.wheel(0, 500)
        await asyncio.sleep(2)
        
        cards2 = await page.evaluate('''() => {
            const results = [];
            
            // 方法2：查找所有可见的大卡片（可能是图文）
            const visibleCards = Array.from(document.querySelectorAll('li, div[class*="card"], div[class*="item"]'))
                .filter(el => {
                    const rect = el.getBoundingClientRect();
                    return rect.width > 100 && rect.height > 100;  // 可见的大元素
                });
            
            console.log('找到可见卡片:', visibleCards.length);
            
            for (let i = 0; i < Math.min(visibleCards.length, 10); i++) {
                const card = visibleCards[i];
                const link = card.querySelector('a[href]') || card.closest('a[href]');
                
                if (link) {
                    const href = link.href;
                    if (!href.includes('douyin.com') || href.includes('download') || href.includes('creator')) {
                        continue;
                    }
                    
                    const title = card.querySelector('h3, [class*="title"], [class*="desc"]');
                    const author = card.querySelector('[class*="author"], [class*="name"]');
                    const likes = card.querySelector('[class*="like"], [class*="digg"], [class*="count"]');
                    
                    results.push({
                        link: href,
                        title: title ? title.textContent.trim().substring(0, 50) : null,
                        author: author ? author.textContent.trim() : null,
                        likes: likes ? likes.textContent.trim() : null,
                        className: card.className
                    });
                }
            }
            
            return results;
        }''')
        
        print(f"\n滚动后找到 {len(cards2)} 个卡片:")
        for i, card in enumerate(cards2, 1):
            print(f"\n[{i}] 链接: {card['link']}")
            print(f"    标题: {card['title']}")
            print(f"    作者: {card['author']}")
            print(f"    点赞: {card['likes']}")
        
        print("\n\n浏览器保持打开，可以手动检查...")
        await asyncio.sleep(120)
        
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
