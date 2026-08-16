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
    "sonnet": ("anthropic", "claude-sonnet-5"),
    "opus": ("anthropic", "claude-opus-4-8"),
    "gpt4o-mini": ("openai", "gpt-4o-mini"),
    "gpt4o": ("openai", "gpt-4o"),
    "kimi": ("moonshot", "kimi-k2.6"),
}

OPENAI_COMPAT = {
    "openai": ("https://api.openai.com/v1/chat/completions", "OPENAI_API_KEY"),
    "moonshot": ("https://api.moonshot.ai/v1/chat/completions", "MOONSHOT_API_KEY"),
}

# The eval's Anthropic key is read from MARKSTAY_EVAL_API_KEY, NOT from the SDK's
# default ANTHROPIC_API_KEY, and the name is load-bearing rather than cosmetic.
#
# `ANTHROPIC_API_KEY` is Claude Code's own auth variable. Exporting it to run this
# eval hijacks any Claude Code session launched from the same shell: the session
# silently switches from subscription auth to API billing (so its own tokens are
# charged to the eval's credit, and a reasoning-heavy session can outspend the
# measurement it was launched to run), and the claude.ai identity resolves to null,
# which makes the Gmail / Calendar / Drive connectors disappear. Both are recorded
# in ~/.claude/CLAUDE.md; the second cost a session on 2026-07-31 and the first was
# hit on 2026-08-16 launching the sub-block measurement.
#
# A namespaced name keeps the two apart: this process gets a paid key, and Claude
# Code keeps its subscription auth, from the same shell at the same time.
_EVAL_KEY_ENV = "MARKSTAY_EVAL_API_KEY"

_anthropic_client = None

# Newer Anthropic models reject `temperature` outright ("`temperature` is deprecated
# for this model", a 400 on the first call); older ones still accept it and we want
# temp 0 there for determinism. A deny-list rather than an allow-list because it is
# the newer end that drops the parameter, so a model absent from it is assumed to be
# an older one that still honours temp 0. Confirmed rejecting: opus 4.8, sonnet 5.
# Confirmed accepting: haiku 4.5.
#
# This lives in one function because both call sites (here and llm_io.complete_meta)
# build their own request kwargs, and a copy of the rule in each is a copy that goes
# stale: the sub-block measurement's first sonnet-5 smoke failed twice for exactly
# that reason, once per site.
_NO_TEMPERATURE = ("claude-opus-4-8", "claude-opus-5", "claude-sonnet-5")


def anthropic_kwargs(model_id: str, prompt: str, max_tokens: int) -> dict:
    """Request kwargs for an Anthropic completion, temperature included only where
    the model still accepts it, and extended thinking off everywhere.

    Thinking is disabled deliberately, and it is not a cost tweak. Sonnet 5 reasons
    by default and bills those tokens against the same `max_tokens` ceiling as the
    answer, so a full-document rewrite silently returns **zero text blocks**: the
    first paid attempt at the sub-block measurement lost 24 of 48 sonnet cells that
    way, 9 of them empty (`stop_reason=max_tokens`, `thinking_tokens=16000`, no text
    block at all). That is the same failure the Kimi k2.x note in `complete` below
    describes, arriving on the Anthropic side.

    Raising the cap would have papered over it at real expense. Off is also the
    faithful setting: these runners measure single-pass document-rewrite fidelity,
    and the results they are compared against were produced by non-thinking models,
    so leaving it on would change the experiment rather than sharpen it.
    """
    kwargs = dict(
        model=model_id,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        thinking={"type": "disabled"},
        # An explicit per-request timeout is what makes a large `max_tokens` legal
        # without streaming: above ~20k the SDK refuses outright ("Streaming is
        # required for operations that may take longer than 10 minutes") unless the
        # caller states how long it is willing to wait. These runners want the whole
        # rewritten document as one string, so setting the bound is much less
        # invasive than restructuring every call site around a stream.
        timeout=1200.0,
    )
    if not model_id.startswith(_NO_TEMPERATURE):
        kwargs["temperature"] = 0
    return kwargs


def _anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import AsyncAnthropic
        key = os.environ.get(_EVAL_KEY_ENV) or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                f"{_EVAL_KEY_ENV} is not set. Export the paid key under that name, "
                "not ANTHROPIC_API_KEY, which is Claude Code's own auth variable:\n"
                f'  read -rsp "key: " {_EVAL_KEY_ENV} && export {_EVAL_KEY_ENV} && echo'
            )
        _anthropic_client = AsyncAnthropic(api_key=key)
    return _anthropic_client


async def complete(model_name: str, prompt: str, max_tokens: int = 8000) -> str:
    # 8000, not the doc length: reasoning models (Kimi k2.x) spend completion
    # tokens on hidden `reasoning_content` before the answer, so a tight cap
    # truncates the visible output to empty. Non-reasoning models stop at their
    # natural completion well under this, so the higher ceiling is free for them.
    family, model_id = MODELS[model_name]
    if family == "anthropic":
        resp = await _anthropic().messages.create(
            **anthropic_kwargs(model_id, prompt, max_tokens)
        )
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
