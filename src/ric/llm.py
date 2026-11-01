"""Minimal client for any OpenAI-compatible chat endpoint (Groq, Gemini, OpenRouter, Ollama, llm-gateway).

Configure with LLM_BASE_URL, LLM_API_KEY and LLM_MODEL. With none set, the copilot runs in
offline mode and never calls a model.
"""
from __future__ import annotations

import json
import os
import urllib.request


def enabled() -> bool:
    return bool(os.getenv("LLM_BASE_URL") and os.getenv("LLM_MODEL"))


def chat(messages: list[dict], temperature: float = 0.0, timeout: int = 60) -> str:
    req = urllib.request.Request(
        os.environ["LLM_BASE_URL"].rstrip("/") + "/chat/completions",
        data=json.dumps({"model": os.environ["LLM_MODEL"], "messages": messages,
                         "temperature": temperature}).encode(),
        headers={"Authorization": f"Bearer {os.getenv('LLM_API_KEY', 'none')}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)["choices"][0]["message"]["content"].strip()
