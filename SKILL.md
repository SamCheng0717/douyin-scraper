---
name: douyin-creator
description: 抖音图文笔记二创流水线。一键采集 → OCR识别 → Markdown报告（含热度公式）→ 二创。支持自动采集10篇、热度计算公式显示（270赞/1天=270分）、图片文字识别。当用户提到"抖音二创"、"抖音图文采集"、"抖音笔记抓取"、"抖音爆款采集"等场景时加载此技能。
---

# 抖音图文笔记二创 Skill

## ⚠️ 必须配置 OCR Token

**在使用本技能前，必须配置百度PaddleOCR Token！**

1. 在技能目录创建 `.env` 文件：
   ```
   BAIDU_PADDLEOCR_TOKEN=你的token
   ```

2. 如何获取Token：
   - 访问 [百度AI Studio](https://aistudio.baidu.com/paddleocr)
   - 免费注册，每天1万次免费调用
   - 获取API Token

**未配置Token将无法使用OCR功能！**

---

## 快速开始（推荐）

### 一键完整流程（采集+OCR+下载图片）

```bash
# 采集 → 下载图片 → OCR识别 → 导出Markdown（默认10篇）
python <skill_path>/scripts/scrape_and_ocr.py --keyword "美食"

# 指定数量
python <skill_path>/scripts/scrape_and_ocr.py --keyword "韩国医美" --count 10

# 跳过OCR（仅采集）
python <skill_path>/scripts/scrape_and_ocr.py --keyword "咖啡" --no-ocr
```

**自动执行：**
1. 打开抖音搜索关键词
2. 筛选图文笔记
3. 逐个点击笔记，下载图片
4. OCR识别图片文字
5. 拼接完整笔记内容
6. 导出Markdown报告

**Markdown报告包含：**
- 📝 **OCR识别内容**（图片中的文字）
- 📈 **热度计算公式**：270赞 / 1天 = **270.00分**
- 🔥 热度分数（按分数降序）
- 👍 点赞数、发布时间
- 🖼️ 本地图片路径

## 流程

```
配置OCR Token → 采集图文 → 下载图片 → OCR识别 → 导出Markdown → 二创
```

---

## 依赖安装

### 1. 安装Python依赖
```bash
pip install playwright requests python-dotenv
```

### 2. 安装浏览器
```bash
python -m playwright install chromium
```

### 3. 配置百度PaddleOCR（推荐）

**申请API Key**：
1. 访问 https://aistudio.baidu.com/paddleocr
2. 注册并申请API Key
3. 每天免费1万次调用

**配置方法**：
```bash
# 复制配置模板
cp .env.example .env

# 编辑.env文件，填写你的Token
BAIDU_PADDLEOCR_TOKEN=your_token_here
```

或设置环境变量：
```bash
# Linux/Mac
export BAIDU_PADDLEOCR_TOKEN=your_token_here

# Windows
set BAIDU_PADDLEOCR_TOKEN=your_token_here
```

### 4. 检查依赖
```bash
python <skill_path>/scripts/check_deps.py
```

### 5. 配置LLM（用于二创）
```bash
python <skill_path>/scripts/llm_router.py --setup
```

---

## 核心功能

### 0. 完整流程（推荐）

```bash
# 一键完成：采集 → OCR → 导出
python <skill_path>/scripts/full_workflow.py --keyword "美食"

# 指定数量和最低点赞
python <skill_path>/scripts/full_workflow.py --keyword "旅行" --count 5 --min-likes 1000

# 跳过OCR
python <skill_path>/scripts/full_workflow.py --keyword "咖啡" --no-ocr
```

**完整流程会自动执行：**
1. 采集笔记（默认10篇）
2. OCR识别图片文字
3. 导出Markdown报告

**Markdown报告包含：**
- 🔥 热度分数 + 计算公式（例如：270赞 / 1天 = 270分）
- 👍 点赞数、发布时间
- 📝 原文描述
- 🔍 OCR识别内容
- 🖼️ 图片列表
- 📊 统计信息

### 1. 登录（只需一次）

```bash
python <skill_path>/scripts/login.py
```

浏览器打开抖音，用户扫码登录。状态保存在 `profile/` 目录（Playwright 自动持久化）。

### 2. 采集图文笔记

```bash
python <skill_path>/scripts/scrape.py --keyword "韩国医美" --count 5 --min-likes 50
```

**采集流程（关键）：**

1. 打开抖音首页
2. 输入关键词搜索
3. **鼠标悬浮到筛选按钮**（使用备用选择器自动降级）
4. 下拉菜单弹出后，**点击图文**
5. **点击一周内**（筛选近期内容）
6. 滚动采集卡片
7. **计算热度分数 = 点赞数 / 天数**
8. 按热度排序，保存前 N 条到 SQLite

**备用选择器策略：**
脚本使用多个备用选择器，当首选XPath失效时自动尝试：
```python
filter_selectors = [
    'xpath=/...',           # 首选
    '[data-e2e="..."]',     # 备用1
    'button:has-text("筛选")', # 备用2
]
```

**为什么用悬浮而不是点击？**
抖音的筛选按钮是 hover 触发下拉菜单，不是 click。

**热度公式：**
```python
hot_score = likes / days_ago
# 例如：2天前479赞 = 239.5分，6天前12赞 = 2分
# 分数越高越热门
```

**采集字段：**
- 标题
- 作者
- 描述
- 标签
- 图片列表
- 点赞数
- 发布时间（X天前）
- 热度分数
- 源链接

### 3. OCR 识别（百度PaddleOCR）

```bash
# 首次使用需配置百度PaddleOCR Token
# 编辑 .env 文件，填写 BAIDU_PADDLEOCR_TOKEN

python <skill_path>/scripts/ocr.py

# 按关键词筛选
python <skill_path>/scripts/ocr.py --keyword "美食"
```

**使用百度PaddleOCR优势**：
- ✅ 每天免费1万次调用
- ✅ 识别准确率高
- ✅ 支持中英文混合识别
- ✅ 支持网络图片URL

**配置要求**：
- 需要在 `.env` 文件中配置 `BAIDU_PADDLEOCR_TOKEN`
- 或设置环境变量 `BAIDU_PADDLEOCR_TOKEN`

从 SQLite 读取未处理的笔记，OCR 识别图片文字，更新 `ocr_text` 字段。

### 4. 导出Markdown

```bash
# 导出特定关键词的笔记
python <skill_path>/scripts/export_md.py --keyword "美食"

# 导出全部笔记
python <skill_path>/scripts/export_md.py

# 导出高赞笔记（点赞≥1000）
python <skill_path>/scripts/export_md.py --min-likes 1000

# 导出特定状态的笔记
python <skill_path>/scripts/export_md.py --status pending
```

从 SQLite 读取笔记，生成格式化的 Markdown 报告，包含：
- 📋 目录（可点击跳转）
- 🔥 热度分数、点赞数、作者、发布时间
- 📝 原文描述
- 🏷️ 标签
- 🔍 OCR识别内容（如有）
- 🖼️ 图片列表
- 📊 统计信息（总点赞、平均热度等）

### 5. 二创输出

```bash
python <skill_path>/scripts/rewrite.py --style 1 --keyword "韩国医美"
```

从 SQLite 读取已 OCR 的笔记，按风格二创，输出 Markdown。

---

## 数据库表结构

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    keyword TEXT,           -- 搜索关键词
    title TEXT,             -- 标题
    author TEXT,            -- 作者
    description TEXT,       -- 描述
    tags TEXT,              -- 标签 JSON 数组
    images TEXT,            -- 图片列表 JSON 数组
    likes INTEGER,          -- 点赞数
    comments INTEGER,       -- 评论数
    shares INTEGER,         -- 分享数
    publish_date TEXT,      -- 发布时间（X天前）
    days_ago INTEGER,       -- 天数
    hot_score REAL,         -- 热度分数
    ocr_text TEXT,          -- OCR 识别的文字
    source_url TEXT UNIQUE, -- 源链接
    created_at TEXT,        -- 采集时间
    status TEXT             -- pending/ocr_done/processed
);
```

---

## 目录结构

```
douyin-creator/
├── SKILL.md
├── profile/              ← 登录状态（user_data_dir）
├── data/
│   ├── douyin.db         ← SQLite 数据库
│   └── images/           ← 下载的图片
├── scripts/
│   ├── login.py          ← 登录脚本
│   ├── scrape.py         ← 采集脚本
│   ├── ocr.py            ← OCR 脚本（支持网络图片URL）
│   ├── export_md.py      ← Markdown导出脚本（含热度公式）
│   ├── full_workflow.py  ← 完整流程脚本（推荐）
│   ├── rewrite.py        ← 二创脚本
│   ├── check_deps.py     ← 依赖检查
│   ├── test_flow.py      ← 完整性测试
│   ├── db.py             ← 数据库操作
│   ├── llm_router.py
│   └── llm_config.json
├── output/               ← Markdown报告输出
└── references/
    └── styles.md         -- 风格模板
```

---

## 使用示例

**场景1：一键采集爆款内容（推荐）**

```
用户：采集美食爆款图文笔记
执行：python scripts/full_workflow.py --keyword "美食"

自动完成：
  ✓ 采集10篇笔记（按热度排序）
  ✓ OCR识别图片文字
  ✓ 导出Markdown报告（含热度公式：270赞/1天=270分）
```

**场景2：精准筛选高赞内容**

```
用户：采集旅行笔记，点赞≥1000，只要5篇
执行：python scripts/full_workflow.py --keyword "旅行" --count 5 --min-likes 1000
```

**场景3：快速浏览跳过OCR**

```
用户：快速采集咖啡内容
执行：python scripts/full_workflow.py --keyword "咖啡" --no-ocr

跳过OCR识别，节省时间
```

**场景4：分步执行（高级）**

```
用户：登录抖音
执行：python scripts/login.py

用户：采集韩国医美图文笔记，5条
执行：python scripts/scrape.py --keyword "韩国医美" --count 5

用户：识别图片内容
执行：python scripts/ocr.py

用户：导出Markdown报告
执行：python scripts/export_md.py --keyword "韩国医美"

用户：用爆款标题党风格二创
执行：python scripts/rewrite.py --style 1
```

---

## 关键技术点

### 1. 筛选按钮操作

抖音搜索结果页的筛选按钮是 **hover 触发**，不是 click：

```python
# 错误方式
await filter_btn.click()  # 无效

# 正确方式
await filter_btn.hover()  # 鼠标悬浮，触发下拉菜单
await asyncio.sleep(1)    # 等待菜单弹出
await image_btn.click()   # 点击图文选项
```

### 2. XPath 定位

- 筛选按钮：`//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/span`
- 图文选项：`//*[@id="search-toolbar-container"]/div[1]/div/div/div[3]/div/div[5]/span[3`

### 3. 避免验证码

- 慢速操作（输入延迟 100ms）
- 随机等待（2-5秒）
- 保持登录状态（profile 目录持久化）

### 4. 热度计算

```python
def calculate_hot_score(likes, days_ago):
    """热度分数 = 点赞数 / 天数"""
    if days_ago <= 0:
        days_ago = 1
    return likes / days_ago
```

---

## 测试与验证

### 1. 依赖检查
```bash
python <skill_path>/scripts/check_deps.py
```

检查：
- Python版本（需要3.8+）
- 必需依赖（playwright, easyocr, openai, Pillow）
- Playwright浏览器
- 数据库状态
- LLM配置

### 2. 完整性测试
```bash
python <skill_path>/scripts/test_flow.py
```

测试：
- 数据库表结构完整性
- 必需字段是否存在
- 数据统计

### 3. 功能测试
```bash
# 测试采集
python <skill_path>/scripts/scrape.py --keyword "美食" --count 3

# 测试导出
python <skill_path>/scripts/export_md.py --keyword "美食"
```

---

## 参数说明

### full_workflow.py（推荐）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| --keyword | 搜索关键词 | 必填 |
| --count | 采集数量 | 10 |
| --min-likes | 最低点赞数 | 100 |
| --no-ocr | 跳过OCR识别 | False |
| --output | 输出文件名 | 自动生成 |

**热度计算示例：**
- 1天内270赞 → 270/1 = **270.00分**
- 3天内160赞 → 160/3 = **53.33分**
- 7天内1000赞 → 1000/7 = **142.86分**

### scrape.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| --keyword | 搜索关键词 | 必填 |
| --count | 采集数量 | 10 |
| --min-likes | 最低点赞数 | 100 |

### export_md.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| --keyword | 按关键词筛选 | 全部 |
| --min-likes | 最低点赞数 | 0 |
| --status | 按状态筛选 | 全部 |
| --output | 输出文件名 | 自动生成 |

### rewrite.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| --style | 风格编号 | 1 |
| --keyword | 指定关键词 | 全部 |

---

## 注意事项

1. **先登录**：采集前必须先执行 `login.py` 登录
2. **慢速操作**：避免触发验证码
3. **一周内**：筛选近期内容，提高热度准确度
4. **热度排序**：自动按点赞/天数排序，优先采集爆款
