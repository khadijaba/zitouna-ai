"""Unit tests of preprocessing, rules, entities and the ensemble maths, with fake models (no torch needed)."""

import numpy as np
import pytest

from app import predictor, rules
from app.entities import find_governorate
from app.preprocessing import light_clean, normalize

LABELS = [
    "comptage", "conseil_general", "hors_sujet", "irrigation", "maladie",
    "meteo_alerte", "prix_vente", "recolte", "salutation",
]  # fmt: skip
CONFIG = {"labels": LABELS, "setfit_prefix": "query: ", "weight_setfit": 0.4, "clarify_threshold": 0.4}


def one_hot(label: str, value: float = 1.0, labels=LABELS) -> np.ndarray:
    p = np.full(len(labels), (1 - value) / (len(labels) - 1))
    p[labels.index(label)] = value
    return p


class FakeTfidf:
    """classes_ deliberately in a different order than the config labels."""

    classes_ = np.array(list(reversed(LABELS)))

    def __init__(self, p_in_label_order: np.ndarray):
        self.p = p_in_label_order[::-1]
        self.seen = None

    def predict_proba(self, texts):
        self.seen = texts
        return np.array([self.p])


class FakeSetFit:
    def __init__(self, p: np.ndarray):
        self.p = p
        self.seen = None

    def predict_proba(self, texts, as_numpy=False, **kwargs):
        self.seen = texts
        return np.array([self.p])


def ensemble(p_tfidf: np.ndarray, p_setfit: np.ndarray) -> predictor.Ensemble:
    return predictor.Ensemble.build(FakeTfidf(p_tfidf), FakeSetFit(p_setfit), CONFIG)


# ---- preprocessing ----


def test_normalize_matches_training_rules():
    assert normalize("Shnowa   ZITOUUUNI؟ https://x.tn") == "chnowa zitouuni?"
    assert normalize("الزَّيتونة") == "الزيتونه"
    assert normalize("أرض") == "ارض"


def test_light_clean_keeps_case_and_letters():
    assert light_clean("Zitouniiii  مريضة ") == "Zitounii مريضة"


# ---- ensemble maths ----


def test_tfidf_columns_are_reordered_and_models_get_their_own_preprocessing():
    ens = ensemble(one_hot("irrigation", 0.9), one_hot("irrigation", 0.8))
    res = predictor.predict(ens, "9adech NESGI?")
    assert res.intent == "irrigation"
    assert res.confidence == pytest.approx(0.4 * 0.8 + 0.6 * 0.9)
    assert ens.tfidf.seen == ["9adech nesgi?"]
    assert ens.setfit.seen == ["query: 9adech NESGI?"]
    assert res.models_agree and not res.clarify and not res.mock


# ---- clarification rules ----


def test_domain_guard_beats_off_topic():
    res = predictor.predict(ensemble(one_hot("hors_sujet", 0.9), one_hot("hors_sujet", 0.9)), "zitouni mouch labes")
    assert res.intent == "hors_sujet"
    assert res.clarify and res.question == rules.QUESTIONS[rules.GENERIC]


def test_real_off_topic_is_not_clarified():
    res = predictor.predict(ensemble(one_hot("hors_sujet", 0.9), one_hot("hors_sujet", 0.9)), "wa9tech yebda el bac?")
    assert not res.clarify


def test_disagreement_with_low_confidence_asks_generic_question():
    res = predictor.predict(ensemble(one_hot("maladie", 0.45), one_hot("prix_vente", 0.45)), "chnowa?")
    assert not res.models_agree
    assert res.confidence < 0.4
    assert res.clarify and res.question == rules.QUESTIONS[rules.GENERIC]


def test_confusable_pair_asks_targeted_question():
    p = np.zeros(len(LABELS))
    p[LABELS.index("recolte")], p[LABELS.index("comptage")], p[LABELS.index("salutation")] = 0.5, 0.42, 0.08
    res = predictor.predict(ensemble(p, p), "9adech 3andi?")
    assert res.clarify
    assert res.question == rules.QUESTIONS[frozenset({"recolte", "comptage"})]
    assert [c.intent for c in res.candidates[:2]] == ["recolte", "comptage"]


def test_confident_answer_is_not_clarified():
    p = np.zeros(len(LABELS))
    p[LABELS.index("recolte")], p[LABELS.index("comptage")] = 0.7, 0.3
    assert not predictor.predict(ensemble(p, p), "9adech bech njib zit?").clarify


@pytest.mark.parametrize(
    "text", ["zitouni mouch labes", "الزيتون مريض", "el war9a sfra", "chnowa na3mel fil ardh?", "bel زيت"]
)
def test_mentions_domain(text):
    assert rules.mentions_domain(text)


@pytest.mark.parametrize("text", ["wa9tech yebda el bac?", "el internet ma ykhdemch", "شنية الأخبار؟"])
def test_does_not_mention_domain(text):
    assert not rules.mentions_domain(text)


# ---- entities ----


@pytest.mark.parametrize(
    ("text", "gov"),
    [
        ("fama jlid ghodwa fi beja?", "beja"),
        ("قداش يشريو اليوم بالكيلو في صفاقس؟", "sfax"),
        ("el ta9s fi SIDI BOUZID", "sidi bouzid"),
        ("زيتون القيروان", "kairouan"),
        ("ena men sousse w nekhdem fi sfax", "sousse"),
        ("bsousa", None),
        ("9adech nesgi zitouni?", None),
    ],
)
def test_find_governorate(text, gov):
    assert find_governorate(text) == gov


# ---- keyword fallback ----


def test_fallback_is_flagged_as_mock():
    res = predictor.predict(None, "aslema")
    assert res.intent == "salutation" and res.mock and res.model_version == "mock"
