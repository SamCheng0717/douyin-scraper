#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音图文笔记采集脚本 - 拟人化操作
严格按照人类操作流程：登录 → 首页 → 搜索 → 筛选 → 采集 → 滚动判断 → 关闭
"""

import sys
import os
import re
import random
import asyncio
import json
import hashlib
from pathlib import Path
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("请安装 playwright: pip install playwright")
    sys.exit(1)

import db
import ocr as ocr_module

# 目录配置
PROFILE_DIR = Path(__file__).parent.parent / "profile"
DATA_DIR = Path(__file__).parent.parent / "data"
IMAGES_DIR = DATA_DIR / "images"


def ensure_dir():
    """确保目录存在"""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)


def parse_likes(text):
    """解析点赞数"""
    if not text:
        return 0
    text = text.strip().lower()
    try:
        if '万' in text or 'w' in text:
            num = float(re.search(r'[\d.]+', text).group())
            return int(num * 10000)
        return int(text)
    except:
        return 0


def calculate_hot_score(likes, days_ago):
    """计算热度分数"""
    if days_ago <= 0:
        days_ago = 1
    return likes / days_ago


async def human_delay(min_sec=1, max_sec=3):
    """模拟人类操作的随机延迟"""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)


async def download_image(page, img_url, save_path):
    """在浏览器环境下载图片"""
    try:
        result = await page.evaluate('''async (url) => {
            try {
                const response = await fetch(url);
                const blob = await response.blob();
                const reader = new FileReader();
                return new Promise((resolve) => {
                    reader.onloadend = () => {
                        resolve({
                            success: true,
                            data: reader.result.split(',')[1],
                            type: blob.type
                        });
                    };
                    reader.onerror = () => {
                        resolve({ success: false });
                    };
                    reader.readAsDataURL(blob);
                });
            } catch (e) {
                return { success: false, error: e.message };
            }
        }''', img_url)
        
        if result.get('success'):
            import base64
            img_data = base64.b64decode(result['data'])
            with open(save_path, 'wb') as f:
                f.write(img_data)
            return True
        return False
    except Exception as e:
        print(f"    [错误] 下载异常: {e}")
        return False


async def scrape_with_images(keyword, count=10, do_ocr=True):
    """采集图文笔记并下载图片 - 拟人化流程"""
    ensure_dir()
    
    async with async_playwright() as p:
        print(f"[启动] 启动浏览器，加载登录状态...")
        
        # 使用持久化模式（保持登录）
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={'width': 1400, 'height': 900},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
            ]
        )
        
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        # ===== 步骤1：进入抖音首页 =====
        print(f"\n[步骤1] 进入抖音首页...")
        await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=60000)
        await human_delay(5, 8)  # 等待页面完全加载和可能的301跳转
        
        # 检查是否跳转到jingxuan
        current_url = page.url
        print(f"  当前URL: {current_url}")
        
        # ===== 步骤2：点击搜索框，输入关键词 =====
        print(f"\n[步骤2] 点击搜索框，输入关键词：{keyword}")
        
        # 找到搜索框
        search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=10000)
        await human_delay(0.5, 1.5)
        
        # 模拟人类点击
        await search_input.click()
        await human_delay(0.5, 1)
        
        # 模拟人类打字速度
        for char in keyword:
            await page.keyboard.type(char, delay=random.randint(50, 150))
        
        await human_delay(0.5, 1.5)
        
        # 点击搜索按钮（不是按回车）
        print(f"  点击搜索按钮...")
        search_btn = await page.wait_for_selector('button[type="submit"], button:has-text("搜索")', timeout=5000)
        if search_btn:
            await search_btn.click()
        else:
            # 备用：按回车
            await page.keyboard.press('Enter')
        
        await human_delay(3, 5)  # 等待搜索结果加载
        
        # ===== 步骤3：筛选 - 1周内 + 图文 =====
        print(f"\n[步骤3] 筛选图文和一周内...")
        
        # 先等待搜索结果页面稳定
        await human_delay(2, 3)
        
        # 悬浮到筛选按钮
        print(f"  悬浮到筛选按钮...")
        filter_selectors = [
            'xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/span',
            'span:has-text("筛选")',
            '[class*="filter"]'
        ]
        
        filter_btn = None
        for selector in filter_selectors:
            try:
                filter_btn = await page.wait_for_selector(selector, timeout=3000)
                if filter_btn:
                    print(f"    找到筛选按钮: {selector}")
                    break
            except:
                continue
        
        if filter_btn:
            await filter_btn.hover()
            await human_delay(1, 2)
            
            # 点击"图文"
            print(f"  点击图文...")
            image_selectors = [
                'xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/div/div[5]/span[3]',
                'span:has-text("图文")',
                '[class*="image-text"]'
            ]
            
            for selector in image_selectors:
                try:
                    image_btn = await page.wait_for_selector(selector, timeout=2000)
                    if image_btn:
                        await image_btn.click()
                        await human_delay(0.5, 1)
                        print(f"    已选择图文")
                        break
                except:
                    continue
            
            # 悬浮回筛选按钮
            await filter_btn.hover()
            await human_delay(0.5, 1)
            
            # 点击"一周内"
            print(f"  点击一周内...")
            week_selectors = [
                'text=一周内',
                'span:has-text("一周内")',
                '[class*="week"]'
            ]
            
            for selector in week_selectors:
                try:
                    week_btn = await page.wait_for_selector(selector, timeout=2000)
                    if week_btn:
                        await week_btn.click()
                        await human_delay(0.5, 1)
                        print(f"    已选择一周内")
                        break
                except:
                    continue
        
        await human_delay(3, 5)  # 等待筛选结果加载
        
        # ===== 步骤4：采集笔记 =====
        print(f"\n{'='*60}")
        print(f"开始采集 {count} 篇笔记...")
        print(f"{'='*60}\n")
        
        collected = []
        processed_urls = set()
        scroll_count = 0
        max_scrolls = 2  # 最多滚动2次
        no_new_content_count = 0
        
        while len(collected) < count:
            await human_delay(2, 3)
            
            # 找卡片
            cards = await page.query_selector_all('[class*="search-result-card"]')
            print(f"  [发现] {len(cards)} 张卡片")
            
            new_cards_count = 0
            
            for idx in range(min(len(cards), count * 2)):  # 预留一些buffer
                if len(collected) >= count:
                    break
                
                try:
                    # 每次重新获取卡片，避免DOM失效
                    cards = await page.query_selector_all('[class*="search-result-card"]')
                    if idx >= len(cards):
                        break
                    
                    card = cards[idx]
                    
                    print(f"  [处理] 卡片{idx+1}/{len(cards)}")
                    
                    # 提取卡片基本信息
                    info = await card.evaluate('''(card) => {
                        const result = {};
                        
                        // 描述
                        const allSpans = card.querySelectorAll('span');
                        for (const span of allSpans) {
                            const text = span.textContent.trim();
                            if (text.length > 10 && !text.includes('#') && !text.includes('展开')) {
                                result.description = text;
                                break;
                            }
                        }
                        if (!result.description) result.description = '';
                        
                        // 作者
                        const authorEl = card.querySelector('[class*="TLKbIZlL"], [class*="arnSiSbK"], a[href*="/user/"]');
                        result.author = authorEl ? authorEl.textContent.trim() : '未知作者';
                        
                        // 时间
                        const timeEl = card.querySelector('[class*="NKitpZ1j"]');
                        result.timeText = timeEl ? timeEl.textContent.trim() : '';
                        
                        // 点赞
                        const likeEl = card.querySelector('[class*="KV_gO8oI"]');
                        result.likesText = likeEl ? likeEl.textContent.trim() : '0';
                        
                        // 封面图
                        const mainImg = card.querySelector('img[src*="douyinpic.com"]');
                        result.imgSrc = mainImg ? mainImg.src : '';
                        
                        return result;
                    }''')
                    
                    if not info['description']:
                        print(f"    [跳过] 无描述")
                        continue
                    
                    # 去重
                    desc_key = info['description'][:50]
                    if any(n['description'][:50] == desc_key for n in collected):
                        print(f"    [跳过] 重复内容")
                        continue
                    
                    new_cards_count += 1
                    
                    # 点击卡片进入详情页
                    print(f"\n[{len(collected)+1}] 点击卡片...")
                    current_url = page.url
                    
                    await card.click()
                    await human_delay(3, 5)  # 等待详情页加载
                    
                    note_url = page.url
                    if note_url in processed_urls or note_url == current_url:
                        await page.go_back()
                        await human_delay(2, 3)
                        continue
                    
                    processed_urls.add(note_url)
                    
                    # 提取详情页图片
                    print(f"  [提取] 详情页图片...")
                    images = await page.evaluate('''() => {
                        const imgs = [];
                        const allImgs = document.querySelectorAll('img[src*="douyinpic.com"]');
                        allImgs.forEach(img => {
                            if (img.width > 200 && img.height > 200) {
                                imgs.push(img.src);
                            }
                        });
                        return imgs;
                    }''')
                    
                    if not images:
                        images = [info['imgSrc']] if info['imgSrc'] else []
                    
                    print(f"  [发现] {len(images)} 张图片")
                    
                    # 下载图片
                    local_images = []
                    for idx, img_url in enumerate(images[:5]):
                        if not img_url:
                            continue
                        
                        url_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
                        img_name = f"{keyword}_{len(collected)+1}_{idx+1}_{url_hash}.jpg"
                        img_path = IMAGES_DIR / img_name
                        
                        print(f"  [下载] 第{idx+1}张图片...")
                        if await download_image(page, img_url, img_path):
                            local_images.append(str(img_path))
                            print(f"  [完成] 已保存: {img_name}")
                        else:
                            print(f"  [失败] 下载失败")
                    
                    # 返回列表页
                    await page.go_back()
                    await human_delay(2, 3)
                    
                    # 解析数据
                    likes = parse_likes(info['likesText'])
                    
                    days_ago = 1
                    time_text = info['timeText']
                    if '小时前' in time_text:
                        days_ago = 0.1
                    elif '天前' in time_text:
                        match = re.search(r'(\d+)天前', time_text)
                        if match:
                            days_ago = int(match.group(1))
                    
                    tags = re.findall(r'#([^\s#]+)', info['description'])[:5]
                    title = info['description'][:50] + ('...' if len(info['description']) > 50 else '')
                    hot_score = calculate_hot_score(likes, days_ago)
                    
                    note = {
                        'keyword': keyword,
                        'title': title,
                        'author': info['author'],
                        'description': info['description'][:500],
                        'tags': tags,
                        'images': local_images,
                        'likes': likes,
                        'publish_date': time_text,
                        'days_ago': days_ago,
                        'hot_score': hot_score,
                        'source_url': note_url,
                        'status': 'pending'
                    }
                    
                    # OCR识别
                    if do_ocr and local_images:
                        print(f"  [OCR] 识别图片文字...")
                        ocr_text = ocr_module.ocr_images(local_images)
                        
                        if ocr_text:
                            note['ocr_text'] = ocr_text
                            note['status'] = 'ocr_done'
                            print(f"  [OCR] 识别完成: {len(ocr_text)} 字符")
                        else:
                            print(f"  [OCR] 无识别结果")
                    
                    collected.append(note)
                    print(f"  [完成] 采集成功 (点赞{likes}, 热度{hot_score:.1f})")
                    
                except Exception as e:
                    print(f"  [错误] 采集失败: {e}")
                    try:
                        await page.go_back()
                        await human_delay(2, 3)
                    except:
                        pass
                    continue
            
            # ===== 滚动判断 =====
            if len(collected) < count and scroll_count < max_scrolls:
                print(f"\n[滚动] 第{scroll_count + 1}次滚动...")
                
                # 记录当前卡片数量
                cards_before = len(cards)
                
                # 滚动
                await page.mouse.wheel(0, 800)
                await human_delay(3, 5)
                
                # 检查是否有新内容
                cards_after = await page.query_selector_all('[class*="search-result-card"]')
                
                if len(cards_after) <= cards_before:
                    print(f"  [判断] 没有新内容，停止采集")
                    break
                else:
                    print(f"  [判断] 发现新内容，继续采集")
                    scroll_count += 1
            else:
                break
        
        # ===== 步骤5：保存并关闭 =====
        print(f"\n[排序] 按热度排序...")
        collected.sort(key=lambda x: x['hot_score'], reverse=True)
        
        print(f"\n[保存] 保存到数据库...")
        saved_count = 0
        for note in collected[:count]:
            try:
                note_id = db.insert_note(
                    keyword=note['keyword'],
                    title=note['title'],
                    author=note['author'],
                    description=note['description'],
                    tags=note.get('tags', []),
                    images=note.get('images', []),
                    likes=note.get('likes', 0),
                    publish_date=note.get('publish_date', ''),
                    days_ago=note.get('days_ago', 1),
                    hot_score=note.get('hot_score', 0),
                    source_url=note['source_url'],
                    ocr_text=note.get('ocr_text')  # 传递OCR文本
                )
                
                if note_id:
                    saved_count += 1
                    print(f"  [{saved_count}] {note['title'][:40]}... (热度{note['hot_score']:.1f})")
                else:
                    print(f"  [跳过] 重复URL: {note['title'][:40]}...")
            except Exception as e:
                print(f"  [错误] 保存失败: {e}")
        
        print(f"\n[完成] 采集完成")
        print(f"  - 采集: {len(collected)} 条")
        print(f"  - 保存: {saved_count} 条")
        print(f"  - 图片: {IMAGES_DIR}")
        
        # 关闭浏览器
        print(f"\n[关闭] 浏览器关闭中...")
        await browser.close()
        
        return collected


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='抖音图文笔记采集 - 拟人化操作')
    parser.add_argument('--keyword', required=True, help='搜索关键词')
    parser.add_argument('--count', type=int, default=10, help='采集数量')
    parser.add_argument('--no-ocr', action='store_true', help='跳过OCR识别')
    
    args = parser.parse_args()
    
    db.init_db()
    asyncio.run(scrape_with_images(args.keyword, args.count, do_ocr=not args.no_ocr))
