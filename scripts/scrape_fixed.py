"""
抖音图文笔记采集脚本 - 修复版

流程：
1. 打开抖音首页
2. 输入关键词搜索
3. 鼠标悬浮筛选 → 选择图文
4. 可选：选择一周内
5. 滚动采集（图片、标题、作者、描述、tag）
6. 计算热度分数 = 点赞数 / 天数
7. 筛选爆款，保存到 SQLite
"""

import argparse
import asyncio
import json
import os
import random
import re
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import quote

from playwright.async_api import async_playwright

# 路径配置
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROFILE_DIR = SKILL_DIR / "profile"
DATA_DIR = SKILL_DIR / "data"
DB_PATH = DATA_DIR / "douyin.db"
IMAGES_DIR = DATA_DIR / "images"


def parse_likes(text):
    """解析点赞数"""
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


def init_db():
    """初始化数据库"""
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
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            publish_date TEXT,
            days_ago INTEGER,
            hot_score REAL,
            ocr_text TEXT,
            source_url TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    # 添加缺失的字段
    try:
        cursor.execute('ALTER TABLE notes ADD COLUMN description TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE notes ADD COLUMN publish_date TEXT')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE notes ADD COLUMN days_ago INTEGER DEFAULT 1')
    except:
        pass
    try:
        cursor.execute('ALTER TABLE notes ADD COLUMN hot_score REAL DEFAULT 0')
    except:
        pass
    
    conn.commit()
    conn.close()


def calculate_hot_score(likes, days_ago):
    """
    计算热度分数
    点赞数 / 天数（最小 1 天）
    """
    if days_ago <= 0:
        days_ago = 1
    return likes / days_ago


def save_note(note):
    """保存笔记到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # 清理无法编码的字符（移除emoji等）
        def clean_text(text):
            if not text:
                return text
            result = []
            for char in text:
                try:
                    char.encode('gbk')
                    result.append(char)
                except:
                    pass  # 跳过无法编码的字符
            return ''.join(result)
        
        cursor.execute('''
            INSERT OR IGNORE INTO notes 
            (keyword, title, author, description, tags, images, likes, publish_date, days_ago, hot_score, source_url, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            clean_text(note['keyword']),
            clean_text(note['title']),
            clean_text(note['author']),
            clean_text(note.get('description', '')),
            json.dumps(note.get('tags', []), ensure_ascii=False),
            json.dumps(note.get('images', []), ensure_ascii=False),
            note['likes'],
            clean_text(note.get('publish_date', '')),
            note.get('days_ago', 1),
            note.get('hot_score', 0),
            note['source_url'],
            note['status']
        ))
        conn.commit()
    finally:
        conn.close()


async def scrape_notes(keyword, count=10, min_likes=100):
    """采集图文笔记"""
    
    # 确保目录存在
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 初始化数据库
    init_db()
    
    async with async_playwright() as p:
        print(f"[启动] 启动浏览器，加载登录状态...")
        
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={'width': 1280, 'height': 800},
            locale='zh-CN',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # 反检测
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        try:
            # ===== 第一步：打开抖音首页 =====
            print(f"[首页] 打开抖音首页...")
            await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(8)  # 增加等待时间
            
            # ===== 第二步：在首页顶部搜索框输入关键词 =====
            print(f"[搜索] 在搜索框输入关键词：{keyword}")
            
            search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=5000)
            await search_input.click()
            await asyncio.sleep(1)
            
            await page.keyboard.type(keyword, delay=100)
            await asyncio.sleep(1)
            
            print(f"  [执行] 按回车搜索...")
            await page.keyboard.press('Enter')
            await asyncio.sleep(8)  # 增加等待时间
            
            # ===== 第三步：鼠标悬浮筛选，选择图文和一周内 =====
            print(f"\n[筛选] 鼠标悬浮到筛选按钮...")
            await asyncio.sleep(2)
            
            try:
                filter_btn = await page.wait_for_selector('xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/span', timeout=5000)
                await filter_btn.hover()
                print(f"  [成功] 已悬浮到筛选按钮")
            except Exception as e:
                print(f"  [失败] 未找到筛选按钮: {e}")
            
            await asyncio.sleep(1)
            
            print(f"  [选择] 点击图文...")
            try:
                image_btn = await page.wait_for_selector('xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/div/div[5]/span[3]', timeout=5000)
                await image_btn.click()
                print(f"  [成功] 已选择图文")
            except Exception as e:
                print(f"  [失败] 未找到图文选项: {e}")
            
            await asyncio.sleep(1)
            
            print(f"  [选择] 点击一周内...")
            try:
                week_btn = await page.query_selector('text=一周内')
                if week_btn:
                    await week_btn.click()
                    print(f"  [成功] 已选择一周内")
                else:
                    print(f"  [!] 未找到一周内选项")
            except Exception as e:
                print(f"  [失败] 未找到一周内: {e}")
            
            await asyncio.sleep(3)
            
            print(f"\n{'='*60}")
            print("筛选完成，2秒后自动开始采集...")
            print(f"{'='*60}\n")
            await asyncio.sleep(2)
            
            # ===== 第四步：开始采集 =====
            print(f"\n[采集] 开始采集笔记（目标：{count} 条）...")
            
            collected = []
            scroll_count = 0
            max_scrolls = 30
            
            while len(collected) < count and scroll_count < max_scrolls:
                await asyncio.sleep(2)
                
                # 找笔记卡片
                cards = await page.query_selector_all('[class*="search-result-card"]')
                
                print(f"  [发现] {len(cards)} 张卡片")
                
                for card in cards:
                    if len(collected) >= count:
                        break

                    try:
                        # 使用JavaScript一次性提取所有信息
                        info = await card.evaluate('''(el) => {
                            const result = {};

                            // 提取描述
                            const descEl = el.querySelector('[class*="Q13_HEtf"]');
                            result.description = descEl ? descEl.textContent.trim() : '';

                            // 提取作者
                            const authorEl = el.querySelector('[class*="VqGyTjMv"]');
                            result.author = authorEl ? authorEl.textContent.trim() : '未知作者';

                            // 提取时间
                            const timeEl = el.querySelector('[class*="eK1bT2_i"]');
                            result.timeText = timeEl ? timeEl.textContent.trim() : '';

                            // 提取点赞
                            const likeContainer = el.querySelector('[class*="TCQQg7so"]');
                            if (likeContainer) {
                                const likeSpan = likeContainer.querySelector('span');
                                result.likesText = likeSpan ? likeSpan.textContent.trim() : '0';
                            } else {
                                result.likesText = '0';
                            }

                            // 提取图片
                            const img = el.querySelector('img');
                            result.imgSrc = img ? img.src : '';

                            return result;
                        }''')

                        if not info['description']:
                            continue

                        # 去重
                        if any(n['description'] == info['description'] for n in collected):
                            continue

                        # 解析点赞数
                        likes = parse_likes(info['likesText'])

                        # 解析时间
                        days_ago = 1
                        time_text = info['timeText']
                        if '小时前' in time_text:
                            days_ago = 0.1
                        elif '天前' in time_text:
                            match = re.search(r'(\d+)天前', time_text)
                            if match:
                                days_ago = int(match.group(1))
                        elif '昨天' in time_text:
                            days_ago = 1

                        # 从描述中提取标签
                        tags = []
                        hashtag_matches = re.findall(r'#([^\s#]+)', info['description'])
                        tags = hashtag_matches[:5]

                        # 提取标题
                        title = info['description'][:50] + ('...' if len(info['description']) > 50 else '')

                        # 计算热度
                        hot_score = calculate_hot_score(likes, days_ago)

                        note = {
                            'keyword': keyword,
                            'title': title,
                            'author': info['author'],
                            'description': info['description'][:500],
                            'tags': tags,
                            'images': [info['imgSrc']] if info['imgSrc'] else [],
                            'likes': likes,
                            'publish_date': time_text.replace(' · ', ''),
                            'days_ago': days_ago,
                            'hot_score': hot_score,
                            'source_url': '',
                            'status': 'pending'
                        }

                        collected.append(note)
                        print(f"  [+] [{len(collected)}] {title[:40]}... (点赞{likes}, {time_text.replace(' · ', '')}, 热度{hot_score:.1f})")

                    except Exception as e:
                        continue
                
                # 滚动加载更多
                if len(collected) < count:
                    await page.mouse.wheel(0, 500)
                    scroll_count += 1
                    await asyncio.sleep(2)
            
            # ===== 第五步：按热度排序并保存 =====
            print(f"\n[排序] 按热度分数排序...")
            collected.sort(key=lambda x: x['hot_score'], reverse=True)
            
            print(f"\n[保存] 保存到数据库...")
            saved_count = 0
            for i, note in enumerate(collected[:count]):
                try:
                    save_note(note)
                    saved_count += 1
                    print(f"  [{i+1}] {note['title'][:40]}... (热度{note['hot_score']:.1f})")
                except Exception as e:
                    print(f"  [错误] 保存失败: {e}")
            
            print(f"\n[完成] 采集完成")
            print(f"  - 收集: {len(collected)} 条")
            print(f"  - 保存: {saved_count} 条")
            print(f"  - 数据库: {DB_PATH}")
            
        except Exception as e:
            print(f"[错误] 采集失败: {e}")
            import traceback
            traceback.print_exc()
            await page.screenshot(path=str(SKILL_DIR / "debug_error.png"))
        
        finally:
            print(f"\n[关闭] 浏览器关闭中...")
            await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='抖音图文笔记采集')
    parser.add_argument('--keyword', required=True, help='搜索关键词')
    parser.add_argument('--count', type=int, default=10, help='采集数量')
    parser.add_argument('--min-likes', type=int, default=100, help='最低点赞数')
    
    args = parser.parse_args()
    
    asyncio.run(scrape_notes(args.keyword, args.count, args.min_likes))
