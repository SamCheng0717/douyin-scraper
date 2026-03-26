#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音图文笔记采集 + OCR + Markdown 输出（无 SQLite）

流程：
1. 搜索关键词 → 筛选图文 + 一周内
2. 从列表页提取 waterfall_item_* 中的 note ID
3. 逐个打开 https://www.douyin.com/note/{id}，抓取详情
4. Playwright element.screenshot() 截图图片（绕过 URL 反爬）
5. 立即 OCR，生成 Markdown 报告
"""

import argparse
import asyncio
import base64
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PROFILE_DIR = SKILL_DIR / "profile"
IMAGES_DIR = SKILL_DIR / "data" / "images"
OUTPUT_DIR = SKILL_DIR / "output"

try:
    from dotenv import load_dotenv
    load_dotenv(SKILL_DIR / ".env")
except ImportError:
    pass

OCR_API_URL = os.getenv("BAIDU_PADDLEOCR_API_URL", "https://r41cd0p9x7dfp1s7.aistudio-app.com/layout-parsing")
OCR_TOKEN = os.getenv("BAIDU_PADDLEOCR_TOKEN", "")


# ─────────────────────────── OCR ────────────────────────────

def ocr_image_file(path: Path) -> str:
    if not OCR_TOKEN:
        return ""
    try:
        import requests
    except ImportError:
        return ""

    with open(path, "rb") as f:
        file_data = base64.b64encode(f.read()).decode("ascii")

    headers = {"Authorization": f"token {OCR_TOKEN}", "Content-Type": "application/json"}
    payload = {"file": file_data, "fileType": 1,
                "useDocOrientationClassify": False,
                "useDocUnwarping": False,
                "useChartRecognition": False}
    try:
        resp = requests.post(OCR_API_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            print(f"  [OCR错误] {resp.status_code}: {resp.text[:100]}")
            return ""
        results = resp.json().get("result", {}).get("layoutParsingResults", [])
        texts = [r.get("markdown", {}).get("text", "").strip() for r in results]
        return "\n\n".join(t for t in texts if t)
    except Exception as e:
        print(f"  [OCR异常] {e}")
        return ""


# ────────────────────── 工具函数 ────────────────────────────

def parse_likes(text: str) -> int:
    try:
        text = text.strip().lower()
        if "万" in text:
            return int(float(text.replace("万", "")) * 10000)
        if "w" in text:
            return int(float(text.replace("w", "")) * 10000)
        return int(text)
    except Exception:
        return 0


def parse_days_ago(text: str) -> float:
    if not text:
        return 1
    if "小时前" in text or "分钟前" in text:
        return 0.1
    if "昨天" in text:
        return 1
    m = re.search(r"(\d+)天前", text)
    if m:
        return int(m.group(1))
    return 1


# ─────────────── 列表页：提取 note ID ──────────────────

async def collect_note_ids(page, count: int) -> list:
    """从搜索结果列表页滚动提取 waterfall_item_* IDs"""
    seen = set()
    ids = []
    scroll_count = 0

    while len(ids) < count and scroll_count < 30:
        await asyncio.sleep(2)
        new_ids = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('[id^="waterfall_item_"]'))
                .filter(el => {
                    // 只保留包含"图文"标签的卡片（排除视频）
                    const text = el.textContent;
                    return text.includes('图文');
                })
                .map(el => el.id.replace('waterfall_item_', ''));
        }""")
        for nid in new_ids:
            if nid not in seen:
                seen.add(nid)
                ids.append(nid)
        print(f"  [列表] 已发现 {len(ids)} 个图文 ID")
        if len(ids) < count:
            await page.mouse.wheel(0, 800)
            scroll_count += 1

    return ids[:count]


# ─────────────── 详情页：抓数据 + 截图 + OCR ──────────────

async def process_note(page, note_id: str, idx: int, keyword: str, no_ocr: bool) -> dict:
    """打开笔记详情页，提取所有信息，截图图片，OCR"""
    url = f"https://www.douyin.com/note/{note_id}"
    note = {
        "id": note_id,
        "url": url,
        "title": "",
        "author": "",
        "description": "",
        "likes": 0,
        "time_text": "",
        "days_ago": 1,
        "hot_score": 0.0,
        "images": [],
        "ocr_text": "",
    }

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(3)
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
    except Exception as e:
        print(f"  [错误] 页面加载失败: {e}")
        return note

    # ── 提取文字信息 ──
    info = await page.evaluate("""() => {
        // 标题/描述：从 document.title 提取
        const rawTitle = document.title || '';
        const desc = rawTitle.replace(/ - 抖音$/, '').replace(/ - TikTok$/, '').trim();

        // 点赞数：class 包含 KV_gO8oI（已验证）
        let likesText = '0';
        const likeEl = document.querySelector('[class*="KV_gO8oI"]');
        if (likeEl) likesText = likeEl.textContent.trim();

        // 作者：找 nickname / 用户名相关元素
        let author = '';
        const authorSelectors = [
            '[class*="nickname"]', '[class*="authorName"]',
            '[class*="user-name"]', '[class*="userName"]',
            '[data-e2e="user-name"]', '[data-e2e="author-name"]',
            'h2', 'h3'
        ];
        for (const sel of authorSelectors) {
            try {
                const el = document.querySelector(sel);
                if (el) {
                    const t = el.textContent.trim();
                    if (t && t.length < 50 && !t.includes('抖音') && !t.includes('推荐')) {
                        author = t;
                        break;
                    }
                }
            } catch(e) {}
        }

        // 时间：找评论中的时间 or 发布时间
        let timeText = '';
        // 找所有文本含"前"的 span
        const spans = document.querySelectorAll('span');
        for (const s of spans) {
            const t = s.textContent.trim();
            if ((t.includes('天前') || t.includes('周前') || t.includes('小时前') || t.includes('月前'))
                && t.length < 20) {
                timeText = t;
                break;
            }
        }

        return { desc, author, likesText, timeText };
    }""")

    note["description"] = info.get("desc", "")
    note["author"] = info.get("author", "")
    note["title"] = info.get("desc", "")[:60]
    note["time_text"] = info.get("timeText", "")
    note["likes"] = parse_likes(info.get("likesText", "0"))
    note["days_ago"] = parse_days_ago(info.get("timeText", ""))
    note["hot_score"] = note["likes"] / max(note["days_ago"], 0.1)

    print(f"  描述: {note['description'][:40]}")
    print(f"  作者: {note['author']} | 点赞: {note['likes']} | 时间: {note['time_text']}")

    if no_ocr:
        return note

    # ── 截图图片 ──
    # 内容图片用 class otaLO99b 标识（大图），去重后截图
    img_elements = await page.evaluate("""() => {
        const seen = new Set();
        const result = [];
        // 优先用 otaLO99b 类（内容大图）
        let imgs = Array.from(document.querySelectorAll('img[class*="otaLO99b"]'));
        // 兜底：所有大图（宽或高 > 400），排除头像/logo
        if (imgs.length === 0) {
            imgs = Array.from(document.querySelectorAll('img')).filter(img => {
                const w = img.naturalWidth || img.offsetWidth;
                const h = img.naturalHeight || img.offsetHeight;
                const src = img.src || '';
                return (w > 400 || h > 400)
                    && !src.includes('avatar')
                    && !src.includes('static')
                    && src.includes('douyinpic.com/tos-cn-i');
            });
        }
        for (const img of imgs) {
            // 用 src 前60字符去重（同一张图可能在 DOM 里出现两次）
            const key = img.src.substring(0, 60);
            if (!seen.has(key)) {
                seen.add(key);
                const rect = img.getBoundingClientRect();
                result.push({x: rect.x, y: rect.y, w: rect.width, h: rect.height, src: img.src.substring(0,60)});
            }
        }
        return result;
    }""")

    if not img_elements:
        print(f"  [警告] 未找到内容图片")
        return note

    print(f"  [图片] 找到 {len(img_elements)} 张内容图（去重后）")

    # 重新查询元素用于截图（Playwright 需要 ElementHandle）
    all_imgs = await page.query_selector_all('img[class*="otaLO99b"]')
    if not all_imgs:
        all_imgs = await page.query_selector_all('img')
    # 去重筛选
    seen_src = set()
    deduped = []
    for el in all_imgs:
        src = await el.get_attribute("src") or ""
        key = src[:60]
        if key in seen_src:
            continue
        box = await el.bounding_box()
        if not box or box["width"] < 200 or box["height"] < 200:
            continue
        if "avatar" in src or "static" in src:
            continue
        seen_src.add(key)
        deduped.append(el)

    if not deduped:
        print(f"  [警告] 去重后无有效图片")
        return note

    print(f"  [图片] 实际截图数: {len(deduped)}")

    ocr_texts = []
    saved_paths = []

    for i, img_el in enumerate(deduped):
        save_path = IMAGES_DIR / f"{keyword}_{idx}_{i+1}.png"
        try:
            await img_el.screenshot(path=str(save_path))
            saved_paths.append(save_path)
            print(f"    [截图] 图{i+1} → {save_path.name}")

            if OCR_TOKEN:
                text = ocr_image_file(save_path)
                if text:
                    ocr_texts.append(text)
                    print(f"    [OCR✓] {len(text)} 字符")
                else:
                    print(f"    [OCR] 无文字")
        except Exception as e:
            print(f"    [错误] 图{i+1}: {e}")

    note["images"] = [str(p) for p in saved_paths]
    note["ocr_text"] = "\n\n---\n\n".join(ocr_texts)
    return note


# ─────────────────────── Markdown ────────────────────────

def generate_markdown(notes: list, keyword: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# 抖音图文笔记采集报告", "",
        f"**关键词**：{keyword}",
        f"**采集时间**：{ts}",
        f"**笔记数量**：{len(notes)} 条",
        "", "---", "", "## 📋 目录", "",
    ]
    for i, n in enumerate(notes, 1):
        title = n["title"][:40] or n["description"][:40] or n["id"]
        lines.append(f"{i}. [{title}](#笔记{i})")

    lines += ["", "---"]

    for i, n in enumerate(notes, 1):
        title = n["title"][:40] or n["description"][:40] or n["id"]
        formula = f"{n['likes']}赞 / {n['days_ago']}天 = **{n['hot_score']:.2f}分**"
        lines += [
            "", f'<a name="笔记{i}"></a>', "",
            f"## 笔记 {i} — {title}", "",
            f"**🔥 热度分数**：{n['hot_score']:.2f} 分",
            f"**📈 热度计算**：{formula}",
            f"**👍 点赞数**：{n['likes']}",
            f"**📅 发布时间**：{n['time_text']}",
            f"**👤 作者**：{n['author']}",
            f"**🔗 链接**：{n['url']}",
            "",
            "### 📝 原文描述", "",
            n["description"] or "_(未获取)_", "",
            "### 🔍 OCR 识别内容", "",
            n["ocr_text"] if n["ocr_text"] else "_(无识别结果)_", "",
        ]
        if n["images"]:
            lines.append("### 🖼️ 图片路径")
            for p in n["images"]:
                lines.append(f"- `{p}`")
            lines.append("")
        lines.append("---")

    total_likes = sum(n["likes"] for n in notes)
    avg_score = sum(n["hot_score"] for n in notes) / len(notes) if notes else 0
    ocr_count = sum(1 for n in notes if n["ocr_text"])
    lines += [
        "", "## 📊 统计", "",
        "| 指标 | 数值 |", "|------|------|",
        f"| 笔记总数 | {len(notes)} |",
        f"| 总点赞数 | {total_likes} |",
        f"| 平均热度 | {avg_score:.2f} |",
        f"| OCR 成功 | {ocr_count}/{len(notes)} |", "",
    ]
    return "\n".join(lines)


# ──────────────────────────── 主流程 ─────────────────────────

async def run(keyword: str, count: int, min_likes: int, no_ocr: bool):
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    notes = []

    async with async_playwright() as p:
        print("[启动] 加载登录状态...")
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
            ],
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        try:
            # ── 搜索 + 筛选 ──
            print("[首页] 打开抖音...")
            await page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(6)

            print(f"[搜索] 关键词：{keyword}")
            search_input = await page.wait_for_selector('input[placeholder*="搜索"]', timeout=8000)
            await search_input.click()
            await asyncio.sleep(0.5)
            await page.keyboard.type(keyword, delay=100)
            await asyncio.sleep(0.5)
            await page.keyboard.press("Enter")
            await asyncio.sleep(6)

            print("[筛选] 图文 + 一周内...")
            for sel in [
                'xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/span',
                'span:has-text("筛选")',
            ]:
                try:
                    btn = await page.wait_for_selector(sel, timeout=3000)
                    if btn:
                        await btn.hover()
                        break
                except Exception:
                    continue
            await asyncio.sleep(1)
            for sel in [
                'xpath=//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/div/div[5]/span[3]',
                'span:has-text("图文")',
            ]:
                try:
                    btn = await page.wait_for_selector(sel, timeout=3000)
                    if btn:
                        await btn.click()
                        print("  [✓] 图文")
                        break
                except Exception:
                    continue
            await asyncio.sleep(1)
            try:
                week_btn = await page.query_selector('text=一周内')
                if week_btn:
                    await week_btn.click()
                    print("  [✓] 一周内")
            except Exception:
                pass
            await asyncio.sleep(3)

            # ── 提取 note IDs ──
            print(f"\n[列表] 采集笔记 ID（目标 {count} 条）...")
            note_ids = await collect_note_ids(page, count)
            print(f"[完成] 获得 {len(note_ids)} 个 ID")

            # ── 逐条详情页处理 ──
            for i, nid in enumerate(note_ids, 1):
                print(f"\n[{i}/{len(note_ids)}] 笔记 ID: {nid}")
                note = await process_note(page, nid, i, keyword, no_ocr)

                # min_likes 过滤（详情页才能拿到真实点赞）
                if note["likes"] < min_likes:
                    print(f"  [跳过] 点赞数 {note['likes']} < {min_likes}")
                    continue

                notes.append(note)
                await asyncio.sleep(2)

        except Exception as e:
            print(f"[错误] {e}")
            import traceback
            traceback.print_exc()
            try:
                await page.screenshot(path=str(SKILL_DIR / "debug_error.png"))
            except Exception:
                pass
        finally:
            await browser.close()

    # ── 输出 ──
    md = generate_markdown(notes, keyword)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"notes_{keyword}_{ts}.md"
    out_path.write_text(md, encoding="utf-8")

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"✓ 完成！关键词：{keyword} | 笔记：{len(notes)} 条")
    print(f"报告：{out_path}")
    print(f"{sep}\n")
    print(md)


def main():
    parser = argparse.ArgumentParser(description="抖音图文笔记采集+OCR（无 SQLite）")
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--count", type=int, default=10, help="采集数量（默认10）")
    parser.add_argument("--min-likes", type=int, default=0, help="最低点赞数")
    parser.add_argument("--no-ocr", action="store_true", help="跳过 OCR")
    args = parser.parse_args()
    asyncio.run(run(args.keyword, args.count, args.min_likes, args.no_ocr))


if __name__ == "__main__":
    main()
