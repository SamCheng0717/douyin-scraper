"""
抖音图文笔记导出为Markdown

从SQLite读取笔记数据，生成格式化的Markdown文件
"""
import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# 路径配置
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
DATA_DIR = SKILL_DIR / "data"
DB_PATH = DATA_DIR / "douyin.db"
OUTPUT_DIR = SKILL_DIR / "output"


def export_notes(keyword=None, min_likes=0, status=None, output_file=None):
    """
    导出笔记到Markdown
    
    Args:
        keyword: 按关键词筛选（None表示全部）
        min_likes: 最低点赞数
        status: 按状态筛选（None表示全部）
        output_file: 输出文件名（None表示自动生成）
    """
    # 连接数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 构建查询
    query = """
        SELECT keyword, title, author, description, tags, images, 
               likes, publish_date, days_ago, hot_score, ocr_text, 
               source_url, created_at, status
        FROM notes
        WHERE likes >= ?
    """
    params = [min_likes]
    
    if keyword:
        query += " AND keyword = ?"
        params.append(keyword)
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY hot_score DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"[警告] 没有找到符合条件的笔记")
        return
    
    # 生成Markdown
    md_lines = []
    
    # 标题
    if keyword:
        md_lines.append(f"# 抖音图文笔记采集报告")
        md_lines.append(f"\n**关键词**：{keyword}")
    else:
        md_lines.append(f"# 抖音图文笔记采集报告（全部）")
    
    md_lines.append(f"\n**采集时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    md_lines.append(f"\n**笔记数量**：{len(rows)} 条")
    md_lines.append(f"\n**筛选条件**：点赞数 ≥ {min_likes}")
    md_lines.append("\n---\n")
    
    # 目录
    md_lines.append("## 📋 目录\n")
    for i, row in enumerate(rows, 1):
        title = row[1][:30] + "..." if len(row[1]) > 30 else row[1]
        md_lines.append(f"{i}. [{title}](#笔记{i})")
    md_lines.append("\n---\n")
    
    # 详细内容
    for i, row in enumerate(rows, 1):
        (note_keyword, title, author, description, tags, images, 
         likes, publish_date, days_ago, hot_score, ocr_text, 
         source_url, created_at, note_status) = row
        
        md_lines.append(f'<a name="笔记{i}"></a>\n')
        md_lines.append(f"## 笔记 {i}\n")
        
        # 基本信息 - 热度计算公式
        days = days_ago if days_ago and days_ago > 0 else 1
        md_lines.append(f"**🔥 热度分数**：{hot_score:.2f} 分\n")
        md_lines.append(f"**📈 热度计算**：{likes}赞 / {days}天 = **{hot_score:.2f}分**\n")
        md_lines.append(f"**👍 点赞数**：{likes}\n")
        md_lines.append(f"**📅 发布时间**：{publish_date}（{days}天前）\n")
        md_lines.append(f"**👤 作者**：{author}\n")
        md_lines.append(f"**🏷️ 关键词**：{note_keyword}\n")
        md_lines.append(f"**📊 状态**：{note_status}\n")
        
        # 标题
        md_lines.append(f"\n### 📌 标题\n")
        md_lines.append(f"```\n{title}\n```\n")
        
        # 描述
        if description:
            md_lines.append(f"\n### 📝 原文描述\n")
            md_lines.append(f"{description}\n")
        
        # 标签
        if tags:
            try:
                tags_list = json.loads(tags) if isinstance(tags, str) else tags
                if tags_list:
                    md_lines.append(f"\n### 🏷️ 标签\n")
                    md_lines.append(" ".join([f"#{tag}" for tag in tags_list]))
                    md_lines.append("\n")
            except:
                pass
        
        # OCR内容
        if ocr_text:
            md_lines.append(f"\n### 🔍 OCR识别内容\n")
            md_lines.append(f"```\n{ocr_text}\n```\n")
        
        # 图片列表
        if images:
            try:
                images_list = json.loads(images) if isinstance(images, str) else images
                if images_list:
                    md_lines.append(f"\n### 🖼️ 图片列表\n")
                    for j, img_url in enumerate(images_list, 1):
                        # 只显示URL，不嵌入图片（避免文件过大）
                        md_lines.append(f"{j}. `{img_url[:80]}...`")
                    md_lines.append("\n")
            except:
                pass
        
        md_lines.append("\n---\n")
    
    # 统计信息
    md_lines.append("## 📊 统计信息\n")
    
    total_likes = sum(row[6] for row in rows)
    avg_hot_score = sum(row[9] for row in rows) / len(rows) if rows else 0
    avg_likes = total_likes / len(rows) if rows else 0
    
    md_lines.append(f"- **总点赞数**：{total_likes:,}")
    md_lines.append(f"- **平均点赞数**：{avg_likes:.1f}")
    md_lines.append(f"- **平均热度分数**：{avg_hot_score:.1f}")
    
    # 按关键词分组统计
    if not keyword:
        keyword_stats = {}
        for row in rows:
            k = row[0]
            if k not in keyword_stats:
                keyword_stats[k] = {'count': 0, 'likes': 0}
            keyword_stats[k]['count'] += 1
            keyword_stats[k]['likes'] += row[6]
        
        if keyword_stats:
            md_lines.append(f"\n### 按关键词统计\n")
            for k, stats in sorted(keyword_stats.items(), key=lambda x: x[1]['likes'], reverse=True):
                md_lines.append(f"- **{k}**：{stats['count']} 条，总点赞 {stats['likes']:,}")
    
    md_lines.append("\n---\n")
    md_lines.append(f"\n*生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    # 生成文件名
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        kw_suffix = f"_{keyword}" if keyword else "_all"
        output_file = f"notes{kw_suffix}_{timestamp}.md"
    
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 写入文件
    output_path = OUTPUT_DIR / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))
    
    print(f"[成功] 导出 {len(rows)} 条笔记")
    print(f"[文件] {output_path}")
    print(f"[大小] {output_path.stat().st_size / 1024:.1f} KB")
    
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='导出抖音图文笔记为Markdown')
    parser.add_argument('--keyword', help='按关键词筛选')
    parser.add_argument('--min-likes', type=int, default=0, help='最低点赞数')
    parser.add_argument('--status', help='按状态筛选')
    parser.add_argument('--output', help='输出文件名')
    
    args = parser.parse_args()
    
    export_notes(
        keyword=args.keyword,
        min_likes=args.min_likes,
        status=args.status,
        output_file=args.output
    )
