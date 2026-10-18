"""API behaviour. Runs with the trained ensemble if present, otherwise with the keyword fallback."""

import pytest

INTENTS = {
    "maladie", "irrigation", "meteo_alerte", "recolte", "prix_vente",
    "comptage", "conseil_general", "salutation", "hors_sujet",
}  # fmt: skip


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert isinstance(body["modelLoaded"], bool)


def test_output_schema(client):
    res = client.post("/intent", json={"text": "9adech nesgi zitouni had el jem3a?"})
    assert res.status_code == 200
    body = res.json()
    assert body.keys() == {
        "intent", "confidence", "clarify", "question", "candidates",
        "modelsAgree", "entities", "modelVersion", "mock",
    }  # fmt: skip
    assert body["intent"] in INTENTS
    assert 0 <= body["confidence"] <= 1
    assert len(body["candidates"]) == 3
    assert body["candidates"][0]["intent"] == body["intent"]
    assert [c["score"] for c in body["candidates"]] == sorted((c["score"] for c in body["candidates"]), reverse=True)
    assert body["entities"].keys() == {"gouvernorat"}
    assert (body["question"] is not None) == body["clarify"]


@pytest.mark.parametrize("text", ["", "   ", "x" * 501])
def test_rejects_empty_or_too_long_text(client, text):
    assert client.post("/intent", json={"text": text}).status_code == 422


def test_governorate_entity(client):
    body = client.post("/intent", json={"text": "fama jlid ghodwa fi beja?"}).json()
    assert body["entities"]["gouvernorat"] == "beja"
