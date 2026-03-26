#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音图文笔记采集+OCR一体化脚本 v3

策略：直接在搜索结果页提取卡片信息，点击获取详情页图片
"""

import argparse
import asyncio
import base64
import json
import os
import random
import re
import sqlite3
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from playwright.async_api import async_playwright

# 路径配置
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROFILE_DIR = SKILL_DIR / "profile"
DATA_DIR = SKILL_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
DB_PATH = DATA_DIR / "douyin.db"
OUTPUT_DIR = SKILL_DIR / "output"

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(SKILL_DIR / ".env")
except ImportError:
    pass

# OCR配置
OCR_API_URL = os.getenv("BAIDU_PADDLEOCR_API_URL", "https://r41cd0p9x7dfp1s7.aistudio-app.com/layout-parsing")
OCR_API_TOKEN = os.getenv("BAIDU_PADDLEOCR_TOKEN", "")


def check_ocr_config():
    """检查OCR配置"""
    if not OCR_API_TOKEN:
        print("\n" + "="*60)
        print("错误：未配置百度PaddleOCR Token")
        print("="*60)
        print("\n配置方法：")
        print("1. 在技能目录创建 .env 文件")
        print("2. 填写：BAIDU_PADDLEOCR_TOKEN=your_token")
        print("="*60)
        return False
    return True


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT,
            title TEXT,
            author TEXT,
            description TEXT,
            tags TEXT,
            images TEXT,
            local_images TEXT,
            likes INTEGER DEFAULT 0,
            publish_date TEXT,
            days_ago INTEGER,
            hot_score REAL,
            ocr_text TEXT,
            source_url TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    ''')
    try:
        cursor.execute('ALTER TABLE notes ADD COLUMN local_images TEXT')
    except:
        pass
    conn.commit()
    conn.close()


def parse_likes(text):
    try:
        text = text.strip().lower()
        if '万' in text:
            return int(float(text.replace('万', '')) * 10000)
        elif 'w' in text:
            return int(float(text.replace('w', '')) * 10000)
        else:
            return int(text)
    except:
        return 0


def calculate_hot_score(likes, days_ago):
    if days_ago <= 0:
        days_ago = 1
    return likes / days_ago


def clean_text(text):
    if not text:
        return text
    return ''.join(c for c in text if c.isascii() or '\u4e00' <= c <= '\u9fff')


def save_note(note):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO notes 
            (keyword, title, author, description, tags, images, local_images, likes, publish_date, days_ago, hot_score, ocr_text, source_url, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            note['keyword'], note['title'], note['author'],
            note.get('description', ''),
            json.dumps(note.get('tags', []), ensure_ascii=False),
            json.dumps(note.get('images', []), ensure_ascii=False),
            json.dumps(note.get('local_images', []), ensure_ascii=False),
            note['likes'], note.get('publish_date', ''),
            note.get('days_ago', 1), note.get('hot_score', 0),
            note.get('ocr_text', ''), note['source_url'], note['status']
        ))
        conn.commit()
    finally:
        conn.close()


async def download_image_in_browser(page, img_url, save_path):
    try:
        result = await page.evaluate('''
            async (url) => {
                try {
                    const response = await fetch(url);
                    const blob = await response.blob();
                    return new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                } catch (e) {
                    return null;
                }
            }
        ''', img_url)
        
        if result and result.startswith('data:'):
            base64_data = result.split(',', 1)[1]
            img_data = base64.b64decode(base64_data)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(img_data)
            return True
        return False
    except:
        return False


def ocr_with_baidu(image_path: str) -> str:
    if not OCR_API_TOKEN:
        return ""
    
    try:
        import requests
        with open(image_path, "rb") as f:
            file_data = base64.b64encode(f.read()).decode("ascii")
        
        headers = {
            "Authorization": f"token {OCR_API_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "file": file_data,
            "fileType": 1,
            "useDocOrientationClassify": False,
            "useDocUnwarping": False,
            "useChartRecognition": False,
        }
        
        response = requests.post(OCR_API_URL, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            return ""
        
        result = response.json().get("result", {})
        layout_results = result.get("layoutParsingResults", [])
        
        all_text = []
        for res in layout_results:
            md_text = res.get("markdown", {}).get("text", "")
            if md_text.strip():
                all_text.append(md_text.strip())
        
        return "\n\n".join(all_text)
    except:
        return ""


async def scrape_and_ocr(keyword, count=10, do_ocr=True):
    """采集图文笔记并OCR识别"""
    
    # 检查OCR配置
    if do_ocr and not check_ocr_config():
        return []
    
    # 确保目录存在
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    init_db()
    
    keyword_images_dir = IMAGES_DIR / keyword
    keyword_images_dir.mkdir(parents=True, exist_ok=True)
    
    collected = []
    
    async with async_playwright() as p:
        print(f"[启动] 启动浏览器...")
        
        # 使用持久化模式保持登录状态，避免抖音检测
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={'width': 1400, 'height': 900},
            locale='zh-CN',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
            ]
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        
        try:
            # 打开抖音搜索页
            search_url = f"https://www.douyin.com/search/{keyword}?type=post"
            print(f"[搜索] 打开：{search_url}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)
            
            print(f"\n{'='*60}")
            print(f"开始采集（目标：{count}条）")
            print(f"{'='*60}\n")
            
            # 采集
            scroll_count = 0
            max_scrolls = 50
            
            while len(collected) < count and scroll_count < max_scrolls:
                await asyncio.sleep(2)
                
                # 使用JavaScript获取所有图文卡片信息
                cards_info = await page.evaluate('''() => {
                    const results = [];
                    
                    // 找所有搜索结果容器
                    const containers = document.querySelectorAll('[class*="search-result"]');
                    
                    containers.forEach((container, idx) => {
                        try {
                            // 检查是否包含"图文"标记
                            const hasImageText = container.textContent.includes('图文');
                            if (!hasImageText) return;
                            
                            // 提取描述
                            let description = '';
                            const textEls = container.querySelectorAll('span, p, div');
                            for (const el of textEls) {
                                const text = el.textContent.trim();
                                if (text.length > 20 && !text.includes('图文') && !text.includes('相关搜索') && !text.includes('问问AI')) {
                                    description = text;
                                    break;
                                }
                            }
                            
                            if (!description || description.length < 10) return;
                            
                            // 提取作者
                            let author = '未知作者';
                            const authorEl = container.querySelector('a[href*="/user/"]');
                            if (authorEl) {
                                author = authorEl.textContent.trim() || '未知作者';
                            }
                            
                            // 提取时间
                            let timeText = '';
                            const timeMatch = container.textContent.match(/(\d+天前|\d+小时前|\d+月\d+日|\d+年\d+月\d+日)/);
                            if (timeMatch) {
                                timeText = timeMatch[1];
                            }
                            
                            // 提取点赞数 - 找图文后面的数字
                            let likes = '0';
                            const fullText = container.textContent;
                            // 找"图文"后面的数字
                            const likePattern = /图文[^\d]*(\d+(?:\.\d+)?[万w]?)/;
                            const likeMatch = fullText.match(likePattern);
                            if (likeMatch) {
                                likes = likeMatch[1];
                            }
                            
                            // 提取图片
                            const imgs = container.querySelectorAll('img');
                            const imgSrc = imgs.length > 0 ? imgs[0].src : '';
                            
                            results.push({
                                index: idx,
                                description: description.substring(0, 200),
                                author: author,
                                timeText: timeText,
                                likesText: likes,
                                imgSrc: imgSrc
                            });
                        } catch (e) {}
                    });
                    
                    return results;
                }''')
                
                print(f"  [发现] {len(cards_info)} 张图文卡片，已采集 {len(collected)} 条")
                
                for info in cards_info:
                    if len(collected) >= count:
                        break
                    
                    try:
                        description = info['description']
                        
                        # 去重
                        desc_key = description[:50]
                        if any(n.get('description', '')[:50] == desc_key for n in collected):
                            continue
                        
                        # 解析点赞
                        likes = parse_likes(info.get('likesText', '0'))
                        
                        # 解析时间
                        days_ago = 1
                        time_text = info.get('timeText', '')
                        if '小时前' in time_text:
                            days_ago = 0.1
                        elif '天前' in time_text:
                            match = re.search(r'(\d+)天前', time_text)
                            if match:
                                days_ago = int(match.group(1))
                        
                        # 热度
                        hot_score = calculate_hot_score(likes, days_ago)
                        
                        # 标签
                        tags = re.findall(r'#([^\s#]+)', description)[:5]
                        
                        # 标题
                        title = description[:50] + ('...' if len(description) > 50 else '')
                        
                        print(f"\n[{len(collected)+1}] {title[:40]}...")
                        print(f"    点赞: {likes}, 时间: {time_text}, 热度: {hot_score:.1f}")
                        
                        # 点击卡片 - 使用更精确的选择器
                        current_url = page.url
                        
                        # 找到这个卡片并点击
                        clicked = await page.evaluate(f'''(description) => {{
                            const containers = document.querySelectorAll('[class*="search-result"]');
                            for (const container of containers) {{
                                if (container.textContent.includes("{description[:30]}")) {{
                                    container.click();
                                    return true;
                                }}
                            }}
                            return false;
                        }}''', description)
                        
                        if not clicked:
                            print(f"    [跳过] 无法点击卡片")
                            continue
                        
                        await asyncio.sleep(3)
                        
                        note_url = page.url
                        
                        # 检查是否跳转成功
                        if note_url == current_url or 'search' in note_url:
                            print(f"    [跳过] 未跳转到详情页")
                            continue
                        
                        print(f"    详情页: {note_url[:60]}...")
                        
                        # 获取详情页所有图片
                        try:
                            await asyncio.sleep(2)
                            
                            # 获取所有图片URL
                            img_urls = await page.evaluate('''() => {
                                const urls = [];
                                const imgs = document.querySelectorAll('img');
                                imgs.forEach(img => {
                                    if (img.src && (img.src.includes('douyinpic.com') || img.src.includes('tos-'))) {
                                        // 排除头像和头像相关
                                        if (!img.src.includes('avatar') && !img.src.includes('aweme-avatar')) {
                                            urls.push(img.src);
                                        }
                                    }
                                });
                                return urls;
                            }''')
                            
                            print(f"    发现 {len(img_urls)} 张图片")
                            
                            local_images = []
                            all_ocr_text = []
                            
                            for i, img_url in enumerate(img_urls[:9]):
                                img_name = f"{keyword}_{len(collected)+1}_{i+1}.jpg"
                                save_path = keyword_images_dir / img_name
                                
                                print(f"    下载图片 {i+1}...", end='')
                                
                                if await download_image_in_browser(page, img_url, save_path):
                                    local_images.append(str(save_path))
                                    print(f" ✓")
                                    
                                    if do_ocr:
                                        print(f"    OCR识别中...", end='')
                                        ocr_text = ocr_with_baidu(str(save_path))
                                        if ocr_text:
                                            all_ocr_text.append(ocr_text)
                                            print(f" ✓ ({len(ocr_text)}字)")
                                        else:
                                            print(f" 无结果")
                                else:
                                    print(f" ✗")
                                
                                await asyncio.sleep(0.3)
                            
                            # 保存笔记
                            note = {
                                'keyword': keyword,
                                'title': title,
                                'author': info.get('author', '未知作者'),
                                'description': description[:500],
                                'tags': tags,
                                'images': [info.get('imgSrc', '')] if info.get('imgSrc') else [],
                                'local_images': local_images,
                                'likes': likes,
                                'publish_date': time_text,
                                'days_ago': days_ago,
                                'hot_score': hot_score,
                                'ocr_text': '\n\n'.join(all_ocr_text),
                                'source_url': note_url,
                                'status': 'completed'
                            }
                            
                            save_note(note)
                            collected.append(note)
                            
                        except Exception as e:
                            print(f"    [详情页错误] {e}")
                        
                        # 返回搜索结果页
                        await page.go_back()
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        print(f"    [卡片处理错误] {e}")
                        continue
                
                # 滚动加载更多
                if len(collected) < count:
                    await page.mouse.wheel(0, 800)
                    scroll_count += 1
                    await asyncio.sleep(2)
            
            print(f"\n{'='*60}")
            print(f"采集完成！共采集 {len(collected)} 条笔记")
            print(f"{'='*60}")
            
            # 导出Markdown
            export_markdown(keyword, collected)
            
        except Exception as e:
            print(f"[错误] {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            print(f"\n[关闭] 浏览器关闭中...")
            await browser.close()
    
    return collected


def export_markdown(keyword, notes):
    """导出Markdown报告"""
    if not notes:
        return
    
    notes.sort(key=lambda x: x['hot_score'], reverse=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"notes_{keyword}_{timestamp}.md"
    filepath = OUTPUT_DIR / filename
    
    lines = [
        f"# 抖音图文笔记采集报告",
        f"",
        f"**关键词**：{keyword}",
        f"",
        f"**采集时间**：{time.strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"**笔记数量**：{len(notes)} 条",
        f"",
        f"---",
        f"",
    ]
    
    for i, note in enumerate(notes, 1):
        lines.extend([
            f"## 笔记 {i}",
            f"",
            f"**🔥 热度分数**：{note['hot_score']:.2f} 分",
            f"",
            f"**📈 热度计算**：{note['likes']}赞 / {note['days_ago']}天 = **{note['hot_score']:.2f}分**",
            f"",
            f"**👍 点赞数**：{note['likes']}",
            f"",
            f"**👤 作者**：{note['author']}",
            f"",
            f"### 📝 笔记内容（OCR识别）",
            f"",
        ])
        
        if note.get('ocr_text'):
            lines.append(note['ocr_text'])
        else:
            lines.append(note.get('description', '无内容'))
        
        lines.extend([f"", f"---", f""])
    
    total_likes = sum(n['likes'] for n in notes)
    avg_hot = sum(n['hot_score'] for n in notes) / len(notes)
    
    lines.extend([
        f"## 📊 统计",
        f"",
        f"- 总点赞数：{total_likes:,}",
        f"- 平均热度：{avg_hot:.1f}",
        f"",
        f"---",
        f"",
        f"*生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}*",
    ])
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"\n[导出] Markdown报告：{filepath}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='抖音图文笔记采集+OCR一体化')
    parser.add_argument('--keyword', required=True, help='搜索关键词')
    parser.add_argument('--count', type=int, default=10, help='采集数量（默认10）')
    parser.add_argument('--no-ocr', action='store_true', help='跳过OCR识别')
    
    args = parser.parse_args()
    
    asyncio.run(scrape_and_ocr(args.keyword, args.count, do_ocr=not args.no_ocr))
