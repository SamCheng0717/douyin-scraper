#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整流程测试脚本"""
import sys
import sqlite3
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SKILL_DIR = Path(__file__).parent.parent
DB_PATH = SKILL_DIR / "data" / "douyin.db"

def test_database():
    """测试数据库结构"""
    print("\n[测试] 数据库结构检查...")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 检查表结构
    cursor.execute("PRAGMA table_info(notes)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    
    required = {
        'id': 'INTEGER',
        'keyword': 'TEXT',
        'title': 'TEXT',
        'author': 'TEXT',
        'description': 'TEXT',
        'tags': 'TEXT',
        'images': 'TEXT',
        'likes': 'INTEGER',
        'publish_date': 'TEXT',
        'days_ago': 'INTEGER',
        'hot_score': 'REAL',
        'ocr_text': 'TEXT',
        'source_url': 'TEXT',
        'created_at': 'TIMESTAMP',
        'status': 'TEXT'
    }
    
    missing = []
    for col, dtype in required.items():
        if col not in columns:
            missing.append(col)
            print(f"  ✗ 缺少字段: {col}")
        else:
            print(f"  ✓ 字段存在: {col} ({columns[col]})")
    
    conn.close()
    
    if missing:
        print(f"\n[错误] 数据库缺少字段: {missing}")
        print("  请运行: python scripts/db.py")
        return False
    else:
        print("  ✓ 数据库结构完整")
        return True

def test_data():
    """测试数据"""
    print("\n[测试] 数据检查...")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 统计
    cursor.execute("SELECT COUNT(*) FROM notes")
    total = cursor.fetchone()[0]
    print(f"  总记录: {total}条")
    
    # 按关键词分组
    cursor.execute("SELECT keyword, COUNT(*) FROM notes GROUP BY keyword")
    for row in cursor.fetchall():
        print(f"  - {row[0]}: {row[1]}条")
    
    # 热度Top 3
    cursor.execute("SELECT keyword, title, hot_score FROM notes ORDER BY hot_score DESC LIMIT 3")
    print(f"\n  热度Top 3:")
    for i, row in enumerate(cursor.fetchall(), 1):
        title = row[1][:30] + "..." if len(row[1]) > 30 else row[1]
        print(f"    {i}. [{row[0]}] {title} (热度{row[2]:.1f})")
    
    conn.close()
    return True

def main():
    print("=" * 60)
    print("抖音图文采集技能 - 完整性测试")
    print("=" * 60)
    
    # 测试数据库
    if not test_database():
        return 1
    
    # 测试数据
    if not test_data():
        return 1
    
    print("\n" + "=" * 60)
    print("✓ 所有测试通过！")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
