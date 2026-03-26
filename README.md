# douyin-scraper

抖音图文笔记采集工具 — 搜索关键词，自动筛选「图文」类型，截图并 OCR 识别图片文字，输出 Markdown 报告。

## 功能

- 关键词搜索 + 自动筛选「图文 · 一周内」
- Playwright 浏览器截图（绕过抖音 URL 反爬虫）
- Baidu PaddleOCR 识别图片中的中英文
- OCR 噪音过滤（去除截图中的抖音导航栏文字）
- 热度评分（点赞数 / 发布天数）
- 输出带目录的 Markdown 报告

## 环境要求

- Python 3.9+
- Playwright（Chromium）

```bash
pip install playwright python-dotenv requests
playwright install chromium
```

## 配置

在项目根目录创建 `.env`：

```
BAIDU_PADDLEOCR_TOKEN=你的token
```

> 获取 Token：[百度 PaddleOCR API](https://aistudio.baidu.com/)

## 使用

### 1. 登录

```bash
python scripts/login.py
```

浏览器会打开抖音，扫码登录后关闭即可。登录状态保存在 `profile/`，后续无需重复登录。

### 2. 采集

```bash
python scripts/full_workflow.py --keyword "韩国医美" --count 10
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--keyword` | 搜索关键词 | 必填 |
| `--count` | 采集笔记数量 | `5` |
| `--no-ocr` | 跳过 OCR（只截图） | 关闭 |

### 输出

报告保存在 `output/notes_{keyword}_{timestamp}.md`，图片保存在 `data/images/`。

报告包含：
- 每篇笔记的标题、作者、点赞数、发布时间、链接
- 热度评分排序依据
- OCR 识别的图片文字
- 图片本地路径

## 项目结构

```
douyin-scraper/
├── scripts/
│   ├── full_workflow.py   # 主流水线（搜索→截图→OCR→报告）
│   └── login.py           # 登录并保存 session
├── data/
│   └── images/            # 截图保存目录
├── output/                # Markdown 报告输出目录
├── profile/               # 浏览器登录状态
└── .env                   # Token 配置
```

## 注意事项

- 浏览器以有头模式运行（headless=False），避免被检测为机器人
- 仅采集「图文」类型笔记，视频会自动过滤
- OCR 对纯图片（无文字）效果有限，属正常现象
