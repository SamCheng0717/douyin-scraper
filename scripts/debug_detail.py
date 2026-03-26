#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio, sys
from pathlib import Path
from playwright.async_api import async_playwright
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROFILE_DIR = Path(__file__).parent.parent / "profile"

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1440, "height": 900},
            locale="zh-CN",
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        await page.goto("https://www.douyin.com/note/7600669163870245361",
                        wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(4)

        # 打印页面中所有有实质文字内容的元素（叶节点文本）
        texts = await page.evaluate("""() => {
            const result = [];
            const walk = (node) => {
                if (node.nodeType === 3) {
                    const t = node.textContent.trim();
                    if (t.length > 2 && t.length < 200) {
                        const p = node.parentElement;
                        result.push({
                            tag: p ? p.tagName : '?',
                            cls: p ? p.className.substring(0,60) : '',
                            text: t.substring(0,100)
                        });
                    }
                }
                node.childNodes.forEach(walk);
            };
            walk(document.body);
            return result.slice(0, 80);
        }""")
        print(f"页面文本节点 ({len(texts)} 个):")
        for t in texts:
            print(f"  <{t['tag']} class={t['cls'][:40]}> {t['text']}")

        await browser.close()

asyncio.run(debug())
