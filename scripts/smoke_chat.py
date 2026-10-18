"""End-to-end smoke test of the chat: app/backend -> M5 (intent) -> M2/M3/M4/stubs.

Usage (stack running with `docker compose up`):
    python scripts/smoke_chat.py                              # backend on http://localhost:8080
    python scripts/smoke_chat.py http://localhost:4200        # through the Angular nginx proxy
    python scripts/smoke_chat.py http://localhost:8090        # if BACKEND_PORT=8090 in .env

Standard library only. Sends UTF-8 bodies, so Arabic works on Windows too (unlike curl arguments).
"""

import json
import re
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")
EMAIL, PASSWORD = "smoke@zitouna.tn", "zitouna-smoke-123"

# (text, expected intent, expected clarify, uses the parcel, forcedIntent, text expected in the reply)
CASES = [
    ("aslema", "salutation", False, False, None, "عسلامة"),
    ("شنية الأخبار؟", "salutation", False, False, None, None),
    ("fama jlid ghodwa fi beja?", "meteo_alerte", False, False, None, "باجة"),
    ("9adech nesgi zitouni had el jem3a?", "irrigation", False, True, None, "Henchir Smoke"),
    ("nbi3 el zit taw walla nestanna?", "prix_vente", False, False, None, "دينار"),
    ("قداش يشريو اليوم بالكيلو في صفاقس؟", "prix_vente", False, False, None, None),
    ("9adech bech njib zit had el 3am?", "recolte", False, True, None, "كغ"),
    ("a3tini 3adad el sjar elli fil taswira mel drone", "comptage", False, False, None, "تصويرة"),
    ("c'est quoi le problème mta3 el wra9 el sfor?", "maladie", False, False, None, "Diagnostic"),
    ("كيفاش نداوي الذبانة بطريقة طبيعية؟", "maladie", False, False, None, None),
    ("c'est quoi la différence bin zit vierge w extra vierge?", "conseil_general", False, False, None, None),
    ("wa9tech yebda el bac?", "hors_sujet", False, False, None, "سامحني"),
    ("zitouni mouch labes", None, True, False, None, "ما فهمتكش"),  # domain guard
    ("9adech 3andi?", "comptage", False, True, "comptage", None),  # suggestion button clicked
]


def arabic_share(text: str) -> float:
    """Replies are always in Arabic script; Latin is tolerated for names ("Henchir Smoke", « Diagnostic »)."""
    arabic, latin = len(re.findall(r"[ء-ي]", text)), len(re.findall(r"[A-Za-zÀ-ÿ]", text))
    return arabic / max(arabic + latin, 1)


def call(method: str, path: str, body=None, token=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status, json.loads(res.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    status, body = call("POST", "/api/auth/register", {"fullName": "Smoke Test", "email": EMAIL, "password": PASSWORD})
    if status == 409:
        status, body = call("POST", "/api/auth/login", {"email": EMAIL, "password": PASSWORD})
    if status not in (200, 201):
        print(f"Cannot log in on {BASE}: {status} {body}")
        return 1
    token = body["token"]

    _, parcels = call("GET", "/api/parcels", token=token)
    parcel = next((p for p in parcels if p["name"] == "Henchir Smoke"), None)
    if parcel is None:
        _, parcel = call("POST", "/api/parcels", {
            "name": "Henchir Smoke", "governorate": "Sfax", "latitude": 34.74, "longitude": 10.76,
            "areaHa": 2.5, "treeCount": 250, "irrigated": False,
        }, token=token)  # fmt: skip

    failures = 0
    print(f"Chat smoke test on {BASE}\n")
    for text, intent, clarify, with_parcel, forced, expected_text in CASES:
        request = {"text": text, "parcelId": parcel["id"] if with_parcel else None, "forcedIntent": forced}
        started = time.perf_counter()
        status, res = call("POST", "/api/ai/chat", request, token=token)
        ms = (time.perf_counter() - started) * 1000
        if status != 200:
            failures += 1
            print(f"FAIL  {text!r}: HTTP {status} {res}")
            continue
        problems = []
        if intent and res["intent"] != intent:
            problems.append(f"intent {res['intent']} != {intent}")
        if res["clarify"] != clarify:
            problems.append(f"clarify {res['clarify']} != {clarify}")
        llm = res.get("generatedBy", "template") != "template"
        # LLM replies are free text: the expected words are only checked on template replies.
        if expected_text and not llm and expected_text.lower() not in res["reply"].lower():
            problems.append(f"reply does not contain {expected_text!r}")
        if arabic_share(res["reply"]) < 0.6:
            problems.append(f"reply not in Arabic script ({arabic_share(res['reply']):.0%} Arabic letters)")
        if not res["reply"].strip():
            problems.append("empty reply")
        failures += bool(problems)
        flags = ("clarify " + ",".join(res["suggestions"]) if res["clarify"] else "") + (" [mock]" if res["mock"] else "")
        by = res.get("generatedBy", "template").split("/")[-1]
        print(f"{'FAIL' if problems else 'ok  '}  {ms:5.0f} ms  {res['intent']:<15} [{by}] {text}")
        print(f"      -> {res['reply'][:300]}{' ' + flags if flags else ''}")
        for p in problems:
            print(f"      !! {p}")

    print(f"\n{len(CASES) - failures}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
