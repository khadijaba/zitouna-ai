"""Clarification rules applied on top of the ensemble probabilities.

Edit the lists and questions freely: they are data, not model inputs.
"""

from dataclasses import dataclass

from app.preprocessing import normalize, tokens

# Olive / farming vocabulary. Compared on normalize(text), so spelling variants are folded.
DOMAIN_WORDS = [
    "zitoun", "zitouna", "zitouni", "zit", "olive", "olivier", "oliviers", "huile",
    "wra9", "war9a", "warqa", "feuille", "feuilles", "sgi", "nesgi", "sqi", "irrigation",
    "ma3sra", "saba", "jni", "nejni", "récolte", "recolte", "chajra", "sjar", "ghaba",
    "ardh", "hektar", "dwa", "mridha", "maladie", "smed",
    "زيتون", "زيتونة", "زيت", "ورق", "ورقة", "سقي", "نسقي", "معصره", "صابه", "جني", "نجني",
    "شجره", "شجر", "غابه", "ارض", "هكتار", "دوا", "مريضه", "سماد",
]  # fmt: skip

# Arabic clitics glued to the word: "الزيتون", "بالزيت", "وشجره"...
AR_PREFIXES = ("وال", "بال", "فال", "لل", "ال", "و", "ب", "ف", "ل")

GENERIC = "generic"
# Shown to the farmer: Tunisian derja in Arabic script (all chat answers are in Arabic script).
QUESTIONS = {
    GENERIC: "ما فهمتكش مليح. سؤالك على المرض، السقي، الطقس، الصابة، السوم ولا عدد الزيتون؟",
    frozenset({"recolte", "comptage"}): "تحب تعرف قداش من شجرة عندك، ولا قداش باش تجيب من زيتون وزيت؟",
    frozenset({"irrigation", "recolte"}): "سؤالك على الماء (السقي) ولا على الصابة (الجني)؟",
    frozenset({"irrigation", "meteo_alerte"}): "تحب تعرف الطقس، ولا قداش تسقي؟",
    frozenset({"prix_vente", "recolte"}): "تحب تعرف السوم، ولا قداش باش تجيب؟",
    frozenset({"conseil_general", "maladie"}): "فما مرض على الزيتونة؟ ابعثلي تصويرة متاع ورقة. ولا تحب نصيحة عامة؟",
    frozenset({"conseil_general", "irrigation"}): "سؤالك على قداش تسقي، ولا على معدات السقي؟",
    frozenset({"conseil_general", "recolte"}): "تحب تعرف قداش باش تجيب، ولا كيفاش تعمل الجني؟",
}
CONFUSABLE_MARGIN = 0.15

_DOMAIN = {normalize(w) for w in DOMAIN_WORDS}


def mentions_domain(text: str) -> bool:
    """True if a token is, or starts with, a domain word (zitouni -> zitoun, الزيتون -> زيتون)."""
    for tok in tokens(normalize(text)):
        candidates = {tok} | {tok[len(p) :] for p in AR_PREFIXES if tok.startswith(p) and len(tok) > len(p) + 1}
        if any(c.startswith(w) for c in candidates for w in _DOMAIN):
            return True
    return False


@dataclass(frozen=True)
class Decision:
    clarify: bool
    question: str | None
    rule: str | None  # which rule fired, for logs and tests


def decide(
    text: str, top1: str, top2: str, confidence: float, margin: float, models_agree: bool, threshold: float
) -> Decision:
    """The first rule that applies wins."""
    # 1. Never refuse a real farmer's question.
    if top1 == "hors_sujet" and mentions_domain(text):
        return Decision(True, QUESTIONS[GENERIC], "domain_guard")
    # 2. Both models disagree and the ensemble is unsure.
    if not models_agree and confidence < threshold:
        return Decision(True, QUESTIONS[GENERIC], "disagreement")
    # 3. A known confusable pair, too close to call.
    pair = frozenset({top1, top2})
    if pair in QUESTIONS and margin < CONFUSABLE_MARGIN:
        return Decision(True, QUESTIONS[pair], "confusable_pair")
    return Decision(False, None, None)
