#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite 数据库操作"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "douyin.db"


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))


def init_db():
    """初始化数据库表"""
    conn = get_conn()
    conn.execute("""
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
            days_ago INTEGER DEFAULT 1,
            hot_score REAL DEFAULT 0,
            ocr_text TEXT,
            source_url TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_keyword ON notes(keyword)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON notes(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hot_score ON notes(hot_score)")
    
    # 添加缺失的字段（兼容旧表）
    cursor = conn.cursor()
    for col, dtype in [('description', 'TEXT'), ('publish_date', 'TEXT'), 
                       ('days_ago', 'INTEGER DEFAULT 1'), ('hot_score', 'REAL DEFAULT 0')]:
        try:
            cursor.execute(f'ALTER TABLE notes ADD COLUMN {col} {dtype}')
        except sqlite3.OperationalError:
            pass  # 字段已存在
    
    conn.commit()
    conn.close()


def insert_note(keyword, title, author, description, tags, images, likes, 
                publish_date=None, days_ago=1, hot_score=0, source_url='', ocr_text=None):
    """插入笔记，URL 去重，返回note_id或None"""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO notes (keyword, title, author, description, tags, images, 
                             likes, publish_date, days_ago, hot_score, source_url, ocr_text, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            keyword, title, author, description,
            json.dumps(tags, ensure_ascii=False) if tags else None,
            json.dumps(images, ensure_ascii=False) if images else None,
            likes or 0, publish_date, days_ago, hot_score, source_url, ocr_text,
            'ocr_done' if ocr_text else 'pending',
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return cursor.lastrowid  # 返回插入的ID
    except sqlite3.IntegrityError:
        return None  # URL 重复
    finally:
        conn.close()


def get_pending_notes(keyword=None, limit=None):
    """获取待 OCR 处理的笔记"""
    conn = get_conn()
    sql = "SELECT * FROM notes WHERE status = 'pending'"
    params = []
    if keyword:
        sql += " AND keyword = ?"
        params.append(keyword)
    if limit:
        sql += f" LIMIT {limit}"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return [row_to_dict(r) for r in rows]


def get_ocr_done_notes(keyword=None, limit=None):
    """获取已 OCR 的笔记"""
    conn = get_conn()
    sql = "SELECT * FROM notes WHERE status = 'ocr_done' AND ocr_text IS NOT NULL"
    params = []
    if keyword:
        sql += " AND keyword = ?"
        params.append(keyword)
    if limit:
        sql += f" LIMIT {limit}"

    rows = conn.execute(sql, params).fetchall()
    conn.close()

    return [row_to_dict(r) for r in rows]


def update_ocr(note_id, ocr_text):
    """更新 OCR 结果"""
    conn = get_conn()
    conn.execute("""
        UPDATE notes SET ocr_text = ?, status = 'ocr_done' WHERE id = ?
    """, (ocr_text, note_id))
    conn.commit()
    conn.close()


def mark_processed(note_id):
    """标记为已处理"""
    conn = get_conn()
    conn.execute("UPDATE notes SET status = 'processed' WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()


def get_stats(keyword=None):
    """统计信息"""
    conn = get_conn()
    sql = "SELECT status, COUNT(*) as cnt FROM notes"
    if keyword:
        sql += " WHERE keyword = ?"
        params = [keyword]
    else:
        params = []
    sql += " GROUP BY status"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def row_to_dict(row):
    """行转字典"""
    return {
        "id": row[0],
        "keyword": row[1],
        "title": row[2],
        "author": row[3],
        "description": row[4] if len(row) > 4 else '',
        "tags": json.loads(row[5]) if row[5] else [],
        "images": json.loads(row[6]) if row[6] else [],
        "likes": row[7] if len(row) > 7 else 0,
        "comments": row[8] if len(row) > 8 else 0,
        "shares": row[9] if len(row) > 9 else 0,
        "publish_date": row[10] if len(row) > 10 else '',
        "days_ago": row[11] if len(row) > 11 else 1,
        "hot_score": row[12] if len(row) > 12 else 0,
        "ocr_text": row[13] if len(row) > 13 else '',
        "source_url": row[14] if len(row) > 14 else '',
        "created_at": row[15] if len(row) > 15 else '',
        "status": row[16] if len(row) > 16 else 'pending'
    }


if __name__ == "__main__":
    init_db()
    print("数据库初始化完成:", DB_PATH)
