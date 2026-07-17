from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.config import (
    LLM_MAX_RETRIES,
    LLM_TIMEOUT_SEC,
    MODEL_NAME,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)


class LLMError(Exception):
    pass


class DeepSeekClient:
    """OpenAI-compatible chat client pinned to DeepSeek defaults."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = (api_key if api_key is not None else OPENAI_API_KEY).strip()
        self.base_url = (base_url or OPENAI_BASE_URL).rstrip("/")
        self.model = model or MODEL_NAME

    def configured(self) -> bool:
        return bool(self.api_key) and not self.api_key.startswith("sk-xxx")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Tuple[str, Dict[str, int]]:
        if not self.configured():
            raise LLMError("未配置 OPENAI_API_KEY（DeepSeek Key）")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_err: Optional[Exception] = None
        for attempt in range(LLM_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=LLM_TIMEOUT_SEC) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code >= 400:
                    raise LLMError(f"LLM HTTP {resp.status_code}: {resp.text[:400]}")
                data = resp.json()
                content = data["choices"][0]["message"]["content"] or ""
                usage = data.get("usage") or {}
                tokens = {
                    "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                    "completion_tokens": int(usage.get("completion_tokens") or 0),
                }
                return content, tokens
            except (httpx.TimeoutException, httpx.TransportError, LLMError) as e:
                last_err = e
                if attempt < LLM_MAX_RETRIES:
                    await asyncio.sleep(0.6 * (attempt + 1))
                    continue
                break
        raise LLMError(f"LLM 调用失败: {last_err}")
