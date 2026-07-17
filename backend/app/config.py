from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", encoding="utf-8-sig")
load_dotenv(BACKEND / ".env", encoding="utf-8-sig")


def _truthy(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat").strip() or "deepseek-chat"

FEATURE_SUMMARY = _truthy("FEATURE_SUMMARY", "1")
FEATURE_CACHE = _truthy("FEATURE_CACHE", "1")

AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "8"))
LLM_TIMEOUT_SEC = float(os.getenv("LLM_TIMEOUT_SEC", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))

CACHE_DIR = Path(os.getenv("CACHE_DIR", str(ROOT / ".cache" / "rca")))
FIXTURES_LOGS = BACKEND / "fixtures" / "logs"
PROMPTS_DIR = BACKEND / "prompts"
