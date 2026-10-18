"""POST /explain: an LLM explains a module's result; template sentence when no LLM answers. No network needed."""

import json

import httpx
import pytest
from tests.test_llm import ARABIZI, OK, router_with

from app.explain import MODULE_BACKUP, MODULE_LLM, build_messages, compact, template
from app.schemas import ExplainRequest

FR = {"choices": [{"message": {"content": "Arrosez 511 litres par arbre aujourd'hui."}, "finish_reason": "stop"}]}

RESULTS = {
    "M1": {
        "label": "peacock_spot",
        "labelFr": "Œil de paon",
        "confidence": 0.9996,
        "heatmapBase64": "AAAA" * 500,
        "probabilities": {"healthy": 0.0002},
        "mock": False,
    },
    "M2": {
        "days": [{"date": "2026-10-18", "et0Mm": 3.62, "waterNeedMm": 2.2, "litersPerTree": 510.5, "irrigate": True}],
        "alerts": [],
        "mock": False,
    },
    "M3": {"parcelEstimateKg": 997.4, "lowKg": 473, "highKg": 1891, "scope": "national", "mock": False},
    "M4": {"currentPrice": 18.54, "recommendation": "SELL_NOW", "mock": False},
    "M5": {"intent": "irrigation", "confidence": 0.81, "clarify": False},
    "M6": {"treeCount": 86, "boxes": [{"x": 1, "y": 2}] * 86, "annotatedImageBase64": "BBBB" * 500, "mock": False},
}


def with_router(client, router):
    client.app.state.explain_llm, saved = router, client.app.state.explain_llm
    return saved


def test_compact_drops_images_and_coordinates_and_shortens_lists():
    out = compact({"annotatedImageBase64": "x", "boxes": [1, 2], "days": list(range(20)), "et0": 3.6249, "ok": None})
    assert out == {"days": list(range(7)), "et0": 3.625}


def test_messages_describe_the_module_and_keep_only_the_figures():
    messages = build_messages(ExplainRequest(module="M6", result=RESULTS["M6"]))
    system, user = messages[0]["content"], messages[1]["content"]
    assert "N'en invente jamais" in system and "français simple" in system
    assert "OpenCV" in user and '"treeCount": 86' in user
    assert "Base64" not in user and "boxes" not in user


def test_explain_endpoint_uses_the_llm(client):
    sent = []
    router, _ = router_with({"a": httpx.Response(200, json=FR)})
    original = router.client._transport.handle_request

    def spy(request):
        sent.append(json.loads(request.content))
        return original(request)

    router.client._transport.handle_request = spy
    saved = with_router(client, router)
    try:
        res = client.post("/explain", json={"module": "M2", "result": RESULTS["M2"]})
    finally:
        client.app.state.explain_llm = saved
    assert res.status_code == 200
    body = res.json()
    assert (body["explanation"], body["model"], body["fallback"]) == (
        FR["choices"][0]["message"]["content"],
        "a",
        False,
    )
    assert "litersPerTree" in sent[0]["messages"][1]["content"]


@pytest.mark.parametrize("module", ["M1", "M2", "M3", "M4", "M5", "M6"])
def test_template_explanation_when_every_llm_fails(client, module):
    router, _ = router_with({"a": httpx.Response(503)})
    saved = with_router(client, router)
    try:
        res = client.post("/explain", json={"module": module, "result": RESULTS[module]})
    finally:
        client.app.state.explain_llm = saved
    body = res.json()
    assert res.status_code == 200 and body["fallback"] is True and body["provider"] == "template"
    assert len(body["explanation"]) > 30


def test_template_uses_the_real_figures():
    assert "86 oliviers" in template(ExplainRequest(module="M6", result=RESULTS["M6"]))
    assert "100 %" in template(ExplainRequest(module="M1", result=RESULTS["M1"]))
    assert "997 kg" in template(ExplainRequest(module="M3", result=RESULTS["M3"]))


def test_derja_rejects_an_answer_not_in_arabic_script(client):
    router, calls = router_with({"a": httpx.Response(200, json=ARABIZI), "b": httpx.Response(200, json=OK)})
    saved = with_router(client, router)
    try:
        res = client.post("/explain", json={"module": "M2", "result": RESULTS["M2"], "language": "derja"})
    finally:
        client.app.state.explain_llm = saved
    assert res.json()["model"] == "b" and calls == ["a", "b"]


def test_unknown_module_is_rejected(client):
    assert client.post("/explain", json={"module": "M9", "result": {}}).status_code == 422


CHAIN = [
    "gemini-3.5-flash",
    "qwen/qwen3.8-27b",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.7-flash",
    "glm-4.5-flash",
]


@pytest.mark.parametrize("module", ["M1", "M2", "M3", "M4", "M5", "M6"])
def test_each_module_first_asks_its_dedicated_llm(client, module):
    router, calls = router_with({name: httpx.Response(200, json=FR) for name in CHAIN})
    saved = with_router(client, router)
    try:
        res = client.post("/explain", json={"module": module, "result": RESULTS[module]})
    finally:
        client.app.state.explain_llm = saved
    assert calls == [MODULE_LLM[module]] and res.json()["model"] == MODULE_LLM[module]


def test_the_chain_takes_over_when_the_dedicated_llm_fails(client):
    responses = {name: httpx.Response(200, json=FR) for name in CHAIN}
    responses["qwen/qwen3.8-27b"] = httpx.Response(429)
    router, calls = router_with(responses)
    saved = with_router(client, router)
    try:
        res = client.post("/explain", json={"module": "M6", "result": RESULTS["M6"]})
    finally:
        client.app.state.explain_llm = saved
    assert calls == ["qwen/qwen3.8-27b", "gemini-3.5-flash"] and res.json()["fallback"] is False


def test_every_dedicated_llm_is_in_the_default_chain():
    from app.llm import DEFAULT_CHAIN

    chain = {entry["model"] for entry in DEFAULT_CHAIN}
    assert set(MODULE_LLM.values()) <= chain and set(MODULE_BACKUP.values()) <= chain


def test_each_module_has_a_different_llm():
    assert len(set(MODULE_LLM.values())) == len(MODULE_LLM) == 6


def test_m4_falls_back_to_glm_from_another_provider(client):
    responses = {name: httpx.Response(200, json=FR) for name in CHAIN}
    responses["gemini-3.5-flash-lite"] = httpx.Response(429)
    router, calls = router_with(responses)
    saved = with_router(client, router)
    try:
        res = client.post("/explain", json={"module": "M4", "result": RESULTS["M4"]})
    finally:
        client.app.state.explain_llm = saved
    assert calls == ["gemini-3.5-flash-lite", "glm-4.5-flash"] and res.json()["model"] == "glm-4.5-flash"


def test_m4_goes_to_the_chain_when_glm_has_no_key(client):
    responses = {name: httpx.Response(200, json=FR) for name in CHAIN if name != "glm-4.5-flash"}
    responses["gemini-3.5-flash-lite"] = httpx.Response(503)
    router, calls = router_with(responses)
    saved = with_router(client, router)
    try:
        res = client.post("/explain", json={"module": "M4", "result": RESULTS["M4"]})
    finally:
        client.app.state.explain_llm = saved
    assert calls == ["gemini-3.5-flash-lite", "gemini-3.5-flash"] and res.json()["model"] == "gemini-3.5-flash"
