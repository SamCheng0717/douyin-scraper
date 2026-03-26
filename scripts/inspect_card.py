"""检查search-result-card的内部结构"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json

PROFILE_DIR = Path.home() / '.workbuddy/skills/douyin-creator/profile'

async def inspect():
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
        await asyncio.sleep(8)
        
        search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=5000)
        await search_input.click()
        await asyncio.sleep(1)
        await page.keyboard.type('韩国医美', delay=100)
        await asyncio.sleep(1)
        await page.keyboard.press('Enter')
        await asyncio.sleep(8)
        
        # 筛选
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
        
        print("=== 检查search-result-card内部结构 ===\n")
        
        # 获取前3个卡片的详细信息
        cards_info = await page.evaluate('''() => {
            const cards = document.querySelectorAll('[class*="search-result-card"]');
            const results = [];
            
            for (let i = 0; i < Math.min(cards.length, 3); i++) {
                const card = cards[i];
                
                // 获取所有可能的信息
                const info = {
                    index: i,
                    className: card.className,
                    tagName: card.tagName,
                    
                    // 查找链接
                    links: [],
                    
                    // 查找标题
                    titles: [],
                    
                    // 查找作者
                    authors: [],
                    
                    // 查找点赞
                    likes: [],
                    
                    // 查找图片
                    images: [],
                    
                    // innerHTML前500字符
                    html: card.innerHTML.substring(0, 500)
                };
                
                // 所有的a标签
                card.querySelectorAll('a').forEach(a => {
                    info.links.push({
                        href: a.href,
                        text: a.textContent.trim().substring(0, 50)
                    });
                });
                
                // 所有可能的标题元素
                card.querySelectorAll('h1, h2, h3, [class*="title"], [class*="Title"], [class*="desc"]').forEach(el => {
                    info.titles.push({
                        tag: el.tagName,
                        class: el.className.substring(0, 30),
                        text: el.textContent.trim().substring(0, 50)
                    });
                });
                
                // 所有可能的作者元素
                card.querySelectorAll('[class*="author"], [class*="name"], [class*="Author"]').forEach(el => {
                    info.authors.push({
                        class: el.className.substring(0, 30),
                        text: el.textContent.trim()
                    });
                });
                
                // 所有可能的点赞元素
                card.querySelectorAll('[class*="like"], [class*="count"], [class*="digg"]').forEach(el => {
                    info.likes.push({
                        class: el.className.substring(0, 30),
                        text: el.textContent.trim()
                    });
                });
                
                // 所有图片
                card.querySelectorAll('img').forEach(img => {
                    info.images.push({
                        src: img.src.substring(0, 80),
                        alt: img.alt
                    });
                });
                
                results.push(info);
            }
            
            return results;
        }''')
        
        for card in cards_info:
            print(f"卡片 {card['index']}: {card['tagName']}.{card['className'][:30]}")
            print(f"  链接 ({len(card['links'])}个):")
            for link in card['links'][:3]:
                print(f"    - {link['href'][:60]}...")
                print(f"      文字: {link['text']}")
            
            print(f"  标题 ({len(card['titles'])}个):")
            for title in card['titles'][:3]:
                print(f"    - {title['tag']}.{title['class']}: {title['text']}")
            
            print(f"  作者 ({len(card['authors'])}个):")
            for author in card['authors']:
                print(f"    - {author['class']}: {author['text']}")
            
            print(f"  点赞 ({len(card['likes'])}个):")
            for like in card['likes']:
                print(f"    - {like['class']}: {like['text']}")
            
            print(f"  图片 ({len(card['images'])}个):")
            for img in card['images'][:2]:
                print(f"    - {img['src'][:50]}...")
            
            print(f"\n  HTML片段: {card['html'][:200]}...\n")
            print("="*60 + "\n")
        
        # 保存完整信息
        with open('card_structure.json', 'w', encoding='utf-8') as f:
            json.dump(cards_info, f, ensure_ascii=False, indent=2)
        print("完整结构已保存到 card_structure.json")
        
        await asyncio.sleep(60)
        
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
