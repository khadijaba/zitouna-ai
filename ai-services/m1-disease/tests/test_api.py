import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (40, 120, 40)).save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_predict_returns_contract_fields():
    res = client.post("/predict", files={"image": ("leaf.png", _png(), "image/png")})
    assert res.status_code == 200
    body = res.json()
    assert body["label"] in {"healthy", "peacock_spot", "aculus_olearius", "olive_knot"}
    assert {"labelFr", "confidence", "probabilities", "advice", "modelVersion", "mock"} <= body.keys()
    assert abs(sum(body["probabilities"].values()) - 1) < 1e-3


def test_rejects_non_image():
    res = client.post("/predict", files={"image": ("notes.txt", b"hello", "text/plain")})
    assert res.status_code == 422


# --- Vrai modèle (TorchScript) --------------------------------------------------
# Un faux modèle léger — moyenne par canal puis logits — suffit à tester toute la
# chaîne : chargement, calibration, seuil 0.70, conseils. Sans torch : tests sautés.


def _fake_model_dir(tmp_path: Path, temperature: float) -> Path:
    torch = pytest.importorskip("torch")
    module = torch.nn.Sequential(torch.nn.AdaptiveAvgPool2d(1), torch.nn.Flatten())
    scripted = torch.jit.trace(module.eval(), torch.rand(1, 3, 224, 224))
    torch.jit.save(scripted, str(tmp_path / "model.pt"))
    (tmp_path / "classes.json").write_text(json.dumps(["healthy", "peacock_spot", "aculus_olearius"]), encoding="utf-8")
    (tmp_path / "calibration.json").write_text(json.dumps({"temperature": temperature}), encoding="utf-8")
    return tmp_path


def test_treatments_covers_classes():
    data = json.loads((Path(__file__).resolve().parents[1] / "app" / "treatments.json").read_text(encoding="utf-8"))
    assert "low_confidence" in data
    for class_name in ["healthy", "peacock_spot", "aculus_olearius", "olive_knot"]:
        entry = data["classes"][class_name]
        assert entry["advice"] and entry["warning"]
        assert "INRAT" in entry["source"] or "ONH" in entry["source"]


def test_real_model_high_confidence(tmp_path, monkeypatch):
    from app import predictor

    model_dir = _fake_model_dir(tmp_path, temperature=0.01)  # T<<1 -> probas quasi one-hot
    monkeypatch.setattr(predictor, "MODEL_DIR", model_dir)
    monkeypatch.setattr(predictor, "MODEL_FILE", model_dir / "model.pt")
    loaded = predictor.load()
    assert loaded is not None and len(loaded.classes) == 3

    response = predictor.predict(loaded, _png())
    assert response.mock is False
    assert response.label in loaded.classes
    assert response.confidence >= predictor.LOW_CONFIDENCE_THRESHOLD
    assert response.low_confidence is False
    assert "reprenez" not in response.advice
    assert abs(sum(response.probabilities.values()) - 1) < 1e-3
    assert response.heatmap_base64 is None  # pas de model_full.pt -> pas de Grad-CAM


def test_real_model_low_confidence_gives_retake_advice(tmp_path, monkeypatch):
    from app import predictor

    model_dir = _fake_model_dir(tmp_path, temperature=1000.0)  # T>>1 -> probas quasi uniformes
    monkeypatch.setattr(predictor, "MODEL_DIR", model_dir)
    monkeypatch.setattr(predictor, "MODEL_FILE", model_dir / "model.pt")
    loaded = predictor.load()

    response = predictor.predict(loaded, _png())
    assert response.confidence < predictor.LOW_CONFIDENCE_THRESHOLD
    assert response.low_confidence is True
    assert "reprenez" in response.advice.lower()  # message « photo peu claire » dans advice
    assert response.heatmap_base64 is None


def test_real_model_through_http_endpoint(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    from app import main, predictor

    model_dir = _fake_model_dir(tmp_path, temperature=0.01)
    monkeypatch.setattr(predictor, "MODEL_DIR", model_dir)
    monkeypatch.setattr(predictor, "MODEL_FILE", model_dir / "model.pt")
    monkeypatch.setattr(main, "model", predictor.load())

    res = client.post("/predict", files={"image": ("leaf.png", _png(), "image/png")})
    assert res.status_code == 200
    body = res.json()
    assert body["mock"] is False
    assert body["lowConfidence"] is False
    assert len(body["probabilities"]) == 3
    assert client.get("/health").json()["modelLoaded"] is True
