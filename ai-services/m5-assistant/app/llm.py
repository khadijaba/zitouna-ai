"""LLM access with rotation across free providers/models.

All providers are called through the OpenAI-compatible "chat completions" API, so adding one is
one entry in PROVIDERS. A model that fails (429 quota, 503 overloaded, timeout...) is put in cooldown
and the next one in the chain is tried. Rotate across providers/models, never across several
accounts of the same provider (against most terms of service).
"""

import json
import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

log = logging.getLogger("m5.llm")

# name -> (base URL of the OpenAI-compatible API, env var holding the key)
PROVIDERS = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "xai": ("https://api.x.ai/v1", "XAI_API_KEY"),
}

# Tried in this order. "extra" = provider/model specific parameters.
# gemini-3.5-flash "thinks" by default, which eats the token budget: reasoning_effort=none turns it off.
# The lite models do not think and reject that parameter. Same for qwen on Groq (~0.4 s per answer);
# groq/openai/gpt-oss-120b was tried and left out: it invented figures and mixed scripts.
DEFAULT_CHAIN = [
    {"provider": "gemini", "model": "gemini-3.5-flash", "extra": {"reasoning_effort": "none"}},
    {"provider": "groq", "model": "qwen/qwen3.8-27b", "extra": {"reasoning_effort": "none"}},
    {"provider": "gemini", "model": "gemini-2.5-flash", "extra": {"reasoning_effort": "none"}},
    {"provider": "gemini", "model": "gemini-3.5-flash-lite"},
    {"provider": "gemini", "model": "gemini-flash-lite-latest"},
    {"provider": "openrouter", "model": "meta-llama/llama-3.3-70b-instruct:free"},
]

COOLDOWN_S = {"rate_limited": 60, "unavailable": 20, "misconfigured": 600}


class AllProvidersFailed(RuntimeError):
    pass


@dataclass
class Model:
    provider: str
    model: str
    base_url: str
    api_key: str
    extra: dict = field(default_factory=dict)
    cooldown_until: float = 0.0

    @property
    def name(self) -> str:
        return f"{self.provider}/{self.model}"


@dataclass
class Completion:
    text: str
    provider: str
    model: str
    latency_ms: int


def build_chain(chain: list[dict] | None = None, env: dict | None = None) -> list["Model"]:
    """Chain from LLM_CHAIN (JSON) or DEFAULT_CHAIN. Entries without an API key are skipped."""
    env = os.environ if env is None else env
    if chain is None:
        chain = json.loads(env["LLM_CHAIN"]) if env.get("LLM_CHAIN") else DEFAULT_CHAIN
    models = []
    for entry in chain:
        base_url, key_var = PROVIDERS[entry["provider"]]
        if env.get(key_var):
            models.append(Model(entry["provider"], entry["model"], base_url, env[key_var], entry.get("extra", {})))
    return models


class LlmRouter:
    def __init__(self, models: list[Model], client: httpx.Client | None = None, timeout_s: float = 5.0,
                 deadline_s: float = 12.0, max_tokens: int = 700):  # fmt: skip
        self.models = models
        self.client = client or httpx.Client()
        self.timeout_s = timeout_s
        self.deadline_s = deadline_s
        self.max_tokens = max_tokens

    @property
    def enabled(self) -> bool:
        return bool(self.models)

    def complete(self, messages: list[dict], temperature: float = 0.3,
                 accept: Callable[[str], bool] | None = None) -> Completion:  # fmt: skip
        """accept: optional check of the answer text; a rejected answer moves on to the next model."""
        started = time.monotonic()
        errors = []
        for m in self.models:
            now = time.monotonic()
            if m.cooldown_until > now:
                errors.append(f"{m.name}: cooling down")
                continue
            remaining = self.deadline_s - (now - started)
            if remaining < 1:
                errors.append("deadline reached")
                break
            try:
                text, ms = self._call(m, messages, temperature, min(self.timeout_s, remaining))
                if accept and not accept(text):
                    raise _Failure("rejected", f"answer rejected by the check: {text[:80]!r}")
                log.info("llm=%s latency_ms=%d", m.name, ms)
                return Completion(text, m.provider, m.model, ms)
            except _Failure as f:
                m.cooldown_until = time.monotonic() + COOLDOWN_S.get(f.kind, 0)
                log.warning("llm=%s failed (%s): %s", m.name, f.kind, f)
                errors.append(f"{m.name}: {f.kind}")
        raise AllProvidersFailed("; ".join(errors) or "no LLM configured")

    def _call(self, m: Model, messages: list[dict], temperature: float, timeout_s: float) -> tuple[str, int]:
        body = {"model": m.model, "messages": messages, "temperature": temperature, "max_tokens": self.max_tokens,
                **m.extra}  # fmt: skip
        t0 = time.monotonic()
        try:
            res = self.client.post(f"{m.base_url}/chat/completions", json=body, timeout=timeout_s,
                                   headers={"Authorization": f"Bearer {m.api_key}"})  # fmt: skip
        except httpx.TimeoutException as e:
            raise _Failure("unavailable", "timeout") from e
        except httpx.HTTPError as e:
            raise _Failure("unavailable", type(e).__name__) from e
        ms = int((time.monotonic() - t0) * 1000)

        if res.status_code == 429:
            raise _Failure("rate_limited", "HTTP 429")
        if res.status_code >= 500:
            raise _Failure("unavailable", f"HTTP {res.status_code}")
        if res.status_code >= 400:
            raise _Failure("misconfigured", f"HTTP {res.status_code}: {res.text[:200]}")

        choice = (res.json().get("choices") or [{}])[0]
        text = ((choice.get("message") or {}).get("content") or "").strip()
        if not text or choice.get("finish_reason") == "length":
            # A cut answer ("(données de démo") is worse than the next model's full answer.
            raise _Failure("empty", f"empty or truncated answer (finish_reason={choice.get('finish_reason')})")
        return text, ms


class _Failure(Exception):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
