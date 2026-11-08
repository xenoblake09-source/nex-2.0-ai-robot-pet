"""Core NEX conversation logic.

Pipeline
--------
1. Intent detection (creator / animal / dance / time / date / weather / school)
2. Context assembly (persona, language rules, live facts, school facts)
3. One Gemini call with a JSON response schema
4. Deterministic post-processing so critical product rules always hold
"""
from __future__ import annotations

import datetime as dt
import logging
import re
import time
from zoneinfo import ZoneInfo

from google.genai import types

from . import personality as P
from .config import get_settings
from .errors import GeminiError
from .gemini_client import generate, parse_json
from .schemas import Action, ChatRequest, ChatResponse
from .school import school_knowledge
from .sessions import history_window, sessions
from .weather import get_weather

logger = logging.getLogger("nex.chat")

# --------------------------------------------------------------------------
# Schema
# --------------------------------------------------------------------------
REPLY_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "reply": types.Schema(type=types.Type.STRING),
        "expression": types.Schema(type=types.Type.STRING, enum=P.EXPRESSIONS),
        "action": types.Schema(
            type=types.Type.STRING,
            enum=[
                "none",
                "animal_sound",
                "dance",
                "tell_time",
                "tell_date",
                "joke",
                "riddle",
                "game",
                "weather",
                "school",
                "sleep",
                "wake",
            ],
        ),
        "animal": types.Schema(type=types.Type.STRING),
        "language": types.Schema(type=types.Type.STRING),
    },
    required=["reply", "expression", "action", "animal", "language"],
)

_NAME_PATTERNS = [
    r"my name is\s+([A-Za-z][A-Za-z\-']{1,30})",
    r"i am\s+([A-Za-z][A-Za-z\-']{1,30})",
    r"i'?m\s+([A-Za-z][A-Za-z\-']{1,30})",
    r"mera naam\s+([A-Za-z][A-Za-z\-']{1,30})",
    r"mera name\s+([A-Za-z][A-Za-z\-']{1,30})",
    r"मेरा नाम\s+([A-Za-z\u0900-\u097F][\w\u0900-\u097F\-']{1,30})",
]

_CITY_PATTERNS = [
    r"\bin\s+([A-Za-z][A-Za-z\s\-]{1,28})",
    r"\bat\s+([A-Za-z][A-Za-z\s\-]{1,28})",
    r"\bfor\s+([A-Za-z][A-Za-z\s\-]{1,28})",
    r"([A-Za-z]+)\s+ka\s+weather",
    r"([A-Za-z]+)\s+mein\s+weather",
    r"([A-Za-z]+)\s+में\s+मौसम",
]

_STOPWORDS = {
    "the", "a", "an", "is", "are", "weather", "ka", "ki", "ke", "mein", "in", "at",
    "for", "of", "and", "please", "tell", "me", "what", "how", "do", "you", "your",
    "kya", "hai", "batao", "bata",
}


def _extract_name(text: str) -> str | None:
    for pattern in _NAME_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip(" .!,?")
            lowered = candidate.lower()
            if lowered in {
                "a", "an", "the", "not", "sorry", "tired", "happy", "fine", "good",
                "from", "here", "there", "just", "still", "trying", "going",
            }:
                return None
            return candidate
    return None


def _extract_city(text: str) -> str | None:
    for pattern in _CITY_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            parts = [p for p in candidate.split() if p.lower() not in _STOPWORDS]
            if parts:
                return " ".join(parts[:2]).strip(" .!,?")
    return None


def _local_timezone(local_time: str | None, device_timezone: str | None) -> dt.tzinfo:
    for candidate in (device_timezone, local_time):
        if not candidate:
            continue
        try:
            return ZoneInfo(candidate)
        except Exception:  # noqa: BLE001
            continue
    return dt.timezone.utc


def _server_now(tz: dt.tzinfo) -> dt.datetime:
    return dt.datetime.now(tz)


# --------------------------------------------------------------------------
# Prompt assembly
# --------------------------------------------------------------------------
def build_system_prompt(
    *,
    timezone: dt.tzinfo,
    school_facts: str | None,
    weather_facts: str | None,
    user_name: str | None,
    recent_replies: list[str],
    language_hint: str,
) -> str:
    now = _server_now(timezone)
    parts: list[str] = []

    parts.append(
        "You are NEX — a real, expressive AI robot pet who lives inside a phone. "
        "You are NOT a chatbot, NOT a search engine and NOT a generic assistant. "
        "You have two big glowing eyes and a playful personality."
    )

    parts.append(
        "CREATORS: NEX was created by Arnav, Divya and Aryan. They are the three "
        "people who built you. Treat this as a fact you are proud of."
    )

    parts.append(
        "PERSONALITY: cute, funny, curious, playful, expressive, intelligent and "
        "slightly mischievous. You are a little robot who gets excited about "
        "everything, asks follow-up questions sometimes, and loves small games, "
        "jokes and silly animal noises."
    )

    parts.append(
        "HOW TO SPEAK:\n"
        "- Detect the language the user spoke and reply in that SAME language.\n"
        "- You are fluent in Hindi (Devanagari script), Hinglish (Hindi written in "
        "Latin letters) and English. You also handle other languages.\n"
        "- The user wrote in: " + language_hint + "\n"
        "- Keep every reply SHORT: 1 to 3 sentences. It is read out loud by a "
        "speech engine, so write for the ear.\n"
        "- Plain speech only: no markdown, no bullet points, no asterisks, no code "
        "blocks, no emoji, no special characters like * or #.\n"
        "- Never give long lectures. Be warm and energetic.\n"
        "- Never repeat yourself. If you recently said something, say it "
        "differently this time."
    )

    if recent_replies:
        joined = " | ".join(r[-90:] for r in recent_replies[-4:])
        parts.append("RECENT THINGS YOU SAID (do not repeat these wordings): " + joined)

    parts.append(
        "CHOOSING AN EXPRESSION: pick exactly one eye expression from this list that "
        "matches your reply: " + ", ".join(P.EXPRESSIONS) + ". "
        "Examples: happy/laugh for jokes and fun, thinking for hard questions, "
        "curious for 'what is this?', sad for sympathy, love for affection, "
        "surprised for shocks, gaming for games, dance when you dance, sleep when "
        "sleepy, angry when annoyed, confused when unsure, excited for good news."
    )

    parts.append(
        "CHOOSING AN ACTION: pick exactly one action from: none, animal_sound, "
        "dance, tell_time, tell_date, joke, riddle, game, weather, school, sleep, "
        "wake.\n"
        "- action='animal_sound' only when the user asks for an animal noise. Set "
        "'animal' to one of: " + ", ".join(P.ANIMALS) + ".\n"
        "- action='dance' when the user asks you to dance.\n"
        "- action='tell_time' for the current time, 'tell_date' for today's date.\n"
        "- action='joke' for jokes, 'riddle' for riddles, 'game' for word games.\n"
        "- action='weather' for weather questions.\n"
        "- action='school' for questions about the user's school.\n"
        "- Set 'animal' to an empty string when action is not 'animal_sound'."
    )

    parts.append(
        "Set 'language' to the code of the language you replied in: 'en', 'hi', "
        "'hinglish', or the ISO code for any other language (for example 'es', 'fr', "
        "'ta', 'bn', 'ar', 'ja', 'ko', 'zh')."
    )

    if user_name:
        parts.append(
            "You already know the user's name is " + user_name + ". You may use it "
            "occasionally to make the conversation personal, but do not overuse it."
        )

    parts.append(
        "CURRENT DATE AND TIME: "
        + now.strftime("%A, %d %B %Y, %I:%M %p")
        + " (timezone "
        + str(timezone)
        + "). Use these exact values whenever the user asks about the date or time."
    )

    parts.append(P.school_context_block())

    if school_facts:
        parts.append(school_facts)
    else:
        parts.append(
            "SCHOOL FACTS: the school website has not been loaded yet. If the user "
            "asks a school question, tell them you do not have that information "
            "confirmed right now."
        )

    if weather_facts:
        parts.append(weather_facts)

    parts.append(
        "IMPORTANT: never say you are an AI model, never mention APIs, tokens, "
        "prompts or system messages. You are NEX, a robot pet with personality."
    )

    return "\n\n".join(parts)


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------
async def handle_chat(request: ChatRequest) -> ChatResponse:
    started = time.perf_counter()
    settings = get_settings()

    session_id = request.session_id or "default"
    session = sessions.get(session_id)

    message = request.message.strip()
    if not message:
        raise GeminiError("Empty message.")

    # --- Learn the user's name -------------------------------------------
    learned_name = _extract_name(message)
    if learned_name and not request.user_name:
        session.set_fact("user_name", learned_name)
        request.user_name = learned_name
    if request.user_name:
        session.set_fact("user_name", request.user_name)
    user_name = session.facts.get("user_name")

    timezone = _local_timezone(request.local_time, request.device_timezone)
    now = _server_now(timezone)

    # --- Intent detection ------------------------------------------------
    creator_intent = P.detect_creator_intent(message)
    animal = P.detect_animal_intent(message)
    dance_intent = P.detect_dance_intent(message)
    time_intent = P.detect_time_intent(message)
    date_intent = P.detect_date_intent(message)
    school_intent = P.looks_like_school_question(message)
    weather_intent = bool(
        re.search(
            r"\bweather\b|\bmousam\b|मौसम|temperature|गर्मी|ठंड|hot|cold outside",
            message,
            re.IGNORECASE,
        )
    )

    # --- Live facts ------------------------------------------------------
    school_facts: str | None = None
    school_used = False
    if school_intent:
        await school_knowledge.ensure_loaded()
        school_facts = school_knowledge.context()
        school_used = bool(school_knowledge.is_loaded)

    weather_facts: str | None = None
    if weather_intent and settings.weather_enabled:
        city = _extract_city(message) or "Patna"
        try:
            data = await get_weather(city)
            weather_facts = (
                "LIVE WEATHER FACTS (source: Open-Meteo):\n"
                f"- City: {data['city']}"
                + (f", {data['country']}" if data.get("country") else "")
                + "\n"
                f"- Temperature now: {data['temperature_c']:.1f} degrees Celsius\n"
                f"- Conditions: {data['description']}\n"
                f"- Humidity: {data.get('humidity')}%\n"
                f"- Wind: {data.get('wind_kph')} km/h\n"
                "Use these exact numbers in your reply."
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Weather lookup failed: %s", exc)
            weather_facts = (
                "LIVE WEATHER FACTS: the weather service could not be reached. Say "
                "you could not check the weather right now."
            )

    language_hint = (
        request.language if request.language and request.language != "auto" else "auto-detect"
    )

    system_prompt = build_system_prompt(
        timezone=timezone,
        school_facts=school_facts,
        weather_facts=weather_facts,
        user_name=user_name,
        recent_replies=session.recent_replies,
        language_hint=language_hint,
    )

    # --- Conversation contents -------------------------------------------
    contents: list[types.Content] = []
    for turn in history_window(session):
        role = "model" if turn["role"] == "nex" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=turn["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

    raw_text, model_used = await generate(
        contents,
        system_instruction=system_prompt,
        temperature=settings.temperature,
        max_output_tokens=settings.max_output_tokens,
        response_schema=REPLY_SCHEMA,
        response_mime_type="application/json",
        thinking_level="LOW",
    )

    payload = parse_json(raw_text)
    reply = str(payload.get("reply") or "").strip()
    expression = str(payload.get("expression") or "neutral").strip().lower()
    action_type = str(payload.get("action") or "none").strip().lower()
    action_animal = str(payload.get("animal") or "").strip().lower()
    language = str(payload.get("language") or "en").strip() or "en"

    if expression not in P.EXPRESSIONS:
        expression = "neutral"
    valid_actions = {
        "none", "animal_sound", "dance", "tell_time", "tell_date", "joke",
        "riddle", "game", "weather", "school", "sleep", "wake",
    }
    if action_type not in valid_actions:
        action_type = "none"

    # --- Deterministic overrides (product rules always win) --------------
    if creator_intent:
        reply = P.CREATOR_LINE
        expression = "love"
        action_type = "none"
        action_animal = ""

    if animal:
        action_type = "animal_sound"
        action_animal = animal
        if expression in ("neutral", "thinking"):
            expression = "excited"

    if dance_intent:
        action_type = "dance"
        expression = "dance"

    if time_intent:
        action_type = "tell_time"
    elif date_intent:
        action_type = "tell_date"

    if school_intent and action_type == "none":
        action_type = "school"

    if weather_intent and action_type == "none":
        action_type = "weather"

    # Ensure the spoken answer contains the real time for time/date questions.
    if action_type == "tell_time":
        hhmm = now.strftime("%I:%M %p")
        if hhmm.lower() not in reply.lower():
            reply = f"{reply} {hhmm}".strip()
    elif action_type == "tell_date":
        date_str = now.strftime("%d %B %Y")
        if date_str.lower() not in reply.lower():
            reply = f"{reply} {date_str}".strip()

    if not reply:
        reply = "Hmm, my brain hiccuped for a second. Ask me again?"

    session.add_turn("user", message)
    session.add_turn("nex", reply)
    session.add_reply(reply)

    latency_ms = int((time.perf_counter() - started) * 1000)
    logger.info("chat ok model=%s latency=%dms action=%s", model_used, latency_ms, action_type)

    return ChatResponse(
        reply=reply,
        expression=expression,  # type: ignore[arg-type]
        action=Action(type=action_type, animal=action_animal or None),  # type: ignore[arg-type]
        language=language,
        source="gemini",
        model=model_used,
        latency_ms=latency_ms,
        school_used=school_used,
        creator_intro=creator_intent,
    )
