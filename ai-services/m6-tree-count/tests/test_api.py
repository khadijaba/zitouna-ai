import io
import math
import random

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFilter

from app import main, predictor
from app.main import app

client = TestClient(app)
cv2 = pytest.importorskip("cv2")  # the real detector needs OpenCV (installed in the Docker image)


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def synthetic_orchard(rows: int, cols: int, spacing: int = 42, seed: int = 0, touching: int = 0) -> tuple[bytes, int]:
    """Aerial-like view: beige soil with texture, olive crowns (grey-green discs of varying size) in rows.

    `touching` extra trees are planted right next to existing ones (crowns in contact), like real groves.
    Returns (png bytes, true number of trees).
    """
    rng = random.Random(seed)
    w, h = cols * spacing + spacing, rows * spacing + spacing
    img = Image.new("RGB", (w, h), (196, 178, 140))
    px = img.load()
    for _ in range(w * h // 6):  # soil texture
        x, y = rng.randrange(w), rng.randrange(h)
        d = rng.randint(-18, 18)
        r, g, b = px[x, y]
        px[x, y] = (r + d, g + d, b + d)
    pen = ImageDraw.Draw(img)
    centres = []
    for i in range(rows):
        for j in range(cols):
            centres.append((spacing * (j + 1) + rng.randint(-4, 4), spacing * (i + 1) + rng.randint(-4, 4)))
    for k in range(touching):
        cx, cy = centres[k * 3 % len(centres)]
        centres.append((cx + 19, cy + 3))
    for cx, cy in centres:
        radius = rng.randint(9, 13)
        shade = rng.randint(-12, 12)
        pen.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(78 + shade, 96 + shade, 62 + shade))
    return _png(img.filter(ImageFilter.GaussianBlur(0.8))), len(centres)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_detector_is_real_not_mock():
    model = predictor.load()
    assert isinstance(model, predictor.OpenCvDetector)
    res = predictor.predict(model, synthetic_orchard(3, 4)[0])
    assert res.mock is False and res.model_version.startswith("opencv")


@pytest.mark.parametrize(("rows", "cols", "seed"), [(4, 6, 1), (6, 8, 2), (8, 10, 3)])
def test_counts_separate_trees_within_5_percent(rows, cols, seed):
    png, truth = synthetic_orchard(rows, cols, seed=seed)
    res = predictor.predict(predictor.load(), png)
    assert abs(res.tree_count - truth) <= max(1, math.ceil(truth * 0.05)), (res.tree_count, truth)
    assert res.tree_count == len(res.boxes)


def test_touching_crowns_are_split():
    png, truth = synthetic_orchard(5, 6, seed=4, touching=6)
    res = predictor.predict(predictor.load(), png)
    assert abs(res.tree_count - truth) <= math.ceil(truth * 0.1), (res.tree_count, truth)


def test_bare_soil_has_no_tree():
    img = Image.new("RGB", (400, 300), (196, 178, 140))
    assert predictor.predict(predictor.load(), _png(img)).tree_count == 0


def test_http_endpoint_returns_boxes_and_annotated_image(monkeypatch):
    monkeypatch.setattr(main, "model", predictor.load())
    png, truth = synthetic_orchard(4, 5, seed=5)
    res = client.post("/predict", files={"image": ("parcel.png", png, "image/png")})
    assert res.status_code == 200
    body = res.json()
    assert body["mock"] is False and body["treeCount"] == len(body["boxes"])
    assert abs(body["treeCount"] - truth) <= 1
    assert body["annotatedImageBase64"]
    box = body["boxes"][0]
    assert 0 < box["confidence"] <= 1 and box["width"] > 0


def test_rejects_non_image():
    res = client.post("/predict", files={"image": ("x.txt", b"nope", "text/plain")})
    assert res.status_code == 422
