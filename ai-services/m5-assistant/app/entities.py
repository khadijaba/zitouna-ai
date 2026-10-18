"""Simple entity extraction: which governorate does the farmer talk about? (used by M2 for the weather)."""

import re

from app.preprocessing import normalize

# canonical id -> spellings (Latin, arabizi, Arabic). Add variants freely, they are normalized below.
GOVERNORATES = {
    "ariana": ["ariana", "aryana", "أريانة"],
    "beja": ["beja", "béja", "bja", "باجة"],
    "ben arous": ["ben arous", "benarous", "bin 3rous", "بن عروس"],
    "bizerte": ["bizerte", "bizerta", "benzart", "bnzart", "بنزرت"],
    "gabes": ["gabes", "gabès", "9abes", "qabes", "قابس"],
    "gafsa": ["gafsa", "9afsa", "قفصة"],
    "jendouba": ["jendouba", "jandouba", "جندوبة"],
    "kairouan": ["kairouan", "kairawan", "9irwan", "9ayrawen", "qayrawan", "القيروان", "قيروان"],
    "kasserine": ["kasserine", "kasrine", "9asrine", "القصرين", "قصرين"],
    "kebili": ["kebili", "kébili", "9bili", "قبلي"],
    "kef": ["le kef", "el kef", "kef", "الكاف"],
    "mahdia": ["mahdia", "mahdiya", "المهدية", "مهدية"],
    "manouba": ["manouba", "mannouba", "منوبة"],
    "medenine": ["medenine", "médenine", "mednine", "مدنين"],
    "monastir": ["monastir", "mestir", "المنستير", "منستير"],
    "nabeul": ["nabeul", "nabel", "نابل"],
    "sfax": ["sfax", "sfa9es", "sfaks", "صفاقس"],
    "sidi bouzid": ["sidi bouzid", "sidi bou zid", "sidibouzid", "سيدي بوزيد"],
    "siliana": ["siliana", "سليانة"],
    "sousse": ["sousse", "soussa", "sousa", "سوسة"],
    "tataouine": ["tataouine", "tatawin", "تطاوين"],
    "tozeur": ["tozeur", "touzer", "توزر"],
    # "tounes" / "تونس" also means the whole country, so only unambiguous names here.
    "tunis": ["tunis", "el 3asma", "العاصمة"],
    "zaghouan": ["zaghouan", "zaghwen", "زغوان"],
}

_AR_PREFIX = "(?:و|ب|ل|ف)?"
_PATTERNS = [
    (gov, re.compile(rf"(?<!\w){_AR_PREFIX}{re.escape(normalize(v))}(?!\w)"))
    for gov, variants in GOVERNORATES.items()
    for v in sorted(variants, key=len, reverse=True)
]


def find_governorate(text: str) -> str | None:
    """Canonical id of the first governorate mentioned (by position in the text), or None."""
    norm = normalize(text)
    hits = [(m.start(), gov) for gov, pattern in _PATTERNS if (m := pattern.search(norm))]
    return min(hits)[1] if hits else None
