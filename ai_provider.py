"""Thin AI provider abstraction. TwinEngine works fully without it."""
import os
from typing import Optional

import httpx

DEFAULT_BASE_URL = "https://api.openai.com/v1"


def get_config() -> dict:
    return {
        "provider": (os.getenv("AI_PROVIDER") or "none").strip().lower(),
        "api_key": (os.getenv("AI_API_KEY") or "").strip(),
        "model": (os.getenv("AI_MODEL") or "gpt-4o-mini").strip(),
        "base_url": (os.getenv("AI_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/"),
        "timeout": float(os.getenv("AI_TIMEOUT_SECONDS") or 20),
    }


def is_enabled() -> bool:
    cfg = get_config()
    return cfg["provider"] not in ("", "none", "disabled", "off") and bool(cfg["api_key"])


SYSTEM_PROMPT = """You are the explanation layer of HumanTwin AI, a decision-support digital twin.

STRICT RULES:
1. Never invent user history, deadlines, tasks or preferences.
2. Never claim certainty about future outcomes. Use "likely", "estimated", "risk of".
3. Only use the CONTEXT JSON provided. If something is missing, say it is missing.
4. Distinguish clearly between facts (from context), estimates and predictions.
5. Never make the decision for the user. Present trade-offs and let them choose.
6. Be concise: max 160 words. No markdown headings.
"""


async def complete(prompt: str, context_json: str) -> Optional[str]:
    if not is_enabled():
        return None
    cfg = get_config()
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"CONTEXT JSON:\n{context_json}\n\nREQUEST:\n{prompt}"},
        ],
        "temperature": 0.3,
        "max_tokens": 400,
    }
    headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
            res = await client.post(f"{cfg['base_url']}/chat/completions", json=payload, headers=headers)
            if res.status_code >= 400:
                return None
            data = res.json()
            text = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            return text.strip() or None
    except Exception:
        return None