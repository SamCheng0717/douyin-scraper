# Changelog

## [Unreleased]

## [0.2.0] - 2026-03-26

### Changed
- 项目重命名：`douyin-creator` → `douyin-scraper`
- 移除二创（LLM 改写）功能，专注图文采集
- 更新 CLAUDE.md 反映新定位

### Removed
- `scripts/rewrite.py` — LLM 二创脚本
- `scripts/llm_router.py` — LLM 统一调用模块
- `scripts/llm_config.json` — LLM 配置文件
- `scripts/ocr.py` — 独立 OCR 脚本（功能已内置于 full_workflow.py）
- `scripts/scrape.py` / `scrape_fixed.py` / `scrape_with_images.py` / `scrape_and_ocr.py` — 旧版采集脚本
- `references/styles.md` — 二创风格说明

## [0.1.0] - 2026-03-25

### Added
- `scripts/full_workflow.py` — 一体化流水线：搜索 → 筛选图文 → 截图 → OCR → Markdown 报告
- Playwright `element.screenshot()` 截图，绕过抖音 URL 反爬虫
- Baidu PaddleOCR API 集成（`BAIDU_PADDLEOCR_TOKEN`）
- OCR 噪音过滤：`clean_ocr_text()` 去除抖音导航栏文字（精选/推荐/关注等及其变体）
- 图文过滤：仅采集 `waterfall_item_*` 中含「图文」标签的笔记，排除视频
- 「图文 · 一周内」双重筛选
- 热度评分：`likes / days_ago`
- 多图笔记支持（逐张截图 + OCR）
- 图片去重（按 src 前缀）
