"""Text preprocessing. MUST stay identical to the training notebook: the models were trained on it.

- normalize()   -> input of the TF-IDF pipeline
- light_clean() -> input of SetFit (with the "query: " prefix)
"""

import re
import unicodedata

# Arabic diacritics (U+0617-U+061A, U+064B-U+0652), superscript alef (U+0670), tatweel (U+0640).
AR_DIACRITICS = re.compile(r"[ؗ-ًؚ-ْٰـ]")
URL = re.compile(r"https?://\S+|www\.\S+")
REPEAT = re.compile(r"(.)\1{2,}")


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", str(text)).lower()
    t = URL.sub(" ", t)
    t = AR_DIACRITICS.sub("", t)
    t = re.sub("[إأآٱ]", "ا", t).replace("ة", "ه").replace("ى", "ي")
    t = t.replace("؟", "?").replace("،", ",")
    t = re.sub(r"[^\w\s?']", " ", t)
    t = REPEAT.sub(r"\1\1", t)
    t = re.sub(r"sh", "ch", t)
    return re.sub(r"\s+", " ", t).strip()


def light_clean(text: str) -> str:
    t = unicodedata.normalize("NFKC", str(text))
    t = URL.sub(" ", t)
    t = AR_DIACRITICS.sub("", t)
    t = REPEAT.sub(r"\1\1", t)
    return re.sub(r"\s+", " ", t).strip()


def tokens(normalized: str) -> list[str]:
    """Words of an already normalized text, without punctuation."""
    return re.findall(r"\w+", normalized)
