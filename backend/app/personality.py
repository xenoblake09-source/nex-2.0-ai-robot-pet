"""NEX personality, language rules and the canonical creator identity.

The creator line is a *canonical product fact* enforced server-side so that
"who created you?" always returns the exact required sentence, in every
language, no matter how the model phrases it.
"""
from __future__ import annotations

from .config import get_settings

CREATORS = ("Arnav", "Divya", "Aryan")

# Exact sentence mandated by the project brief. Kept verbatim.
# This is the canonical English answer — it is used as-is and never rephrased.
CREATOR_LINE_EN = "ARNAV, DIVYA AND ARYAN created me."

# Hindi version of the creator line (Devanagari script).
CREATOR_LINE_HI = (
    "मुझे Arnav, Divya और Aryan ने बनाया है! मैं NEX हूँ — "
    "तुम्हारे स्मार्ट और मस्ती करने वाले AI रोबोट पेट!"
)

# Hinglish version (Hindi written in Latin letters).
CREATOR_LINE_HINGLISH = (
    "Mujhe Arnav, Divya aur Aryan ne banaya hai! Main hoon NEX — "
    "tumhara smart aur masti karne wala AI robot pet!"
)

# Legacy alias kept for backward compatibility in tests/config endpoint.
CREATOR_LINE = CREATOR_LINE_HINGLISH

# Map language codes to the correct creator line.
CREATOR_LINES = {
    "en": CREATOR_LINE_EN,
    "english": CREATOR_LINE_EN,
    "hi": CREATOR_LINE_HI,
    "hindi": CREATOR_LINE_HI,
    "hinglish": CREATOR_LINE_HINGLISH,
}


def get_creator_line(language: str) -> str:
    """Return the creator line in the requested language.

    English always gets the exact mandated sentence. Hindi gets the Hindi
    version. Hinglish and any unrecognized code get the Hinglish version
    (which works for both Latin-script Hindi and informal English).
    """
    if not language:
        return CREATOR_LINE_EN
    lang = language.strip().lower()
    return CREATOR_LINES.get(lang, CREATOR_LINE_HINGLISH)

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

# Expression command keywords — these route directly to the eye expression
# system without waiting for Gemini. This makes commands like "be happy",
# "laugh", "sleep" instant and reliable in every language.
EXPRESSION_INTENT_KEYWORDS: dict[str, list[str]] = {
    "happy": [
        "be happy", "show happy", "happy expression", "make happy",
        "khush", "happy face", "dkhola", "dekho khush",
    ],
    "sad": [
        "be sad", "show sad", "sad expression", "make sad",
        "udaas", "sad face",
    ],
    "angry": [
        "be angry", "show angry", "angry expression", "make angry",
        "gussa", "khafa", "angry face",
    ],
    "laugh": [
        "laugh", "laughter", "haso", "hasna", "laugh expression",
    ],
    "sleep": [
        "sleep", "so jao", "soye", "sleep expression", "so jao",
    ],
    "surprised": [
        "be surprised", "show surprised", "surprised expression",
        " hairan", "hairani", "wow",
    ],
    "cry": [
        "cry", "rote", "cry expression", "rulao",
    ],
    "love": [
        "be love", "show love", "love expression", "pyaar", "muhabbat",
    ],
    "dance": [
        "dance", "naacho", "nach", "dance karo", "naccho", "dance expression",
    ],
    "thinking": [
        "be thinking", "think", "socho", "thinking expression",
    ],
    "curious": [
        "be curious", "curious expression", "shauk",
    ],
    "gaming": [
        "game", "khelo", "gaming expression", "game mode",
    ],
}

# Sleep action keywords (different from the expression — this triggers
# the sleep animation + state change).
SLEEP_ACTION_KEYWORDS = [
    "go to sleep", "sleep now", "so jao", "so jaana", "soye jao",
    "go sleep", "sleep mode", "aajao sone", "night night",
]

# Wake action keywords (wake NEX from sleep).
WAKE_ACTION_KEYWORDS = [
    "wake up", "wake", "uttho", "utho", "wake nex", "good morning",
]


def _contains(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(n in lowered for n in needles)


def detect_creator_intent(text: str) -> bool:
    """True when the user is asking who built NEX."""
    return _contains(text, CREATOR_INTENT_KEYWORDS)


def detect_animal_intent(text: str) -> str | None:
    """Return the animal key the user asked to hear, if any.

    Handles patterns like:
      "make a dog sound"
      "can you play a cat sound?"
      "dog ki awaaz nikalo"
      "billi ki awaaz"
      "play the sound of a lion"
    """
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
    # Don't execute if negated: "don't play a dog sound"
    for hint in ANIMAL_HINTS.get(best, []):
        if hint in lowered and _is_negated(lowered, hint):
            return None
    # Check if the request is for a sound/imitation, OR the sentence is
    # basically just the animal name. Also handle "make a X sound",
    # "play X sound", "X ki awaaz" patterns which are implicitly sound
    # requests even without the ANIMAL_INTENT_KEYWORDS matching.
    words = [w for w in lowered.replace("?", " ").replace("!", " ").split() if w]
    if len(words) <= 3:
        return best
    # Check for explicit sound request keywords
    if _contains(lowered, ANIMAL_INTENT_KEYWORDS):
        return best
    # Check for implicit sound request patterns:
    # "make a dog sound", "play cat sound", "dog ki awaaz"
    if any(pattern in lowered for pattern in [
        "sound of", "ki awaaz", "ki aawaz", "ka sound",
        "make a", "play a", "play the", "bring a",
        "hear a", "listen to", "want to hear",
    ]):
        return best
    return None


# Negation keywords — if present near an action keyword, the command is
# negated and should NOT execute the action.
NEGATION_KEYWORDS = [
    "don't", "dont", "do not", "no", "never", "not", "please don't",
    "nahi", "nahi", "mat", "na", "kabhi nahi", "nahi chahiye",
    "i don't want", "i do not want", "mujhe nahi", "main nahi",
    "mat karo", "mat kro", "karo mat", "kar mat",
    "don't dance", "naacho mat", "nacho mat",
]


def _is_negated(text: str, keyword: str) -> bool:
    """Check if a keyword appears in a negated context.

    Looks for negation words within ~60 chars before OR after the keyword,
    since Hindi often places negation after the verb (e.g. "naacho mat").
    Uses word-boundary matching so "na" doesn't match inside "naacho".
    """
    import re as _re
    lowered = text.lower()
    idx = lowered.find(keyword.lower())
    if idx < 0:
        return False
    # Check the 60 chars before AND after the keyword for negation words
    before = lowered[max(0, idx - 60):idx]
    after = lowered[idx:idx + 60]
    for neg in NEGATION_KEYWORDS:
        escaped = _re.escape(neg)
        if _re.search(rf'\b{escaped}\b', before) or _re.search(rf'\b{escaped}\b', after):
            return True
    return False


def detect_dance_intent(text: str) -> bool:
    """True when the user asks NEX to dance (not when they say not to)."""
    for kw in DANCE_INTENT_KEYWORDS:
        if kw in text.lower() and not _is_negated(text, kw):
            return True
    return False


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


def detect_expression_intent(text: str) -> str | None:
    """Return the expression name the user explicitly asked for, if any.

    This is deterministic — it does NOT call Gemini. It lets commands like
    "be happy" or "laugh" trigger the correct eye expression instantly.
    """
    lowered = text.lower()
    best: str | None = None
    best_len = 0
    for expression, keywords in EXPRESSION_INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered and not _is_negated(lowered, keyword):
                if len(keyword) > best_len:
                    best = expression
                    best_len = len(keyword)
    return best


def detect_sleep_action(text: str) -> bool:
    """True when the user asked NEX to go to sleep (not when negated)."""
    lowered = text.lower()
    for kw in SLEEP_ACTION_KEYWORDS:
        if kw in lowered and not _is_negated(lowered, kw):
            return True
    return False


def detect_wake_action(text: str) -> bool:
    """True when the user asked NEX to wake up (not when negated)."""
    lowered = text.lower()
    for kw in WAKE_ACTION_KEYWORDS:
        if kw in lowered and not _is_negated(lowered, kw):
            return True
    return False


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

# Devanagari character range — if present, the message is almost certainly
# Hindi written in native script.
_DEVANAGARI_RE = None  # compiled lazily below

_HINDI_WORDS = frozenset({
    "最常见的": 0,  # placeholder to keep the set non-empty
})

# Common Hindi/Hinglish words that strongly indicate the language.
# Only words that are NOT common English words are included here —
# words like "is", "the", "to", "of" appear in both languages and would
# cause false positives.
_HINDI_WORDS = frozenset({
    "kya", "hai", "hoon", "ki", "ke", "ka", "ko", "ne", "tum", "tumhare",
    "tumhara", "mujhe", "main", "aur", "bhi", "na", "nahi", "agar",
    "lekin", "vo", "wo", "isme", "usme", "ab", "abhi", "kaise", "kuch",
    "aise", "bahut", "thoda", "zid", "ruk", "jao", "hao", "bolo",
    "kehna", "suno", "dekho", "haan", "hmm", "are", "re", "yaara",
    "bhai", "yaar", "babua", "accha", "theek", "thik", "jaisa", "jaise",
    "kaya", "kahan", "kab", "con", "pakka", "sach", "zor", "bas",
    "isko", "unko", "hamko", "hame", "tumse", "unke", "ise", "waise",
    "nai", "keh", "ku", "kyo", "kyun", "hum", "hume", "tho",
    "bhi", "tak", "para", "chuka", "raha", "rahe", "gaya", "gayi",
    "hoga", "hogai", "tha", "thi", "honge", "bana", "banao",
})

# Common French words for language detection.
_FRENCH_WORDS = frozenset({
    "bonjour", "merci", "salut", "comment", "ça", "ca", "est", "je",
    "tu", "il", "elle", "nous", "vous", "ils", "elles", "un", "une",
    "des", "le", "la", "et", "ou", "que", "qui", "quoi", "où", "pour",
    "dans", "sur", "avec", "sans", "plus", "moins", "très", "aussi",
})

# Common Spanish words.
_SPANISH_WORDS = frozenset({
    "hola", "gracias", "cómo", "como", "qué", "que", "es", "un", "una",
    "el", "la", "y", "o", "por", "para", "con", "sin", "se", "su",
    "muy", "mucho", "muchos", "bueno", "buenos", "día", "noche",
    "hablar", "decir", "ver", "ir", "ser", "estar", "tener",
})

# Common German words.
_GERMAN_WORDS = frozenset({
    "hallo", "danke", "bitte", "ich", "du", "er", "sie", "es", "wir",
    "ihr", "und", "oder", "nicht", "sehr", "auch", "wie", "was",
    "wer", "wo", "wann", "warum", "mit", "von", "zu", "auf",
})


def detect_language(text: str) -> str:
    """Detect the language of a message.

    Returns one of: 'en', 'hi', 'hinglish', 'fr', 'es', 'de', or 'unknown'.

    Detection priority:
    1. Devanagari script → Hindi (hi)
    2. French words → French (fr)
    3. Spanish words → Spanish (es)
    4. German words → German (de)
    5. Hindi/Hinglish words → Hinglish (hinglish)
    6. English words → English (en)
    7. Unknown → 'unknown'
    """
    if not text:
        return "en"

    lowered = text.lower()

    # 1. Devanagari script → Hindi
    import re as _re
    if _re.search(r'[\u0900-\u097F]', text):
        return "hi"

    # 2. French
    fr_matches = sum(1 for w in lowered.split() if w.strip(".,!?;:") in _FRENCH_WORDS)
    if fr_matches >= 2:
        return "fr"

    # 3. Spanish
    es_matches = sum(1 for w in lowered.split() if w.strip(".,!?;:") in _SPANISH_WORDS)
    if es_matches >= 2:
        return "es"

    # 4. German
    de_matches = sum(1 for w in lowered.split() if w.strip(".,!?;:") in _GERMAN_WORDS)
    if de_matches >= 2:
        return "de"

    # 5. Hindi/Hinglish words
    hi_matches = sum(1 for w in lowered.split() if w.strip(".,!?;:") in _HINDI_WORDS)
    if hi_matches >= 2:
        return "hinglish"
    elif hi_matches == 1:
        return "hinglish"

    # 6. English
    en_words = {"the", "is", "are", "you", "what", "how", "tell", "me",
                "please", "hello", "hey", "my", "name", "time", "weather",
                "do", "does", "can", "would", "will", "who", "where",
                "when", "why", "this", "that", "these", "those", "and",
                "or", "but", "if", "so", "too", "very", "just", "about",
                "not", "no", "yes", "ok", "okay", "good", "great", "fine"}
    en_matches = sum(1 for w in lowered.split() if w.strip(".,!?;:") in en_words)
    if en_matches >= 1:
        return "en"

    return "unknown"


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
