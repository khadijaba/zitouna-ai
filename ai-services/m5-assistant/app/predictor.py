"""Intent classification for M5: TF-IDF + SetFit ensemble, clarification rules, governorate entity.

If the trained ensemble is not in MODEL_DIR (CI, teammates without the 1 GB model), the service
falls back to a keyword matcher and answers with mock=True.
"""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app import rules
from app.entities import find_governorate
from app.preprocessing import light_clean, normalize, tokens
from app.schemas import Candidate, Entities, IntentResponse

log = logging.getLogger("m5")

# Relative to the service folder when run locally; Docker sets MODEL_DIR=/models/m5_ensemble.
MODEL_DIR = Path(os.getenv("MODEL_DIR", "../../models/m5_ensemble"))
MODEL_VERSION = os.getenv("MODEL_VERSION", "m5_ensemble")


@dataclass
class Ensemble:
    tfidf: Any  # sklearn Pipeline, trained on normalize(text)
    setfit: Any  # SetFitModel, trained on prefix + light_clean(text); None for a TF-IDF-only model
    labels: list[str]
    tfidf_order: list[int]  # column i of the ensemble = column tfidf_order[i] of tfidf.predict_proba
    prefix: str
    weight_setfit: float
    clarify_threshold: float

    @classmethod
    def build(cls, tfidf: Any, setfit: Any, config: dict) -> "Ensemble":
        labels = list(config["labels"])
        classes = [str(c) for c in tfidf.classes_]
        if sorted(classes) != sorted(labels):
            raise ValueError(f"TF-IDF classes {classes} do not match config labels {labels}")
        return cls(
            tfidf=tfidf,
            setfit=setfit,
            labels=labels,
            tfidf_order=[classes.index(label) for label in labels],
            prefix=config.get("setfit_prefix", "query: "),
            weight_setfit=float(config["weight_setfit"]),
            clarify_threshold=float(config["clarify_threshold"]),
        )

    def p_tfidf(self, text: str) -> np.ndarray:
        return np.asarray(self.tfidf.predict_proba([normalize(text)])[0])[self.tfidf_order]

    def p_setfit(self, text: str) -> np.ndarray:
        return np.asarray(
            self.setfit.predict_proba([self.prefix + light_clean(text)], as_numpy=True, show_progress_bar=False)[0]
        )


def load(model_dir: Path = MODEL_DIR) -> Ensemble | None:
    """Load both models once. Returns None (keyword fallback) if the model folder is missing."""
    config_file = model_dir / "config.json"
    if not config_file.exists():
        log.warning("No model in %s: running in keyword fallback mode (mock=true)", model_dir.resolve())
        return None

    import joblib  # heavy imports only when the model is really there
    import sklearn

    config = json.loads(config_file.read_text(encoding="utf-8"))
    if config.get("sklearn_version") and config["sklearn_version"] != sklearn.__version__:
        log.warning("Model trained with scikit-learn %s, running %s", config["sklearn_version"], sklearn.__version__)

    setfit = None
    if float(config["weight_setfit"]) > 0:  # weight 0: TF-IDF-only model (notebooks/m5_assistant/train_m5.ipynb)
        from setfit import SetFitModel

        setfit = SetFitModel.from_pretrained(str(model_dir / "setfit"))
    ensemble = Ensemble.build(tfidf=joblib.load(model_dir / "tfidf.joblib"), setfit=setfit, config=config)
    setfit_labels = getattr(ensemble.setfit, "labels", None)
    if setfit_labels and list(setfit_labels) != ensemble.labels:
        raise ValueError(f"SetFit labels {setfit_labels} differ from config labels {ensemble.labels}")
    return ensemble


def predict(ensemble: Ensemble | None, text: str) -> IntentResponse:
    if ensemble is None:
        return _keyword_fallback(text)

    p_tfidf = ensemble.p_tfidf(text)
    if ensemble.setfit is None:
        # No second model to disagree with: a low confidence counts as a disagreement (clarification rule 2).
        p, models_agree = p_tfidf, float(p_tfidf.max()) >= ensemble.clarify_threshold
    else:
        p_setfit = ensemble.p_setfit(text)
        p = ensemble.weight_setfit * p_setfit + (1 - ensemble.weight_setfit) * p_tfidf
        models_agree = int(np.argmax(p_tfidf)) == int(np.argmax(p_setfit))
    return _respond(
        text,
        labels=ensemble.labels,
        p=p,
        models_agree=models_agree,
        threshold=ensemble.clarify_threshold,
        model_version=MODEL_VERSION,
        mock=False,
    )


def _respond(
    text: str, labels: list[str], p: np.ndarray, models_agree: bool, threshold: float, model_version: str, mock: bool
) -> IntentResponse:
    order = np.argsort(p)[::-1]
    top1, top2 = labels[order[0]], labels[order[1]]
    confidence = float(p[order[0]])
    margin = confidence - float(p[order[1]])
    decision = rules.decide(text, top1, top2, confidence, margin, models_agree, threshold)
    if decision.clarify:
        log.debug("clarify rule=%s top1=%s top2=%s margin=%.3f", decision.rule, top1, top2, margin)
    return IntentResponse(
        intent=top1,
        confidence=round(confidence, 4),
        clarify=decision.clarify,
        question=decision.question,
        candidates=[Candidate(intent=labels[i], score=round(float(p[i]), 4)) for i in order[:3]],
        models_agree=models_agree,
        entities=Entities(gouvernorat=find_governorate(text)),
        model_version=model_version,
        mock=mock,
    )


# ---- Keyword fallback (no trained model): also a simple baseline -------------------------------

FALLBACK_LABELS = [
    "maladie", "irrigation", "meteo_alerte", "recolte", "prix_vente",
    "comptage", "conseil_general", "salutation", "hors_sujet",
]  # fmt: skip
FALLBACK_KEYWORDS = {
    "salutation": ["aslema", "salam", "ahla", "bonjour", "bonsoir", "marhba", "عسلامه", "السلام", "اهلا"],
    "maladie": ["mardh", "mridh", "maladie", "dwa", "fongicide", "tsfar", "sfor", "مرض", "دوا"],
    "irrigation": ["sgi", "nesgi", "tesgi", "irrig", "lma", "eau", "سقي", "نسقي", "ماء"],
    "meteo_alerte": ["ta9s", "meteo", "météo", "chta", "pluie", "jlid", "skhana", "gel", "طقس", "شتاء", "مطر"],
    "recolte": ["saba", "jni", "nejni", "récolte", "recolte", "rendement", "صابه", "جني"],
    "prix_vente": ["soum", "s3ar", "prix", "nbi3", "vendre", "يشريو", "سوم", "نبيع"],
    "comptage": ["3add", "3adad", "compter", "drone", "taswira", "عدد"],
}


def _keyword_fallback(text: str) -> IntentResponse:
    words = tokens(normalize(text))
    scores = np.array(
        [
            sum(any(w.startswith(k) for w in words) for k in FALLBACK_KEYWORDS.get(label, []))
            for label in FALLBACK_LABELS
        ],
        dtype=float,
    )
    if scores.sum() == 0:
        default = "conseil_general" if rules.mentions_domain(text) else "hors_sujet"
        scores[FALLBACK_LABELS.index(default)] = 1.0
    p = (scores + 0.05) / (scores + 0.05).sum()  # smoothed pseudo-probabilities
    return _respond(text, FALLBACK_LABELS, p, models_agree=True, threshold=0.0, model_version="mock", mock=True)
