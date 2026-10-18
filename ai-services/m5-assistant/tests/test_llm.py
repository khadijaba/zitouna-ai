"""LLM rotation and /answer, with a fake HTTP transport: no network, no API key needed."""

import json
import os

import httpx
import pytest

from app.llm import AllProvidersFailed, LlmRouter, Model, build_chain
from app.prompt import build_messages, is_arabic_script
from app.schemas import AnswerRequest

OK = {"choices": [{"message": {"content": "اسقي زيتونك 3 مرات الجمعة هاذي."}, "finish_reason": "stop"}]}
ARABIZI = {"choices": [{"message": {"content": "Esgi zitounek 3 marrat had el jem3a."}, "finish_reason": "stop"}]}


def models(*names: str) -> list[Model]:
    return [Model("p", n, f"https://{n}.test/v1", "key") for n in names]


def router_with(responses: dict[str, httpx.Response | Exception], **kwargs) -> tuple[LlmRouter, list[str]]:
    """responses: model name -> response (or exception) returned for that model."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        name = json.loads(request.content)["model"]
        calls.append(name)
        res = responses[name]
        if isinstance(res, Exception):
            raise res
        return res

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return LlmRouter(models(*responses), client=client, **kwargs), calls


def test_first_model_answers():
    router, calls = router_with({"a": httpx.Response(200, json=OK), "b": httpx.Response(200, json=OK)})
    done = router.complete([{"role": "user", "content": "x"}])
    assert (done.model, done.text, calls) == ("a", "اسقي زيتونك 3 مرات الجمعة هاذي.", ["a"])


@pytest.mark.parametrize(
    "failure",
    [httpx.Response(429), httpx.Response(503), httpx.Response(400, text="bad"), httpx.ReadTimeout("slow")],
    ids=["quota", "overloaded", "bad-request", "timeout"],
)
def test_rotates_to_next_model_and_cools_down_the_failing_one(failure):
    router, calls = router_with({"a": failure, "b": httpx.Response(200, json=OK)})
    assert router.complete([{"role": "user", "content": "x"}]).model == "b"
    assert router.complete([{"role": "user", "content": "x"}]).model == "b"
    assert calls == ["a", "b", "b"]  # "a" is skipped while cooling down


def test_truncated_answer_counts_as_failure():
    cut = {"choices": [{"message": {"content": "Aslema, l"}, "finish_reason": "length"}]}
    router, _ = router_with({"a": httpx.Response(200, json=cut), "b": httpx.Response(200, json=OK)})
    assert router.complete([{"role": "user", "content": "x"}]).model == "b"


def test_rejected_answer_moves_to_next_model_without_cooldown():
    router, calls = router_with({"a": httpx.Response(200, json=ARABIZI), "b": httpx.Response(200, json=OK)})
    assert router.complete([], accept=is_arabic_script).model == "b"
    assert router.complete([]).model == "a"  # no cooldown: "a" is fine for answers that need no check
    assert calls == ["a", "b", "a"]


@pytest.mark.parametrize(
    ("text", "arabic"),
    [
        ("اسقي زيتونك 3 مرات الجمعة هاذي.", True),
        ("في القطعة « Henchir Smoke » لازمك تسقي 6 مرات، ابعثلي تصويرة من صفحة « Diagnostic ».", True),
        ("Esgi zitounek 3 marrat had el jem3a.", False),
        ("Il faut irriguer 3 fois cette semaine.", False),
        ("12.5 TND", False),
    ],
)
def test_is_arabic_script(text, arabic):
    assert is_arabic_script(text) is arabic


def test_all_failing_raises():
    router, _ = router_with({"a": httpx.Response(429), "b": httpx.Response(500)})
    with pytest.raises(AllProvidersFailed, match="p/a: rate_limited; p/b: unavailable"):
        router.complete([{"role": "user", "content": "x"}])


def test_sends_model_specific_parameters():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        seen["auth"] = request.headers["Authorization"]
        return httpx.Response(200, json=OK)

    m = Model("gemini", "gemini-3.5-flash", "https://x.test/v1", "secret", {"reasoning_effort": "none"})
    LlmRouter([m], client=httpx.Client(transport=httpx.MockTransport(handler))).complete([])
    assert seen["reasoning_effort"] == "none" and seen["auth"] == "Bearer secret"


def test_chain_skips_providers_without_key():
    chain = build_chain(env={"GEMINI_API_KEY": "k"})
    assert chain and all(m.provider == "gemini" for m in chain)
    assert build_chain(env={}) == []


def test_prompt_contains_question_facts_and_rules():
    req = AnswerRequest(question="9adech nesgi?", intent="irrigation",
                        facts=[{"source": "M2", "mock": True, "data": {"jours_irrigation": 6}}])  # fmt: skip
    messages = build_messages(req)
    assert messages[0]["role"] == "system" and "UNIQUEMENT ceux des faits fournis" in messages[0]["content"]
    assert "9adech nesgi?" in messages[-1]["content"] and '"jours_irrigation": 6' in messages[-1]["content"]


# ---- /answer endpoint ----


def test_answer_endpoint_uses_the_router(client):
    router, _ = router_with({"a": httpx.Response(200, json=OK)})
    client.app.state.llm, saved = router, client.app.state.llm
    try:
        fact = {"source": "M2", "mock": False, "data": {"jours": 3}}
        res = client.post("/answer", json={"question": "9adech nesgi?", "intent": "irrigation", "facts": [fact]})
    finally:
        client.app.state.llm = saved
    assert res.status_code == 200
    assert res.json() == {"answer": OK["choices"][0]["message"]["content"], "provider": "p", "model": "a",
                          "latencyMs": res.json()["latencyMs"]}  # fmt: skip


def test_answer_endpoint_503_when_all_llms_fail(client):
    router, _ = router_with({"a": httpx.Response(429)})
    client.app.state.llm, saved = router, client.app.state.llm
    try:
        res = client.post("/answer", json={"question": "x", "intent": "recolte"})
    finally:
        client.app.state.llm = saved
    assert res.status_code == 503


# ---- Optional live test: RUN_LLM_TESTS=1 python -m pytest tests/test_llm.py -k live -s ----


@pytest.mark.skipif(os.getenv("RUN_LLM_TESTS") != "1" or not build_chain(), reason="live LLM test disabled")
def test_live_answer_in_derja():
    fact = {"source": "M2", "mock": True, "data": {"jours_irrigation": 6, "besoin_total_mm": 17}}
    req = AnswerRequest(question="9adech nesgi zitouni had el jem3a?", intent="irrigation", facts=[fact])
    done = LlmRouter(build_chain()).complete(build_messages(req))
    print(f"\n{done.provider}/{done.model} {done.latency_ms} ms: {done.text}")
    assert "6" in done.text and is_arabic_script(done.text)
