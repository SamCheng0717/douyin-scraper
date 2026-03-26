#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
二创 - 从数据库读取已 OCR 的笔记，按风格生成 Markdown
"""
import argparse
import sys
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SKILL_DIR = Path(__file__).parent.parent
OUTPUT_DIR = SKILL_DIR / "output"

from db import get_ocr_done_notes, mark_processed


STYLES = {
    1: {
        "name": "爆款标题党",
        "prompt": """你是一个爆款内容创作者。根据以下原始内容，创作一篇吸引眼球的内容：

要求：
1. 标题要有冲击力，让人忍不住点开
2. 开头要抓住痛点，引发共鸣
3. 正文用短句，每段不超过3行
4. 结尾要有行动号召

原始内容：
{content}

请输出标题和正文："""
    },
    2: {
        "name": "深度干货流",
        "prompt": """你是一个专业领域的内容创作者。根据以下原始内容，创作一篇深度干货文章：

要求：
1. 标题要体现专业性和价值感
2. 开头点明主题和收益
3. 正文结构化，用小标题分段
4. 内容要具体可执行

原始内容：
{content}

请输出文章："""
    },
    3: {
        "name": "轻松闲聊风",
        "prompt": """你是一个生活类博主。根据以下原始内容，创作一篇轻松闲聊的内容：

要求：
1. 标题要亲切自然
2. 像朋友聊天一样娓娓道来
3. 可以加入个人感受和经历
4. 结尾要温暖

原始内容：
{content}

请输出内容："""
    },
    4: {
        "name": "励志鸡汤风",
        "prompt": """你是一个励志类博主。根据以下原始内容，创作一篇正能量内容：

要求：
1. 标题要有感染力
2. 开头用故事或场景引入
3. 中间提炼金句
4. 结尾要升华主题

原始内容：
{content}

请输出内容："""
    },
    5: {
        "name": "种草带货风",
        "prompt": """你是一个种草博主。根据以下原始内容，创作一篇带货种草内容：

要求：
1. 标题突出产品/服务价值
2. 开头展示痛点
3. 中间详细介绍体验和效果
4. 结尾引导行动

原始内容：
{content}

请输出内容："""
    },
    6: {
        "name": "短视频脚本",
        "prompt": """你是一个短视频脚本创作者。根据以下原始内容，创作一个短视频脚本：

要求：
1. 时长控制在60秒内
2. 标注景别、台词、动作
3. 开头3秒要抓住眼球
4. 结尾要有互动引导

原始内容：
{content}

请输出脚本："""
    }
}


def get_llm_client():
    """获取 LLM 客户端"""
    import json
    config_path = Path(__file__).parent / "llm_config.json"
    if not config_path.exists():
        print("请先配置 LLM: python llm_router.py --setup")
        return None, None

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    provider = config.get("provider", "deepseek")
    api_key = config.get("api_key")
    model = config.get("model", "deepseek-chat")

    if provider == "deepseek":
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
    elif provider == "glm":
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://open.bigmodel.cn/api/paas/v4")
    else:
        print(f"不支持的提供商: {provider}")
        return None, None

    return client, model


def generate_content(client, model, prompt_template, content):
    """调用 LLM 生成内容"""
    try:
        prompt = prompt_template.format(content=content)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=2000
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"  生成失败: {e}")
        return None


def rewrite(keyword: str, style: int, limit: int):
    """二创"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    client, model = get_llm_client()
    if not client:
        return

    style_info = STYLES.get(style)
    if not style_info:
        print(f"无效风格: {style}")
        return

    notes = get_ocr_done_notes(keyword, limit)
    if not notes:
        print("没有已 OCR 的笔记可供二创")
        return

    print(f"\n风格: {style_info['name']}")
    print(f"处理: {len(notes)} 条笔记\n")

    results = []

    for i, note in enumerate(notes, 1):
        print(f"[{i}/{len(notes)}] {note['title'][:30]}...")

        content = generate_content(client, model, style_info["prompt"], note["ocr_text"])
        if content:
            results.append({
                "original_title": note["title"],
                "author": note["author"],
                "likes": note["likes"],
                "tags": note["tags"],
                "source_url": note["source_url"],
                "rewritten": content
            })
            mark_processed(note["id"])
            print(f"  完成")

    # 输出 Markdown
    if results:
        md_path = OUTPUT_DIR / f"{keyword}_{style_info['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        lines = [f"# {keyword} - {style_info['name']}\n\n"]

        for r in results:
            lines.append(f"## {r['original_title']}\n")
            lines.append(f"> 原作者：{r['author']} | 点赞：{r['likes']}\n\n")
            lines.append(r["rewritten"])
            lines.append(f"\n\n---\n*来源：{r['source_url']}*\n\n")

        md_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\n输出: {md_path}")


def main():
    parser = argparse.ArgumentParser(description="二创生成")
    parser.add_argument("--keyword", help="筛选关键词")
    parser.add_argument("--style", type=int, default=1, choices=range(1, 7), help="风格 1-6")
    parser.add_argument("--limit", type=int, default=5, help="处理数量")

    args = parser.parse_args()

    print("可选风格：")
    for k, v in STYLES.items():
        print(f"  {k}. {v['name']}")
    print()

    rewrite(args.keyword, args.style, args.limit)


if __name__ == "__main__":
    main()
