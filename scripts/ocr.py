#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR 识别 - 使用百度PaddleOCR API
从数据库读取未处理的图片，识别文字，更新数据库
"""
import argparse
import base64
import json
import os
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from db import get_pending_notes, update_ocr, get_stats

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# API配置
API_URL = os.getenv("BAIDU_PADDLEOCR_API_URL", "https://r41cd0p9x7dfp1s7.aistudio-app.com/layout-parsing")
API_TOKEN = os.getenv("BAIDU_PADDLEOCR_TOKEN", "")


def ocr_with_baidu(image_data: str) -> str:
    """使用百度PaddleOCR API识别图片"""
    if not API_TOKEN:
        print("  [错误] 未配置百度PaddleOCR Token")
        print("  请在 .env 文件中设置 BAIDU_PADDLEOCR_TOKEN")
        print("  或设置环境变量: export BAIDU_PADDLEOCR_TOKEN=your_token")
        return ""
    
    try:
        import requests
    except ImportError:
        print("  [错误] 请安装 requests: pip install requests")
        return ""
    
    headers = {
        "Authorization": f"token {API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "file": image_data,
        "fileType": 1,  # 图片类型
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    }
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"  [错误] API调用失败: {response.status_code}")
            print(f"  响应: {response.text[:200]}")
            return ""
        
        result = response.json().get("result", {})
        layout_results = result.get("layoutParsingResults", [])
        
        if not layout_results:
            return ""
        
        # 提取所有markdown文本
        all_text = []
        for res in layout_results:
            md_text = res.get("markdown", {}).get("text", "")
            if md_text.strip():
                all_text.append(md_text.strip())
        
        return "\n\n".join(all_text)
        
    except requests.exceptions.Timeout:
        print("  [错误] API调用超时")
        return ""
    except Exception as e:
        print(f"  [错误] API调用异常: {e}")
        return ""


def ocr_images(image_paths: list) -> str:
    """OCR 识别多张图片（支持本地路径和网络URL）"""
    all_text = []
    
    for img_path in image_paths:
        try:
            # 判断是否为网络URL
            if img_path.startswith('http'):
                print(f"    下载图片: {img_path[:60]}...")
                # 下载图片
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    urllib.request.urlretrieve(img_path, tmp.name)
                    local_path = tmp.name
            else:
                local_path = img_path
            
            # 读取图片并转base64
            if not Path(local_path).exists():
                print(f"    [警告] 文件不存在: {local_path}")
                continue
            
            with open(local_path, "rb") as file:
                file_bytes = file.read()
                file_data = base64.b64encode(file_bytes).decode("ascii")
            
            # 调用百度OCR API
            print(f"    识别中...")
            text = ocr_with_baidu(file_data)
            
            if text.strip():
                all_text.append(text.strip())
                print(f"    ✓ 识别成功: {len(text)} 字符")
            else:
                print(f"    [警告] 无识别结果")
                
        except Exception as e:
            print(f"    [错误] 处理失败: {e}")
        finally:
            # 清理临时文件
            if img_path.startswith('http') and 'local_path' in locals():
                try:
                    os.unlink(local_path)
                except:
                    pass
    
    return "\n\n".join(all_text)


def ocr_notes(keyword: str = None, limit: int = None):
    """处理待 OCR 的笔记"""
    # 检查API配置
    if not API_TOKEN:
        print("\n" + "="*60)
        print("[错误] 未配置百度PaddleOCR Token")
        print("="*60)
        print("\n配置方法：")
        print("1. 在百度AI Studio申请API Key: https://aistudio.baidu.com/paddleocr")
        print("2. 创建 .env 文件（参考 .env.example）")
        print("3. 填写 BAIDU_PADDLEOCR_TOKEN=your_token")
        print("\n或设置环境变量：")
        print("  export BAIDU_PADDLEOCR_TOKEN=your_token  (Linux/Mac)")
        print("  set BAIDU_PADDLEOCR_TOKEN=your_token     (Windows)")
        print("="*60 + "\n")
        return
    
    notes = get_pending_notes(keyword, limit)

    if not notes:
        print("没有待处理的笔记")
        return

    print(f"待处理: {len(notes)} 条笔记\n")

    for i, note in enumerate(notes, 1):
        print(f"[{i}/{len(notes)}] {note['title'][:30]}...")

        images = note.get("images", [])
        # 解析JSON字符串
        if isinstance(images, str):
            try:
                images = json.loads(images)
            except:
                images = []
        
        if not images:
            print("  无图片，跳过")
            continue

        print(f"  识别 {len(images)} 张图片...")
        start = time.time()

        ocr_text = ocr_images(images)

        if ocr_text:
            update_ocr(note["id"], ocr_text)
            print(f"  ✓ 完成 ({time.time()-start:.1f}s)")
        else:
            print("  ✗ 无识别结果")

    print(f"\nOCR 完成")
    stats = get_stats(keyword)
    print(f"统计: {stats}")


def main():
    parser = argparse.ArgumentParser(description="OCR 识别图片内容（百度PaddleOCR）")
    parser.add_argument("--keyword", help="筛选关键词")
    parser.add_argument("--limit", type=int, help="处理数量限制")

    args = parser.parse_args()
    ocr_notes(args.keyword, args.limit)


if __name__ == "__main__":
    main()
