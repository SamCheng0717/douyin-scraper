"""
调试脚本 - 检查抖音搜索结果页面的当前结构
"""
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
PROFILE_DIR = SKILL_DIR / "profile"

async def debug():
    async with async_playwright() as p:
        print("[启动] 浏览器...")
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={'width': 1280, 'height': 800},
            locale='zh-CN',
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        try:
            # 打开抖音
            print("[首页] 打开抖音...")
            await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(8)
            
            # 搜索
            print("[搜索] 输入关键词...")
            search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=5000)
            await search_input.click()
            await asyncio.sleep(1)
            await page.keyboard.type("美食", delay=100)
            await asyncio.sleep(1)
            await page.keyboard.press('Enter')
            await asyncio.sleep(8)
            
            # 筛选图文
            print("[筛选] 选择图文...")
            try:
                filter_btn = await page.wait_for_selector('xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/span', timeout=5000)
                await filter_btn.hover()
                await asyncio.sleep(1)
                image_btn = await page.wait_for_selector('xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/div/div[5]/span[3]', timeout=5000)
                await image_btn.click()
                await asyncio.sleep(3)
            except Exception as e:
                print(f"  筛选失败: {e}")
            
            # 截图
            await page.screenshot(path=str(SKILL_DIR / "debug_current_page.png"))
            print("[截图] 已保存 debug_current_page.png")
            
            # 获取卡片
            cards = await page.query_selector_all('[class*="search-result-card"]')
            print(f"\n[发现] {len(cards)} 张卡片")
            
            if cards:
                # 检查第一张卡片的HTML结构
                first_card = cards[0]
                html = await first_card.inner_html()
                
                # 保存HTML
                with open(SKILL_DIR / "debug_card_html.txt", 'w', encoding='utf-8') as f:
                    f.write(html)
                print("[HTML] 已保存卡片HTML到 debug_card_html.txt")
                
                # 提取所有class名
                import re
                classes = re.findall(r'class="([^"]+)"', html)
                unique_classes = set()
                for c in classes:
                    for cls in c.split():
                        unique_classes.add(cls)
                
                print(f"\n[Class] 找到 {len(unique_classes)} 个唯一class:")
                # 显示包含特定关键词的class
                keywords = ['desc', 'author', 'time', 'like', 'title', 'text']
                for cls in sorted(unique_classes):
                    for kw in keywords:
                        if kw in cls.lower():
                            print(f"  - {cls}")
                            break
                
                # 尝试用JavaScript提取
                print("\n[测试] JavaScript提取...")
                info = await first_card.evaluate('''(el) => {
                    const result = {};
                    
                    // 列出所有子元素的class
                    const allElements = el.querySelectorAll('*');
                    const classes = [];
                    allElements.forEach(e => {
                        if (e.className && typeof e.className === 'string') {
                            classes.push(e.className);
                        }
                    });
                    result.allClasses = classes;
                    
                    // 尝试找描述
                    const descSelectors = [
                        '[class*="Q13_HEtf"]',
                        '[class*="desc"]',
                        '[class*="description"]',
                        '[class*="title"]',
                        'h3',
                        'h2'
                    ];
                    for (const sel of descSelectors) {
                        const el = el.querySelector(sel);
                        if (el) {
                            result.desc = el.textContent.trim();
                            result.descClass = el.className;
                            break;
                        }
                    }
                    
                    // 尝试找作者
                    const authorSelectors = [
                        '[class*="VqGyTjMv"]',
                        '[class*="author"]',
                        '[class*="user"]',
                        '[class*="name"]'
                    ];
                    for (const sel of authorSelectors) {
                        const el = el.querySelector(sel);
                        if (el) {
                            result.author = el.textContent.trim();
                            result.authorClass = el.className;
                            break;
                        }
                    }
                    
                    return result;
                }''')
                
                print(f"  描述: {info.get('desc', 'N/A')}")
                print(f"  描述Class: {info.get('descClass', 'N/A')}")
                print(f"  作者: {info.get('author', 'N/A')}")
                print(f"  作者Class: {info.get('authorClass', 'N/A')}")
                
                print("\n[等待] 浏览器保持打开，按Ctrl+C关闭...")
                await asyncio.sleep(300)
            
        except KeyboardInterrupt:
            print("\n[关闭] 用户中断")
        except Exception as e:
            print(f"[错误] {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
