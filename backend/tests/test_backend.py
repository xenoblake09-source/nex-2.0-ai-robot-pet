"""Real functional tests for the NEX backend.

Run with:
    cd backend && python -m tests.test_backend
or
    cd backend && python tests/test_backend.py

These tests hit the real code paths. Tests that need Gemini are reported as
SKIP when GEMINI_API_KEY is not configured — they are never faked.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.personality import CREATOR_LINE, detect_animal_intent, detect_creator_intent  # noqa: E402

BASE_URL = os.getenv("NEX_TEST_BASE_URL", "http://127.0.0.1:8000")
HAS_KEY = bool(get_settings().gemini_api_key)

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(name)
        print(f"  PASS  {name}" + (f"  ({detail})" if detail else ""))
    else:
        FAILED.append(name)
        print(f"  FAIL  {name}  ({detail})")


def skip(name: str, why: str = "GEMINI_API_KEY not configured") -> None:
    print(f"  SKIP  {name}  ({why})")


def test_intent_detection() -> None:
    print("\n[1] Intent detection (offline, real code)")
    check("creator intent (english)", detect_creator_intent("Who created you?"), "Who created you?")
    check(
        "creator intent (hinglish)",
        detect_creator_intent("Tumhe kisne banaya?"),
        "Tumhe kisne banaya?",
    )
    check(
        "creator intent (creator word)",
        detect_creator_intent("who is your creator"),
        "who is your creator",
    )
    check(
        "animal intent (hindi)",
        detect_animal_intent("NEX, dog ki awaaz nikalo!") == "dog",
        "dog",
    )
    check("animal intent (english)", detect_animal_intent("play a cat sound") == "cat", "cat")
    check("no animal intent", detect_animal_intent("what is the time") is None)


def test_health(client: httpx.Client) -> None:
    print("\n[2] GET /health")
    r = client.get("/health", timeout=15)
    check("health returns 200", r.status_code == 200, str(r.status_code))
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    check("health has status=ok", data.get("status") == "ok", json.dumps(data)[:160])
    check("health reports gemini_configured", "gemini_configured" in data)
    check(
        "health reports gemini_configured correctly",
        data.get("gemini_configured") == HAS_KEY,
        f"reported={data.get('gemini_configured')} expected={HAS_KEY}",
    )


def test_config(client: httpx.Client) -> None:
    print("\n[3] GET /api/config")
    r = client.get("/api/config", timeout=15)
    check("config returns 200", r.status_code == 200, str(r.status_code))
    data = r.json()
    check("config lists 15+ animals", len(data.get("animals", [])) >= 15, str(len(data.get("animals", []))))
    check("config creator line exact", data.get("creator_line") == CREATOR_LINE, data.get("creator_line", "")[:60])
    check("config has creators", data.get("creators") == ["Arnav", "Divya", "Aryan"], str(data.get("creators")))
    check(
        "config leaks no api key",
        "GEMINI_API_KEY" not in json.dumps(data) and "AIza" not in json.dumps(data),
    )


def test_animals(client: httpx.Client) -> None:
    print("\n[4] GET /api/animals")
    r = client.get("/api/animals", timeout=15)
    data = r.json()
    check("animals endpoint works", r.status_code == 200 and data.get("count", 0) >= 15, str(data.get("count")))


def test_chat_validation(client: httpx.Client) -> None:
    print("\n[5] POST /api/chat — validation and error shapes")
    r = client.post("/api/chat", json={"message": ""}, timeout=15)
    check("empty message rejected with 422", r.status_code == 422, str(r.status_code))

    if not HAS_KEY:
        skip("live Gemini chat", "GEMINI_API_KEY not configured")
        r = client.post("/api/chat", json={"message": "hello"}, timeout=30)
        check(
            "missing key yields clear config_error",
            r.status_code == 503 and r.json().get("error", {}).get("code") == "config_error",
            f"{r.status_code} {r.text[:120]}",
        )
        return

    r = client.post(
        "/api/chat",
        json={"message": "Hello NEX!", "language": "auto", "session_id": "pytest"},
        timeout=90,
    )
    check("chat returns 200", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    if r.status_code != 200:
        return
    data = r.json()
    check("chat has non-empty reply", bool(data.get("reply")), data.get("reply", "")[:80])
    check("chat reply is from gemini", data.get("source") == "gemini", str(data.get("source")))
    check("chat has valid expression", bool(data.get("expression")), str(data.get("expression")))
    check("chat reports model", bool(data.get("model")), str(data.get("model")))
    check("chat latency recorded", isinstance(data.get("latency_ms"), int))


def test_creator_identity(client: httpx.Client) -> None:
    print("\n[6] POST /api/chat — creator identity (exact sentence)")
    if not HAS_KEY:
        skip("creator identity over live Gemini", "GEMINI_API_KEY not configured")
        return
    for question in ["Who created you?", "Tumhe kisne banaya?", "Who is your creator?"]:
        r = client.post("/api/chat", json={"message": question, "session_id": "pytest2"}, timeout=90)
        ok = r.status_code == 200 and r.json().get("reply") == CREATOR_LINE
        check(
            f"exact creator reply for '{question}'",
            ok,
            r.json().get("reply", "")[:90] if r.status_code == 200 else r.text[:90],
        )


def test_animal_request(client: httpx.Client) -> None:
    print("\n[7] POST /api/chat — animal sound action")
    if not HAS_KEY:
        skip("animal sound routing over live Gemini", "GEMINI_API_KEY not configured")
        return
    r = client.post(
        "/api/chat",
        json={"message": "NEX, dog ki awaaz nikalo!", "session_id": "pytest3"},
        timeout=90,
    )
    if r.status_code != 200:
        check("animal request works", False, r.text[:150])
        return
    action = r.json().get("action", {})
    check("animal action detected", action.get("type") == "animal_sound", json.dumps(action))
    check("animal is dog", action.get("animal") == "dog", str(action.get("animal")))


def test_school(client: httpx.Client) -> None:
    print("\n[8] GET /api/school — live website retrieval")
    r = client.get("/api/school", timeout=45)
    check("school endpoint 200", r.status_code == 200, str(r.status_code))
    data = r.json()
    check("school website fetched", bool(data.get("loaded")), json.dumps(data)[:200])
    check("school text is substantial", data.get("chars", 0) > 200, f"{data.get('chars')} chars")


def test_weather(client: httpx.Client) -> None:
    print("\n[9] GET /api/weather — live Open-Meteo")
    r = client.get("/api/weather", params={"city": "Patna"}, timeout=45)
    check("weather endpoint 200", r.status_code == 200, r.text[:150])
    if r.status_code == 200:
        data = r.json()
        check(
            "weather has temperature",
            isinstance(data.get("temperature_c"), (int, float)),
            str(data.get("temperature_c")),
        )
        check("weather source is open-meteo", data.get("source") == "open-meteo")


def main() -> int:
    print("=" * 68)
    print("NEX backend functional tests")
    print(f"target: {BASE_URL}")
    print(f"gemini configured: {HAS_KEY}")
    print("=" * 68)

    test_intent_detection()

    with httpx.Client(base_url=BASE_URL) as client:
        for fn in (
            test_health,
            test_config,
            test_animals,
            test_chat_validation,
            test_creator_identity,
            test_animal_request,
            test_school,
            test_weather,
        ):
            try:
                fn(client)
            except Exception as exc:  # noqa: BLE001
                check(fn.__name__, False, f"exception {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    print(f"PASSED: {len(PASSED)}   FAILED: {len(FAILED)}")
    if FAILED:
        print("Failures:")
        for name in FAILED:
            print(f"  - {name}")
    print("=" * 68)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
