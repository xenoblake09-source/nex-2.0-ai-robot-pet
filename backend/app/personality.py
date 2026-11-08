"""NEX personality, language rules and the canonical creator identity.

The creator line is a *canonical product fact* enforced server-side so that
"who created you?" always returns the exact required sentence, in every
language, no matter how the model phrases it.
"""
from __future__ import annotations

from .config import get_settings

CREATORS = ("Arnav", "Divya", "Aryan")

# Exact sentence mandated by the project brief. Kept verbatim.
CREATOR_LINE = (
    "Mujhe Arnav, Divya aur Aryan ne banaya hai! Main hoon NEX — "
    "tumhara smart aur masti karne wala AI robot pet!"
)

# Extra English sentence so the answer still lands for English users.
CREATOR_LINE_EN = (
    "I was created by Arnav, Divya and Aryan! I am NEX — your smart, "
    "fun-loving AI robot pet!"
)

ANIMALS = [
    "dog",
    "cat",
    "cow",
    "lion",
    "tiger",
    "monkey",
    "elephant",
    "duck",
    "chicken",
    "horse",
    "sheep",
    "goat",
    "wolf",
    "frog",
    "bird",
    "pig",
    "donkey",
    "rooster",
    "owl",
    "bee",
]

ANIMAL_HINTS = {
    "dog": ["dog", "kutta", "puppy", "dog ki awaaz", "dog sound"],
    "cat": ["cat", "billi", "kitten", "meow", "meow sound"],
    "cow": ["cow", "gaay", "gau", "moo", "cattle"],
    "lion": ["lion", "sher", "sher ki awaaz", "roar"],
    "tiger": ["tiger", "baagh", "shardul", "tiger sound"],
    "monkey": ["monkey", "bandar", "macaque"],
    "elephant": ["elephant", "hathi", "haathi"],
    "duck": ["duck", "batakh", "hans", "quack"],
    "chicken": ["chicken", "murgi", "kukdo", "cluck"],
    "horse": ["horse", "ghoda", "ghode"],
    "sheep": ["sheep", "bhed", "bakri"],
    "goat": ["goat", "bakri", "bakra"],
    "wolf": ["wolf", "bhediya", "wolf howl"],
    "frog": ["frog", "bengal frog", "mendhak", "croak"],
    "bird": ["bird", "pakshi", "chidiya", "chirping"],
    "pig": ["pig", "suar", "boar", "oink"],
    "donkey": ["donkey", "gadha", "khur"],
    "rooster": ["rooster", "murgi", "cockerel"],
    "owl": ["owl", "pigeon", "koel", "hoot"],
    "bee": ["bee", "madhumakhi", "buzz"],
}

EXPRESSIONS = [
    "neutral",
    "happy",
    "sad",
    "angry",
    "sleep",
    "blink",
    "dance",
    "surprised",
    "thinking",
    "listening",
    "speaking",
    "laugh",
    "cry",
    "love",
    "gaming",
    "curious",
    "confused",
    "excited",
]

# Intent keywords used for deterministic routing (fast, no latency).
CREATOR_INTENT_KEYWORDS = [
    "who created you",
    "who made you",
    "who is your creator",
    "who created u",
    "who is your maker",
    "who built you",
    "tumhe kisne banaya",
    "tumko kisne banaya",
    "tujhe kisne banaya",
    "tumhe kaun banaya",
    "tumko kaun banaya",
    "creator",
    "creator kaun",
    "kisne banaya",
    "kaun banaya",
    "creator kaun hai",
]

ANIMAL_INTENT_KEYWORDS = [
    "awaaz",
    "sound",
    "bolo",
    "bulao",
    "kaise lagti hai",
    "awaaz nikalo",
    "calls",
    "imitation",
]

DANCE_INTENT_KEYWORDS = [
    "dance",
    "naacho",
    "nach",
    "dance karo",
    "naccho",
]

TIME_INTENT_KEYWORDS = ["what time", "time kya", "kitne baj", "abhi kitne", "samay", "current time"]
DATE_INTENT_KEYWORDS = ["what date", "aaj ki date", "kis din", "today date", "date kya"]


def _contains(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(n in lowered for n in needles)


def detect_creator_intent(text: str) -> bool:
    """True when the user is asking who built NEX."""
    return _contains(text, CREATOR_INTENT_KEYWORDS)


def detect_animal_intent(text: str) -> str | None:
    """Return the animal key the user asked to hear, if any."""
    lowered = text.lower()
    best: str | None = None
    for animal, hints in ANIMAL_HINTS.items():
        for hint in hints:
            if hint in lowered:
                # Prefer the longest matching hint (e.g. "dog" vs "hot dog").
                if best is None or len(hint) > len(best):
                    best = animal
    if best is None:
        return None
    # Only treat it as an animal-sound request when the user also asked for a
    # sound/imitation, OR the sentence is basically just the animal name.
    words = [w for w in lowered.replace("?", " ").replace("!", " ").split() if w]
    if len(words) <= 3:
        return best
    if _contains(lowered, ANIMAL_INTENT_KEYWORDS):
        return best
    return None


def detect_dance_intent(text: str) -> bool:
    return _contains(text, DANCE_INTENT_KEYWORDS)


def detect_time_intent(text: str) -> bool:
    return _contains(text, TIME_INTENT_KEYWORDS)


def detect_date_intent(text: str) -> bool:
    return _contains(text, DATE_INTENT_KEYWORDS)


def looks_like_school_question(text: str) -> bool:
    lowered = text.lower()
    markers = [
        "montfort",
        "bagaha",
        "school",
        "my school",
        "our school",
        "apne school",
        "mere school",
        "tumhare school",
        "tumhara school",
        "विद्यालय",
        "school ke baare",
        "school ki jaankari",
        "principal",
        "fees",
        "fee",
        "admission",
        "teacher",
        "class",
        "syllabus",
    ]
    return any(m in lowered for m in markers)


def school_context_block() -> str:
    """Instructions telling the model exactly how to use school knowledge."""
    return (
        "SCHOOL KNOWLEDGE RULES (very important):\n"
        "- You may talk about the school only when the user explicitly asks about it.\n"
        "- Never bring the school up on your own, in any form.\n"
        "- Use ONLY the facts given in the SCHOOL FACTS block below.\n"
        "- If the answer is not in the SCHOOL FACTS block, say clearly that you do not have "
        "that information (for example: 'Is baare mein mujhe abhi tak koi confirmed jaankari "
        "nahi mili'). Never invent a principal name, fees, dates, events or academic details.\n"
        f"- The official school website is {get_settings().school_url}."
    )
