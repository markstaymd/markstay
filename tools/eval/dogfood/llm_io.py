"""Shared truncation-aware model call for the dogfood runners.

A full-document rewrite that hits the output-token cap looks like a mass drop but is
an artifact, so callers need to know when that happened. Anthropic exposes
stop_reason directly; OpenAI-compat models return None (caller falls back to a
length-ratio guard). Keeps the network dependency out of dogfood_sim.py (the pure
classification lib).
"""

from __future__ import annotations

import sys
from pathlib import Path

# providers.py lives one dir up (eval/).
_EVAL = Path(__file__).resolve().parents[1]
if str(_EVAL) not in sys.path:
    sys.path.insert(0, str(_EVAL))
import providers as P  # noqa: E402


async def complete_meta(model_name: str, prompt: str, max_tokens: int):
    """Returns (text, hit_cap) where hit_cap is True/False for Anthropic models and
    None for OpenAI-compat models (no clean stop_reason plumbed)."""
    family, model_id = P.MODELS[model_name]
    if family == "anthropic":
        kwargs = dict(model=model_id, max_tokens=max_tokens,
                      messages=[{"role": "user", "content": prompt}])
        if not model_id.startswith("claude-opus-4-8"):
            kwargs["temperature"] = 0
        resp = await P._anthropic().messages.create(**kwargs)
        text = "".join(b.text for b in resp.content
                       if getattr(b, "type", None) == "text")
        return text, (resp.stop_reason == "max_tokens")
    text = await P.complete(model_name, prompt, max_tokens=max_tokens)
    return text, None
