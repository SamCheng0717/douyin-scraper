"""查找抖音图文笔记的真实结构"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import json

PROFILE_DIR = Path.home() / '.workbuddy/skills/douyin-creator/profile'

async def find_notes():
    p = await async_playwright().start()
    browser = await p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        headless=False,
        viewport={'width': 1280, 'height': 800}
    )
    page = browser.pages[0] if browser.pages else await browser.new_page()
    
    try:
        # 搜索
        print("[1] 打开抖音并搜索...")
        await page.goto('https://www.douyin.com/', wait_until='domcontentloaded')
        await asyncio.sleep(3)
        
        search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=5000)
        await search_input.click()
        await asyncio.sleep(1)
        await page.keyboard.type('韩国医美', delay=100)
        await asyncio.sleep(1)
        await page.keyboard.press('Enter')
        await asyncio.sleep(5)
        
        # 筛选图文和一周内
        print("[2] 筛选图文和一周内...")
        filter_btn = await page.wait_for_selector('xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/span', timeout=5000)
        await filter_btn.hover()
        await asyncio.sleep(1)
        
        image_btn = await page.wait_for_selector('xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/div/div[5]/span[3]', timeout=5000)
        await image_btn.click()
        await asyncio.sleep(2)
        
        await filter_btn.hover()
        await asyncio.sleep(1)
        
        week_btn = await page.wait_for_selector('text=一周内', timeout=5000)
        await week_btn.click()
        await asyncio.sleep(5)
        
        # 截图
        await page.screenshot(path='before_find.png', full_page=True)
        print("[3] 截图已保存: before_find.png")
        
        # 深度查找
        print("\n[4] 深度查找图文笔记...")
        
        notes = await page.evaluate('''() => {
            const results = [];
            
            // 策略1：找所有图片数量标记（图文笔记会有 1/9 这样的标记）
            const imageCounters = document.querySelectorAll('[class*="count"], [class*="indicator"]');
            console.log('找到图片计数器:', imageCounters.length);
            
            // 策略2：找所有大尺寸图片（图文笔记的封面图）
            const allImages = Array.from(document.querySelectorAll('img')).filter(img => {
                const rect = img.getBoundingClientRect();
                return rect.width > 100 && rect.height > 100 && !img.src.includes('avatar');
            });
            console.log('找到大图片:', allImages.length);
            
            // 策略3：遍历每个大图片，找它所在的卡片
            for (let i = 0; i < Math.min(allImages.length, 20); i++) {
                const img = allImages[i];
                
                // 向上查找卡片容器
                let card = img;
                for (let j = 0; j < 10; j++) {
                    const parent = card.parentElement;
                    if (!parent) break;
                    
                    const rect = parent.getBoundingClientRect();
                    if (rect.width > 150 && rect.height > 200) {
                        card = parent;
                        break;
                    }
                    card = parent;
                }
                
                // 在卡片里找信息
                const link = card.querySelector('a[href]') || card.closest('a[href]');
                const title = card.querySelector('h3, h2, [class*="title"], [class*="desc"], [class*="Title"], [class*="Desc"]');
                const author = card.querySelector('[class*="author"], [class*="name"], [class*="Author"], [class*="Name"]');
                const likes = card.querySelector('[class*="like"], [class*="Like"], [class*="digg"], svg + span');
                
                const noteData = {
                    imgSrc: img.src.substring(0, 100),
                    link: link ? link.href : null,
                    title: title ? title.textContent.trim().substring(0, 100) : null,
                    author: author ? author.textContent.trim() : null,
                    likes: likes ? likes.textContent.trim() : null,
                    cardTag: card.tagName,
                    cardClass: card.className.substring(0, 100)
                };
                
                // 去重
                if (noteData.link && !results.find(r => r.link === noteData.link)) {
                    results.push(noteData);
                }
            }
            
            return results;
        }''')
        
        print(f"\n找到 {len(notes)} 条笔记:")
        for i, note in enumerate(notes, 1):
            print(f"\n[{i}] {note['title'] or '(无标题)'}")
            print(f"    作者: {note['author'] or '(未知)'}")
            print(f"    点赞: {note['likes'] or '(未知)'}")
            print(f"    链接: {note['link']}")
            print(f"    图片: {note['imgSrc'][:50]}...")
            print(f"    容器: {note['cardTag']}.{note['cardClass'][:30]}")
        
        # 保存结果
        with open('found_notes.json', 'w', encoding='utf-8') as f:
            json.dump(notes, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: found_notes.json")
        
        # 尝试点击第一个笔记查看详情
        if notes and notes[0]['link']:
            print(f"\n[5] 点击第一个笔记查看详情...")
            await page.goto(notes[0]['link'], wait_until='domcontentloaded')
            await asyncio.sleep(3)
            await page.screenshot(path='note_detail.png')
            print(f"详情页截图: note_detail.png")
            print(f"当前URL: {page.url}")
        
        print("\n浏览器保持打开，可以手动检查...")
        await asyncio.sleep(60)
        
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_notes())
