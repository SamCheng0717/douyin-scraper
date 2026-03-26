"""模拟真实用户行为"""
import asyncio
import random
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
        # 打开首页
        print("[1] 打开首页...")
        await page.goto('https://www.douyin.com/', wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(8)  # 给更多时间让页面完全加载
        
        # 鼠标随机移动（模拟真实用户）
        print("[2] 模拟鼠标移动...")
        for _ in range(5):
            x = random.randint(100, 1180)
            y = random.randint(100, 700)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # 点击搜索框
        print("[3] 点击搜索框...")
        search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=5000)
        await search_input.hover()
        await asyncio.sleep(1)
        await search_input.click()
        await asyncio.sleep(2)
        
        # 慢速输入关键词
        print("[4] 输入关键词...")
        keyword = '韩国医美'
        for char in keyword:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.15, 0.35))
        
        await asyncio.sleep(2)
        
        # 按回车
        print("[5] 按回车搜索...")
        await page.keyboard.press('Enter')
        
        # 等待页面加载完成
        print("[6] 等待搜索结果加载...")
        await asyncio.sleep(8)  # 直接等待，不用networkidle
        
        # 截图
        await page.screenshot(path='real_user_test.png', full_page=True)
        print("截图: real_user_test.png")
        
        # 检查URL
        print(f"\n当前URL: {page.url}")
        
        # 检查页面标题
        title = await page.title()
        print(f"页面标题: {title}")
        
        # 查找所有图片（搜索结果应该有图片）
        print("\n[7] 查找页面上的图片...")
        images = await page.evaluate('''() => {
            const imgs = Array.from(document.querySelectorAll('img'));
            return imgs.map(img => ({
                src: img.src.substring(0, 80),
                alt: img.alt || '',
                width: img.width,
                height: img.height
            })).filter(img => img.width > 50 && img.height > 50);
        }''')
        
        print(f"找到 {len(images)} 张大图:")
        for i, img in enumerate(images[:10], 1):
            print(f"{i}. {img['width']}x{img['height']} - {img['src'][:50]}...")
        
        # 查找可能的搜索结果容器
        print("\n[8] 查找搜索结果容器...")
        containers = await page.evaluate('''() => {
            const selectors = [
                '[class*="search"]',
                '[class*="result"]',
                '[class*="list"]',
                '[class*="card"]',
                'ul',
                'main'
            ];
            
            const results = [];
            selectors.forEach(sel => {
                const els = document.querySelectorAll(sel);
                if (els.length > 0 && els.length < 100) {
                    results.push({
                        selector: sel,
                        count: els.length,
                        firstClass: els[0].className.substring(0, 50)
                    });
                }
            });
            return results;
        }''')
        
        for c in containers:
            print(f"  {c['selector']}: {c['count']} 个 - {c['firstClass']}")
        
        # 如果有图片，尝试找图片的父级容器
        if images:
            print("\n[9] 分析图片容器...")
            cardInfo = await page.evaluate('''() => {
                const imgs = Array.from(document.querySelectorAll('img')).filter(img => img.width > 100 && img.height > 100);
                const results = [];
                
                imgs.slice(0, 5).forEach(img => {
                    let parent = img.parentElement;
                    for (let i = 0; i < 5; i++) {
                        if (parent && parent !== document.body) {
                            parent = parent.parentElement;
                        }
                    }
                    
                    if (parent) {
                        const link = parent.querySelector('a');
                        const text = parent.textContent.trim().substring(0, 50);
                        results.push({
                            parentClass: parent.className.substring(0, 50),
                            parentTag: parent.tagName,
                            link: link ? link.href : null,
                            text: text
                        });
                    }
                });
                
                return results;
            }''')
            
            for i, info in enumerate(cardInfo, 1):
                print(f"{i}. {info['parentTag']}.{info['parentClass']}")
                print(f"   文本: {info['text']}")
                print(f"   链接: {info['link']}")
        
        print("\n\n浏览器保持打开，可以手动检查...")
        await asyncio.sleep(120)
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        await page.screenshot(path='error.png')
        await asyncio.sleep(60)
    finally:
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
