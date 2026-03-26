---
name: douyin-scraper
description: 抖音图文笔记采集工具。搜索关键词 → 自动筛选「图文·一周内」→ Playwright 截图（绕过反爬虫）→ Baidu OCR 识别图片文字 → 输出 Markdown 报告（含热度评分）。当用户提到"抖音图文采集"、"抖音笔记抓取"、"抖音爬虫"、"抖音内容采集"等场景时加载此技能。
---

# douyin-scraper

抖音图文笔记采集工具 —— 一条命令完成：搜索 → 筛选图文 → 截图 → OCR → Markdown 报告。

## ⚠️ 前置配置

### 1. 安装依赖

```bash
pip install playwright requests python-dotenv
python -m playwright install chromium
```

### 2. 配置 Baidu PaddleOCR Token

在技能目录创建 `.env`：

```
BAIDU_PADDLEOCR_TOKEN=你的token
```

获取 Token：访问 [百度 AI Studio](https://aistudio.baidu.com/paddleocr)，免费注册，每天 1 万次免费调用。

### 3. 登录抖音（只需一次）

```bash
python <skill_path>/scripts/login.py
```

浏览器打开抖音，扫码登录后关闭。登录状态自动保存，后续无需重复操作。

---

## 使用

```bash
# 采集 10 篇图文笔记（含 OCR）
python <skill_path>/scripts/full_workflow.py --keyword "韩国医美"

# 指定数量
python <skill_path>/scripts/full_workflow.py --keyword "减肥餐" --count 5

# 跳过 OCR（仅截图）
python <skill_path>/scripts/full_workflow.py --keyword "咖啡" --no-ocr
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--keyword` | 搜索关键词 | 必填 |
| `--count` | 采集笔记数量 | `5` |
| `--no-ocr` | 跳过 OCR | 关闭 |

---

## 输出

报告保存至 `output/notes_{keyword}_{timestamp}.md`，图片保存至 `data/images/`。

每篇笔记包含：

- 🔥 热度分数（点赞数 / 发布天数）及计算公式
- 👍 点赞数、发布时间、作者、原文链接
- 📝 原文描述
- 🔍 OCR 识别的图片文字（支持多图）
- 🖼️ 本地截图路径

---

## 技术特点

- **Playwright 截图**：通过 `element.screenshot()` 截取内容图，绕过抖音图片 URL 反爬虫
- **图文过滤**：自动识别并跳过视频，只采集「图文」类型笔记
- **OCR 噪音过滤**：自动去除截图中的抖音导航栏文字（精选/推荐/关注 等）
- **多图支持**：一篇图文多张图片逐张截图 + OCR，合并识别结果
- **反检测**：有头浏览器（headless=False）+ 拟人操作节奏，避免触发验证码
- **热度公式**：`likes / days_ago`，越新越热排越前

---

## 目录结构

```
douyin-scraper/
├── scripts/
│   ├── full_workflow.py   # 主流水线
│   └── login.py           # 登录脚本
├── data/
│   └── images/            # 截图
├── output/                # Markdown 报告
├── profile/               # 浏览器登录状态
└── .env                   # Token 配置
```
