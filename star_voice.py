import re

import star_storage as storage


DEFAULT_SETTINGS = {
    "voice_mode": "conversation",
    "voice_language": "auto",
    "voice_primary_language": "en-IN",
    "voice_timeout": "5",
    "voice_phrase_time_limit": "6",
    "voice_pause_threshold": "0.8",
    "voice_energy_threshold": "300",
    "voice_spoken_confirmations": "true",
    "wake_engine": "auto",
    "wake_phrases": "hello star,hey star,star,sitar,sitara",
    "tts_voice": "en-US-JennyNeural",
    "tts_rate": "+5%",
    "tts_pitch": "+0Hz",
}

LANGUAGE_ALIASES = {
    "auto": "auto",
    "english": "en-IN",
    "en": "en-IN",
    "india english": "en-IN",
    "hindi": "hi-IN",
    "hi": "hi-IN",
    "hinglish": "auto",
    "mix": "auto",
    "mixed": "auto",
}

RECOGNITION_FALLBACKS = {
    "auto": ["en-IN", "hi-IN", "en-US"],
    "en-IN": ["en-IN", "en-US", "hi-IN"],
    "hi-IN": ["hi-IN", "en-IN", "en-US"],
    "en-US": ["en-US", "en-IN", "hi-IN"],
}

MISHEARD_REPLACEMENTS = {
    "can sell": "cancel",
    "council": "cancel",
    "cancer": "cancel",
    "cancle": "cancel",
    "kan sal": "cancel",
    "kan sel": "cancel",
    "conform": "confirm",
    "conference": "confirm",
    "confirm it": "confirm",
    "kanfarm": "confirm",
    "kanpharm": "confirm",
    "khan farm": "confirm",
    "hindi mode": "voice language hindi",
    "english mode": "voice language english",
}

CONFIRM_WORDS = {
    "confirm",
    "yes",
    "yep",
    "yeah",
    "do it",
    "continue",
    "proceed",
    "ok",
    "okay",
    "haan",
    "han",
    "ha",
    "kar de",
    "kar do",
    "chalu karo",
    "theek hai",
}

CANCEL_WORDS = {
    "cancel",
    "cancel it",
    "no",
    "nope",
    "do not",
    "dont",
    "don't",
    "mat karo",
    "mat kar",
    "nahi",
    "nahin",
    "rehne do",
    "chod do",
}

STOP_SPEAKING_WORDS = {
    "stop",
    "stop it",
    "pause",
    "be quiet",
    "shut up",
    "bas",
    "ruk",
    "ruk ja",
    "chup",
    "chup ho ja",
    "awaz band",
    "bolna band",
}

EXIT_LISTENING_WORDS = {
    "goodbye",
    "good bye",
    "bye",
    "bye star",
    "exit",
    "sleep",
    "go to sleep",
    "stop listening",
    "listening band",
    "sunna band",
    "so ja",
}

REPEAT_WORDS = {
    "repeat",
    "repeat that",
    "say again",
    "once again",
    "dobara bolo",
    "fir se bolo",
    "phir se bolo",
    "wapas bolo",
}

_DB_READY = False


def ensure_db():
    global _DB_READY
    if not _DB_READY:
        storage.init_db()
        _DB_READY = True


def parse_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def get_settings():
    ensure_db()
    settings = {}
    for key, default in DEFAULT_SETTINGS.items():
        settings[key] = storage.get_setting(key, default)
    return settings


def update_settings(**kwargs):
    ensure_db()
    updated = {}
    for key, value in kwargs.items():
        if value is None:
            continue
        if key not in DEFAULT_SETTINGS:
            continue
        clean_value = normalize_setting_value(key, value)
        storage.set_setting(key, clean_value)
        updated[key] = clean_value
    return updated


def normalize_setting_value(key, value):
    value = str(value).strip()
    if key == "wake_engine":
        clean = value.lower()
        return clean if clean in {"auto", "speech", "picovoice"} else "auto"
    if key in {"voice_language", "voice_primary_language"}:
        return LANGUAGE_ALIASES.get(value.lower(), value)
    if key in {"voice_timeout", "voice_phrase_time_limit"}:
        return str(max(1, int(float(value))))
    if key in {"voice_pause_threshold"}:
        return str(max(0.2, min(2.5, float(value))))
    if key in {"voice_energy_threshold"}:
        return str(max(50, int(float(value))))
    if key == "voice_spoken_confirmations":
        return "true" if parse_bool(value) else "false"
    return value


def normalize_text(text):
    clean = str(text or "").lower().strip()
    clean = clean.replace("`", "'")
    clean = re.sub(r"[^\w\s'.-]", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


def wake_phrases(settings=None):
    settings = settings or get_settings()
    phrases = str(settings.get("wake_phrases") or DEFAULT_SETTINGS["wake_phrases"])
    return [normalize_text(item) for item in phrases.split(",") if normalize_text(item)]


def detect_wake_phrase(text, settings=None):
    clean = normalize_text(text)
    for phrase in wake_phrases(settings):
        if clean == phrase or clean.startswith(phrase + " "):
            return phrase
    return None


def command_after_wake(text, settings=None):
    clean = normalize_text(text)
    phrase = detect_wake_phrase(clean, settings=settings)
    if not phrase:
        return ""
    return clean[len(phrase):].strip()


def clean_transcript(text):
    clean = normalize_text(text)
    clean = clean.replace("’", "'").replace("`", "'")

    wake_prefixes = [
        "hello star",
        "hey star",
        "ok star",
        "okay star",
        "star",
        "sitar",
        "sitara",
    ]
    for prefix in wake_prefixes:
        if clean == prefix:
            return ""
        if clean.startswith(prefix + " "):
            clean = clean[len(prefix):].strip()
            break

    for wrong, right in MISHEARD_REPLACEMENTS.items():
        clean = re.sub(rf"\b{re.escape(wrong)}\b", right, clean)

    return clean


def recognition_languages(settings=None):
    settings = settings or get_settings()
    configured = settings.get("voice_language", "auto")
    configured = LANGUAGE_ALIASES.get(str(configured).lower(), configured)
    languages = RECOGNITION_FALLBACKS.get(configured, [configured])
    primary = LANGUAGE_ALIASES.get(str(settings.get("voice_primary_language", "en-IN")).lower(), settings.get("voice_primary_language", "en-IN"))
    ordered = [primary] + languages
    unique = []
    for language in ordered:
        if language and language not in unique:
            unique.append(language)
    return unique


def confirmation_intent(text):
    clean = clean_transcript(text)
    if clean in CONFIRM_WORDS:
        return "confirm"
    if clean in CANCEL_WORDS:
        return "cancel"
    return None


def is_repeat_command(text):
    return clean_transcript(text) in REPEAT_WORDS


def is_stop_speaking_command(text):
    clean = clean_transcript(text)
    return clean in STOP_SPEAKING_WORDS or any(clean.startswith(word + " ") for word in STOP_SPEAKING_WORDS)


def is_exit_listening_command(text):
    clean = clean_transcript(text)
    return clean in EXIT_LISTENING_WORDS or any(clean.startswith(word + " ") for word in EXIT_LISTENING_WORDS)


def remember_interaction(command, reply):
    ensure_db()
    if command:
        storage.set_setting("last_voice_command", command)
    if reply:
        storage.set_setting("last_voice_reply", reply)


def last_voice_state():
    ensure_db()
    return {
        "last_command": storage.get_setting("last_voice_command", ""),
        "last_reply": storage.get_setting("last_voice_reply", ""),
    }


def format_settings(settings=None):
    settings = settings or get_settings()
    languages = ", ".join(recognition_languages(settings))
    return (
        f"Voice mode is {settings['voice_mode']}. "
        f"Wake engine is {settings.get('wake_engine', 'auto')}. "
        f"Language is {settings['voice_language']} with fallback {languages}. "
        f"Listening timeout is {settings['voice_timeout']} seconds."
    )


def parse_voice_command(command):
    text = clean_transcript(command)
    if text in {"voice status", "voice settings", "listening status", "speech status"}:
        return {"action": "status"}
    if is_repeat_command(text):
        return {"action": "repeat"}
    if text.startswith(("voice language", "set voice language", "speech language")):
        for phrase in ["set voice language", "voice language", "speech language"]:
            if text.startswith(phrase):
                language = text[len(phrase):].strip()
                return {"action": "set", "voice_language": LANGUAGE_ALIASES.get(language, language)}
    if text.startswith(("voice mode", "set voice mode")):
        for phrase in ["set voice mode", "voice mode"]:
            if text.startswith(phrase):
                return {"action": "set", "voice_mode": text[len(phrase):].strip()}
    if text.startswith(("wake engine", "set wake engine")):
        for phrase in ["set wake engine", "wake engine"]:
            if text.startswith(phrase):
                return {"action": "set", "wake_engine": text[len(phrase):].strip()}
    if text in {"hindi mode", "hinglish mode", "english mode"}:
        language = text.replace(" mode", "")
        return {"action": "set", "voice_language": LANGUAGE_ALIASES.get(language, language)}
    return None
