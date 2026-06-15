"""Pluggable LLM providers for the marker-survival eval.

Anthropic via the official async SDK; OpenAI-compatible families (OpenAI,
Moonshot/Kimi) via raw httpx so no extra packages are needed. Keys come from the
environment (source ~/.credentials/unlock.sh before running).
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
    "kimi": ("moonshot", "kimi-k2.6"),
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


async def complete(model_name: str, prompt: str, max_tokens: int = 8000) -> str:
    # 8000, not the doc length: reasoning models (Kimi k2.x) spend completion
    # tokens on hidden `reasoning_content` before the answer, so a tight cap
    # truncates the visible output to empty. Non-reasoning models stop at their
    # natural completion well under this, so the higher ceiling is free for them.
    family, model_id = MODELS[model_name]
    if family == "anthropic":
        kwargs = dict(
            model=model_id,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        # Newer Anthropic models (e.g. opus 4.8) reject `temperature`; older ones
        # still accept it and we want temp 0 there for determinism.
        if not model_id.startswith("claude-opus-4-8"):
            kwargs["temperature"] = 0
        resp = await _anthropic().messages.create(**kwargs)
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

    url, key_env = OPENAI_COMPAT[family]
    key = os.environ.get(key_env)
    if not key:
        raise RuntimeError(f"{key_env} not set in environment")
    payload = {
        "model": model_id,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    # Most OpenAI-compatible models honour temperature 0 for determinism, but the
    # Kimi k2.x line rejects anything but 1 ("only 1 is allowed for this model"),
    # so omit it there and take the model default.
    if not model_id.startswith("kimi-k2"):
        payload["temperature"] = 0
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
