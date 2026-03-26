# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**douyin-scraper** — a skill for collecting high-engagement Douyin (TikTok China) image-text (图文) notes, capturing images via Playwright, and running OCR to extract text. Output is a Markdown report per keyword.

## Pipeline Commands

```bash
# 1. Login (browser opens for QR scan)
python scripts/login.py

# 2. Scrape + OCR in one step
python scripts/full_workflow.py --keyword "韩国医美" --count 10
python scripts/full_workflow.py --keyword "减肥餐" --count 5 --no-ocr  # skip OCR
```

## Architecture

**Data flow:** `full_workflow.py` → search Douyin → filter 图文 + 一周内 → collect note IDs → detail page → Playwright screenshot → Baidu PaddleOCR → clean OCR text → `output/*.md`

**No database** — results are written directly to Markdown reports in `output/`.

**Key files:**
- `scripts/full_workflow.py` — single-script pipeline (login state, scrape, screenshot, OCR, report)
- `scripts/login.py` — opens browser for QR scan, persists session to `profile/`
- `scripts/db.py` — legacy SQLite module, kept for reference but not used by full_workflow.py

**OCR:**
- Provider: Baidu PaddleOCR API (`BAIDU_PADDLEOCR_TOKEN` in `.env`)
- Images captured via `element.screenshot()` (bypasses Douyin URL anti-scraping)
- Noise filter: `clean_ocr_text()` strips Douyin nav bar text (抖音/精选/推荐/关注 etc.)

**Output:** Markdown files named `notes_{keyword}_{timestamp}.md` in `output/`

## Important Notes

- Browser runs headless=False to avoid bot detection; login state persisted in `profile/`
- Images saved to `data/images/` as `{keyword}_{note_idx}_{img_idx}.png`
- 图文 filter: only collects `waterfall_item_*` elements whose `textContent` contains "图文"
- Hot score formula: `likes / days_ago` (small days_ago → very recent posts rank high)
- Windows UTF-8 console fix (`sys.stdout.reconfigure`) applied at top of full_workflow.py
