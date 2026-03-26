#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""依赖检查脚本"""
import sys
import subprocess
import os
from pathlib import Path

# Windows 编码修复
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def check_dependencies():
    """检查所有依赖"""
    print("=" * 60)
    print("抖音图文采集技能 - 依赖检查")
    print("=" * 60)
    
    # Python 版本
    py_version = sys.version_info
    print(f"\nPython版本: {py_version.major}.{py_version.minor}.{py_version.micro}")
    if py_version < (3, 8):
        print("  ✗ 需要Python 3.8或更高版本")
        return False
    print("  ✓ Python版本符合要求")
    
    # 必需依赖
    required = {
        'playwright': 'playwright',
        'requests': 'requests',
        'dotenv': 'python-dotenv',
        'openai': 'openai',
        'PIL': 'Pillow',
        'sqlite3': '内置',
    }
    
    print("\n依赖检查:")
    missing = []
    
    for pkg, pip_name in required.items():
        try:
            if pkg == 'PIL':
                import PIL
                print(f"  ✓ {pkg} ({pip_name}): {PIL.__version__}")
            elif pkg == 'sqlite3':
                import sqlite3
                print(f"  ✓ {pkg} ({pip_name}): 内置模块")
            else:
                mod = __import__(pkg)
                version = getattr(mod, '__version__', '未知')
                print(f"  ✓ {pkg} ({pip_name}): {version}")
        except ImportError as e:
            print(f"  ✗ {pkg} ({pip_name}): 未安装")
            if pip_name != '内置':
                missing.append(pip_name)
    
    # Playwright浏览器检查
    print("\nPlaywright浏览器:")
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'playwright', 'install', '--dry-run', 'chromium'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print("  ✓ Chromium浏览器已安装")
        else:
            print("  ⚠ 可能需要安装浏览器:")
            print("    python -m playwright install chromium")
    except Exception as e:
        print(f"  ⚠ 无法检查浏览器状态: {e}")
        print("    请手动运行: python -m playwright install chromium")
    
    # 数据库检查
    print("\n数据库检查:")
    db_path = Path(__file__).parent.parent / "data" / "douyin.db"
    if db_path.exists():
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notes")
        count = cursor.fetchone()[0]
        conn.close()
        print(f"  ✓ 数据库存在: {db_path}")
        print(f"  ✓ 已有记录: {count}条")
    else:
        print(f"  ℹ 数据库不存在，将在首次运行时创建")
    
    # 配置检查
    print("\nLLM配置检查:")
    config_path = Path(__file__).parent / "llm_config.json"
    if config_path.exists():
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        provider = config.get('provider', '未设置')
        print(f"  ✓ 配置文件存在: {config_path}")
        print(f"  ✓ 当前提供商: {provider}")
    else:
        print(f"  ⚠ 配置文件不存在: {config_path}")
        print("    请运行: python llm_router.py --setup")
    
    # 百度PaddleOCR配置检查
    print("\n百度PaddleOCR配置检查:")
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path)
        token = os.getenv("BAIDU_PADDLEOCR_TOKEN", "")
        if token and token != "your_token_here":
            print(f"  ✓ .env 文件存在: {env_path}")
            print(f"  ✓ Token已配置: {token[:10]}...")
        else:
            print(f"  ⚠ Token未配置或使用默认值")
            print("    请编辑 .env 文件，填写 BAIDU_PADDLEOCR_TOKEN")
    else:
        print(f"  ⚠ .env 文件不存在: {env_path}")
        print("    请复制 .env.example 并填写配置")
    
    # 环境变量检查
    env_token = os.getenv("BAIDU_PADDLEOCR_TOKEN", "")
    if env_token and env_token != "your_token_here":
        print(f"  ✓ 环境变量已配置")
    
    # 总结
    print("\n" + "=" * 60)
    if missing:
        print("缺少以下依赖:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\n安装命令:")
        print(f"  pip install {' '.join(missing)}")
        return False
    else:
        print("✓ 所有依赖已安装！")
        return True

if __name__ == "__main__":
    success = check_dependencies()
    sys.exit(0 if success else 1)
