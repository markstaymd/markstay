"""Pluggable LLM providers for the marker-survival eval.

Anthropic via the official async SDK; OpenAI-compatible families (OpenAI,
Moonshot/Kimi) via raw httpx so no extra packages are needed. Keys come from the
environment: set ANTHROPIC_API_KEY, OPENAI_API_KEY, and/or MOONSHOT_API_KEY for
whichever model families you run.
"""

import os
import httpx

# name -> (family, model_id)
MODELS = {
    "haiku": ("anthropic", "claude-haiku-4-5-20251001"),
    "sonnet": ("anthropic", "claude-sonnet-4-6"),
    "opus": ("anthropic", "claude-opus-4-8"),
    "gpt4o-mini": ("openai", "gpt-4o-mini"),
    "gpt4o": ("openai", "gpt-4o"),
    "kimi": ("moonshot", "kimi-k2-0905-preview"),
}

OPENAI_COMPAT = {
    "openai": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"),
    "moonshot": ("https://api.moonshot.ai/v1/chat/completions", "MOONSHOT_API_KEY"),
}

_anthropic_client = None


def _anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        _anthropic_client = AsyncAnthropic()
    return _anthropic_client


async def complete(model_name: str, prompt: str, max_tokens: int = 2000) -> str:
    family, model_id = MODELS[model_name]
    if family == "anthropic":
        resp = await _anthropic().messages.create(
            model=model_id,
            max_tokens=max_tokens,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

    url, key_env = OPENAI_COMPAT[family]
    key = os.environ.get(key_env)
    if not key:
        raise RuntimeError(f"{key_env} not set in environment")
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model_id,
                "temperature": 0,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
