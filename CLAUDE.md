# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

抖音图文笔记二创流水线 — a skill for collecting high-engagement Douyin (TikTok China) image-text notes, running OCR on images, and generating rewritten content via LLM.

## Pipeline Commands

All scripts are run from the `scripts/` directory or with the full path. The pipeline flows in order:

```bash
# 1. Login (browser opens for QR scan)
python scripts/login.py

# 2. Scrape image-text notes
python scripts/scrape.py --keyword "韩国医美" --count 10 --min-likes 1000

# 3. OCR all pending notes
python scripts/ocr.py [--keyword "韩国医美"] [--limit 5]

# 4. Rewrite in chosen style
python scripts/rewrite.py --style 1 --keyword "韩国医美" [--limit 5]

# LLM config
python scripts/llm_router.py --setup   # interactive wizard
python scripts/llm_router.py --show    # show current config
python scripts/llm_router.py --test "prompt"
```

## Architecture

**Data flow:** scrape.py → `data/douyin.db` → ocr.py updates `ocr_text` + sets `status='ocr_done'` → rewrite.py reads `ocr_done` notes → `output/*.md`

**Note status lifecycle:** `pending` → `ocr_done` → `processed`

**Key modules:**
- `scripts/db.py` — all SQLite operations; import this rather than writing raw SQL elsewhere
- `scripts/llm_router.py` — unified LLM call via `call_llm(prompt, system)`, auto-detects provider from env vars or `scripts/llm_config.json`
- `scripts/scrape.py` — Playwright-based scraper with anti-detection (headless=False, human-like typing/scrolling)
- `scripts/ocr.py` — uses `easyocr` for Chinese+English OCR
- `scripts/rewrite.py` — 6 writing styles defined in `STYLES` dict; note it uses `openai` SDK directly (not `llm_router.py`)

**LLM configuration priority:** `LLM_PROVIDER` env var > `llm_config.json` > auto-detect. Supported providers: openai, deepseek, glm, gemini, ollama. Config file lives at `scripts/llm_config.json`.

**Rewrite styles 1-6:** 爆款标题党, 深度干货流, 轻松闲聊风, 励志鸡汤风, 种草带货风, 短视频脚本. Full style specs in `references/styles.md`.

## Important Notes

- `scrape.py` contains its own inline `init_db()`/`save_note()` that duplicates `db.py` — `db.py` is the canonical module
- `rewrite.py` has its own `get_llm_client()` that reads `llm_config.json` directly, while `llm_router.py` provides the unified `call_llm()` — these are parallel implementations
- The scraper runs headless=False (visible browser) to avoid bot detection; login state is persisted in `profile/`
- Images are saved to `data/images/`, DB at `data/douyin.db`
- Output Markdown files are named `{keyword}_{style}_{timestamp}.md` in `output/`
- Windows UTF-8 console fix (`sys.stdout.reconfigure`) is applied at top of `ocr.py` and `rewrite.py`
