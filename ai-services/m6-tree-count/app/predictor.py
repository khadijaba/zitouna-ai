"""Model loading and inference for M6. This is the file the module owner edits.

Detector used by default: **classical crown detection with OpenCV** (the roadmap baseline), no training needed:

1. vegetation score per pixel: excess green (2G - R - B, on chromatic coordinates) + darkness (olive crowns
   are darker than the bare soil between the rows), smoothed;
2. Otsu threshold -> canopy mask, cleaned with a morphological opening / closing;
3. typical crown radius = median equivalent radius of the isolated blobs;
4. distance transform of the mask + local maxima at least ~1 radius apart -> one tree per maximum, so touching
   crowns are split; blobs much smaller than a crown are ignored.

If a fine-tuned YOLOv8 is exported to models/m6/best.pt and ultralytics is installed, it is used instead.
Without OpenCV (not installed), the service falls back to mock mode (regular grid, mock=True).
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, UnidentifiedImageError

from app.schemas import Box, TreeCountResponse

logger = logging.getLogger(__name__)

MODEL_DIR = Path(os.getenv("MODEL_DIR", "../../models/m6"))
MODEL_FILE = MODEL_DIR / "best.pt"
MAX_SIDE = 1280  # downscale big satellite captures before inference


class InvalidImageError(ValueError):
    pass


@dataclass
class OpenCvDetector:
    """Parameters of the classical detector (tuned on synthetic orchards, see tests)."""

    min_radius_px: float = 4.0  # smaller blobs are noise (single bushes, weeds)
    darkness_weight: float = 0.5
    version: str = "opencv-crowns-1.0"


@dataclass
class YoloDetector:
    model: object
    version: str = "yolov8"


def load() -> OpenCvDetector | YoloDetector | None:
    """YOLO if trained weights exist, else the OpenCV detector; None (mock) only without OpenCV."""
    if MODEL_FILE.exists():
        try:
            from ultralytics import YOLO

            return YoloDetector(YOLO(str(MODEL_FILE)), version=os.getenv("MODEL_VERSION", "yolov8"))
        except Exception:
            logger.exception("Could not load %s: using the OpenCV detector", MODEL_FILE)
    try:
        import cv2  # noqa: F401
    except ImportError:
        logger.warning("OpenCV not installed: mock mode")
        return None
    return OpenCvDetector()


def predict(model: OpenCvDetector | YoloDetector | None, image_bytes: bytes) -> TreeCountResponse:
    image = _open_image(image_bytes)
    if model is None:
        boxes, version = _mock_boxes(image, image_bytes), "mock"
    elif isinstance(model, YoloDetector):
        boxes, version = _yolo_boxes(model, image), model.version
    else:
        boxes, version = detect_crowns(image, model), model.version

    return TreeCountResponse(
        tree_count=len(boxes),
        boxes=boxes,
        annotated_image_base64=_draw(image, boxes),
        model_version=version,
        mock=model is None,
    )


def detect_crowns(image: Image.Image, params: OpenCvDetector) -> list[Box]:
    import cv2
    import numpy as np

    rgb = np.asarray(image, dtype=np.float32) / 255.0
    total = rgb.sum(axis=2) + 1e-6
    r, g, b = (rgb[..., k] / total for k in range(3))
    excess_green = 2 * g - r - b
    darkness = 1.0 - rgb.mean(axis=2)
    score = _normalise(excess_green) + params.darkness_weight * _normalise(darkness)
    score = cv2.GaussianBlur(score, (0, 0), sigmaX=1.5)

    score_u8 = (_normalise(score) * 255).astype(np.uint8)
    if score_u8.std() < 8:  # uniform image (bare soil, sky...): nothing to separate
        return []
    _, mask = cv2.threshold(score_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    if mask.mean() > 255 * 0.85:  # the "canopy" covers almost everything: no contrast between crowns and soil
        return []

    # Typical crown radius from the blobs (median, robust to merged crowns).
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA].astype(np.float32)
    areas = areas[areas >= np.pi * params.min_radius_px**2]
    if len(areas) == 0:
        return []
    radius = float(np.sqrt(np.median(areas) / np.pi))

    # One tree per local maximum of the distance to the soil, at least ~radius apart.
    distance = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    window = max(3, int(radius * 1.4) | 1)
    dilated = cv2.dilate(distance, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (window, window)))
    peaks = (distance == dilated) & (distance >= max(params.min_radius_px * 0.8, radius * 0.45))
    ys, xs = np.nonzero(peaks)

    # Plateaus give several equal maxima for one crown: keep one per label and per radius-sized cell.
    kept: list[tuple[float, float, float]] = []
    for y, x in sorted(zip(ys, xs, strict=True), key=lambda p: -distance[p[0], p[1]]):
        if all((x - kx) ** 2 + (y - ky) ** 2 > (radius * 1.1) ** 2 for kx, ky, _ in kept):
            kept.append((float(x), float(y), float(distance[y, x])))

    h, w = mask.shape
    boxes = []
    for x, y, d in kept:
        half = max(d, radius * 0.8)
        x0, y0 = max(0.0, x - half), max(0.0, y - half)
        x1, y1 = min(float(w), x + half), min(float(h), y + half)
        patch = score[int(y0) : int(y1) + 1, int(x0) : int(x1) + 1]
        confidence = float(np.clip(patch.mean() / (score.max() + 1e-6), 0.05, 0.99))
        boxes.append(
            Box(
                x=round(x0, 1),
                y=round(y0, 1),
                width=round(x1 - x0, 1),
                height=round(y1 - y0, 1),
                confidence=round(confidence, 3),
            )
        )
    return boxes


def _normalise(a):
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo) if hi > lo else a * 0


def _yolo_boxes(model: YoloDetector, image: Image.Image) -> list[Box]:
    result = model.model.predict(image, conf=0.25, verbose=False)[0]
    boxes = []
    for (x1, y1, x2, y2), c in zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist(), strict=True):
        boxes.append(Box(x=x1, y=y1, width=x2 - x1, height=y2 - y1, confidence=round(float(c), 3)))
    return boxes


def _mock_boxes(image: Image.Image, image_bytes: bytes) -> list[Box]:
    w, h = image.size
    spacing = 40 + hashlib.sha256(image_bytes).digest()[0] % 40  # 40-80 px between trees
    crown = spacing * 0.6
    return [
        Box(x=x, y=y, width=crown, height=crown, confidence=0.9)
        for y in range(spacing // 2, int(h - crown), spacing)
        for x in range(spacing // 2, int(w - crown), spacing)
    ]


def _draw(image: Image.Image, boxes: list[Box]) -> str:
    annotated = image.copy()
    pen = ImageDraw.Draw(annotated)
    for b in boxes:
        pen.rectangle([b.x, b.y, b.x + b.width, b.y + b.height], outline=(255, 210, 0), width=2)
    buf = io.BytesIO()
    annotated.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _open_image(image_bytes: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except (UnidentifiedImageError, OSError) as e:
        raise InvalidImageError("The uploaded file is not a readable image") from e
    image = image.convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    return image
