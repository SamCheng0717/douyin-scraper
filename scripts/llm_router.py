#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 多模型路由器
支持：OpenAI / DeepSeek / Gemini / GLM (智谱) / Ollama (本地)
配置方式：环境变量 或 llm_config.json

优先级：LLM_PROVIDER 指定 > 自动检测（按顺序找到第一个有 key 的）
"""
import os
import json
import sys
from pathlib import Path

# Windows 控制台 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ─────────────────────────────────────────
# 模型提供商配置表
# ─────────────────────────────────────────
PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "protocol": "openai",
    },
    "deepseek": {
        "name": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "protocol": "openai",  # DeepSeek 兼容 OpenAI 协议
    },
    "glm": {
        "name": "智谱 GLM",
        "env_key": "GLM_API_KEY",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-flash",
        "protocol": "openai",  # GLM4 兼容 OpenAI 协议
    },
    "gemini": {
        "name": "Google Gemini",
        "env_key": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-1.5-flash",
        "protocol": "gemini",  # Gemini 有独立协议
    },
    "ollama": {
        "name": "Ollama (本地)",
        "env_key": None,  # 无需 key
        "base_url": "http://localhost:11434/v1",
        "default_model": "qwen2.5:7b",
        "protocol": "openai",  # Ollama 也兼容 OpenAI 协议
    },
}

# 自动检测顺序（按优先级）
AUTO_DETECT_ORDER = ["openai", "deepseek", "glm", "gemini", "ollama"]


def load_config() -> dict:
    """
    加载配置：优先读 llm_config.json，再读环境变量
    返回格式：{"provider": "deepseek", "api_key": "...", "model": "...", "base_url": "..."}
    """
    config_path = Path(__file__).parent / "llm_config.json"

    file_cfg = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
        except Exception:
            pass

    # 合并：文件配置可被同名环境变量覆盖
    provider = (
        os.environ.get("LLM_PROVIDER")
        or file_cfg.get("provider", "")
    ).lower().strip()

    # 如果没指定 provider，自动检测
    if not provider:
        provider = _auto_detect_provider(file_cfg)

    if not provider:
        return {}

    preset = PROVIDERS.get(provider, {})

    # API Key 优先级：环境变量 > 配置文件 > provider 默认 env
    env_key_name = preset.get("env_key")
    api_key = (
        os.environ.get("LLM_API_KEY")
        or file_cfg.get("api_key", "")
        or (os.environ.get(env_key_name) if env_key_name else "")
    )

    model = (
        os.environ.get("LLM_MODEL")
        or file_cfg.get("model", "")
        or preset.get("default_model", "")
    )

    base_url = (
        os.environ.get("LLM_BASE_URL")
        or file_cfg.get("base_url", "")
        or preset.get("base_url", "")
    )

    return {
        "provider": provider,
        "name": preset.get("name", provider),
        "protocol": preset.get("protocol", "openai"),
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
    }


def _auto_detect_provider(file_cfg: dict) -> str:
    """按顺序检测哪个 provider 有可用的 key"""
    for p in AUTO_DETECT_ORDER:
        preset = PROVIDERS[p]
        env_key_name = preset.get("env_key")

        # Ollama 不需要 key，只要服务在跑就算可用
        if p == "ollama":
            if _check_ollama():
                return "ollama"
            continue

        has_key = (
            os.environ.get("LLM_API_KEY")
            or file_cfg.get("api_key")
            or (os.environ.get(env_key_name) if env_key_name else None)
        )
        if has_key:
            return p

    return ""


def _check_ollama() -> bool:
    """检测本地 Ollama 服务是否在运行"""
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


# ─────────────────────────────────────────
# 调用入口
# ─────────────────────────────────────────

def call_llm(prompt: str, system: str = "你是一位专业的内容创作者，擅长各种风格的文案写作。") -> str:
    """
    统一调用入口，自动路由到正确的 provider
    抛出异常时由调用方决定是否 fallback
    """
    cfg = load_config()

    if not cfg:
        raise RuntimeError("未找到任何可用的 LLM 配置，请设置 API Key 或配置 llm_config.json")

    provider = cfg["provider"]
    protocol = cfg["protocol"]

    print(f"   🤖 使用模型: {cfg['name']} / {cfg['model']}")

    if protocol == "gemini":
        return _call_gemini(prompt, system, cfg)
    else:
        return _call_openai_compat(prompt, system, cfg)


def _call_openai_compat(prompt: str, system: str, cfg: dict) -> str:
    """OpenAI 兼容协议（OpenAI / DeepSeek / GLM / Ollama）"""
    import requests

    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = f"Bearer {cfg['api_key']}"

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1500,
        "temperature": 0.8,
    }

    url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
    resp = requests.post(url, headers=headers, json=payload, timeout=90)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_gemini(prompt: str, system: str, cfg: dict) -> str:
    """Google Gemini 原生 API"""
    import requests

    api_key = cfg["api_key"]
    model = cfg["model"]
    url = f"{cfg['base_url'].rstrip('/')}/models/{model}:generateContent?key={api_key}"

    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.8},
    }

    resp = requests.post(url, json=payload, timeout=90)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


# ─────────────────────────────────────────
# 配置向导
# ─────────────────────────────────────────

def setup_wizard():
    """交互式配置向导，生成 llm_config.json"""
    print("\n" + "=" * 55)
    print("⚙️  LLM 模型配置向导")
    print("=" * 55)
    print("\n支持的模型提供商：")

    choices = list(PROVIDERS.keys())
    for i, k in enumerate(choices, 1):
        p = PROVIDERS[k]
        key_hint = f"需要 {p['env_key']}" if p.get("env_key") else "无需 Key（本地服务）"
        print(f"  {i}. {p['name']:<20} {key_hint}")

    print()
    while True:
        sel = input("请选择提供商编号（1 - {}）：".format(len(choices))).strip()
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(choices):
                provider_key = choices[idx]
                break
        except ValueError:
            pass
        print("  ⚠️  无效选项")

    preset = PROVIDERS[provider_key]
    cfg = {"provider": provider_key}

    # API Key
    if preset.get("env_key"):
        existing = os.environ.get(preset["env_key"], "")
        if existing:
            print(f"\n✅ 已检测到环境变量 {preset['env_key']}，无需重复填写")
            cfg["api_key"] = ""
        else:
            key = input(f"\n请输入 {preset['name']} API Key：").strip()
            cfg["api_key"] = key
    else:
        cfg["api_key"] = ""

    # 模型名
    default_model = preset["default_model"]
    model = input(f"\n模型名称（直接回车使用默认 {default_model}）：").strip()
    cfg["model"] = model or default_model

    # Base URL（可自定义，比如代理）
    default_url = preset["base_url"]
    url = input(f"\nAPI 地址（直接回车使用默认）\n  默认：{default_url}\n  → ").strip()
    cfg["base_url"] = url or default_url

    # 保存
    config_path = Path(__file__).parent / "llm_config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 配置已保存到：{config_path}")
    print(f"   Provider : {PROVIDERS[provider_key]['name']}")
    print(f"   Model    : {cfg['model']}")
    print(f"   Base URL : {cfg['base_url']}")

    # 测试连通性
    test = input("\n是否测试连接？(Y/n): ").strip().lower()
    if test != "n":
        print("\n⏳ 正在测试...")
        try:
            result = call_llm("请用一句话介绍你自己。")
            print(f"✅ 连接成功！模型回复：{result[:80]}...")
        except Exception as e:
            print(f"❌ 连接失败：{e}")


def show_current_config():
    """显示当前生效的配置"""
    cfg = load_config()
    if not cfg:
        print("⚠️  未配置任何 LLM，将使用内置模板生成内容")
        print("\n可通过以下方式配置：")
        print("  1. 运行配置向导：python llm_router.py --setup")
        print("  2. 设置环境变量：DEEPSEEK_API_KEY / OPENAI_API_KEY / GLM_API_KEY / GEMINI_API_KEY")
        print("  3. 创建 scripts/llm_config.json")
        return

    print(f"\n当前 LLM 配置：")
    print(f"  Provider : {cfg['name']}")
    print(f"  Model    : {cfg['model']}")
    print(f"  Base URL : {cfg['base_url']}")
    key_display = cfg['api_key'][:8] + "****" if cfg.get('api_key') else "（来自环境变量）"
    print(f"  API Key  : {key_display}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM 路由器工具")
    parser.add_argument("--setup", action="store_true", help="运行配置向导")
    parser.add_argument("--show", action="store_true", help="显示当前配置")
    parser.add_argument("--test", type=str, metavar="PROMPT", help="发送测试消息")
    args = parser.parse_args()

    if args.setup:
        setup_wizard()
    elif args.show:
        show_current_config()
    elif args.test:
        try:
            result = call_llm(args.test)
            print(f"\n模型回复：\n{result}")
        except Exception as e:
            print(f"❌ 调用失败: {e}")
    else:
        show_current_config()
