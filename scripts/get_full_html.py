"""获取完整的卡片HTML"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

PROFILE_DIR = Path.home() / '.workbuddy/skills/douyin-creator/profile'

async def get_html():
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
        
        # 获取第一个卡片的完整HTML
        html = await page.evaluate('''() => {
            const card = document.querySelector('[class*="search-result-card"]');
            return card ? card.outerHTML : 'not found';
        }''')
        
        with open('first_card.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print("第一个卡片HTML已保存到 first_card.html")
        print(f"HTML长度: {len(html)} 字符")
        
        # 尝试获取所有可见的文本
        all_text = await page.evaluate('''() => {
            const card = document.querySelector('[class*="search-result-card"]');
            if (!card) return [];
            
            // 获取所有文本节点
            const walker = document.createTreeWalker(
                card,
                NodeFilter.SHOW_TEXT,
                null,
                false
            );
            
            const texts = [];
            let node;
            while (node = walker.nextNode()) {
                const text = node.textContent.trim();
                if (text) {
                    texts.push({
                        text: text,
                        parentTag: node.parentElement.tagName,
                        parentClass: node.parentElement.className.substring(0, 30)
                    });
                }
            }
            return texts;
        }''')
        
        print("\n卡片内所有文本:")
        for t in all_text:
            print(f"  {t['parentTag']}.{t['parentClass']}: {t['text']}")
        
        # 尝试获取卡片的所有属性
        attrs = await page.evaluate('''() => {
            const card = document.querySelector('[class*="search-result-card"]');
            if (!card) return {};
            
            const result = {};
            for (let attr of card.attributes) {
                result[attr.name] = attr.value;
            }
            return result;
        }''')
        
        print("\n卡片属性:")
        for k, v in attrs.items():
            print(f"  {k}: {v[:100] if len(v) > 100 else v}")
        
        await asyncio.sleep(30)
        
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_html())
