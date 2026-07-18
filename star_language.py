import re

import star_storage as storage


LOCAL_REWRITES = [
    (r"\bchrome kholo\b", "open chrome"),
    (r"\bchrome khol\b", "open chrome"),
    (r"\bchrome band karo\b", "close chrome"),
    (r"\bchrome band kar\b", "close chrome"),
    (r"\bchrome bandh karo\b", "close chrome"),
    (r"\bchrome bandh kar\b", "close chrome"),
    (r"\bchrome close karo\b", "close chrome"),
    (r"\bchrome close kar\b", "close chrome"),
    (r"\bcalculator kholo\b", "open calculator"),
    (r"\bcalculator band karo\b", "close calculator"),
    (r"\bcalculator bandh karo\b", "close calculator"),
    (r"\bnotepad kholo\b", "open notepad"),
    (r"\bnotepad band karo\b", "close notepad"),
    (r"\bnotepad bandh karo\b", "close notepad"),
    (r"\bedge band karo\b", "close edge"),
    (r"\bedge bandh karo\b", "close edge"),
    (r"\byoutube band karo\b", "close youtube"),
    (r"\byoutube bandh karo\b", "close youtube"),
    (r"\bwhatsapp band karo\b", "close whatsapp"),
    (r"\bwhatsapp bandh karo\b", "close whatsapp"),
    (r"\bwhatsapp kholo\b", "check whatsapp"),
    (r"\bmera naam kya hai\b", "what is my name"),
    (r"\btumhe kya yaad hai\b", "what do you remember"),
    (r"\byaad rakh\b", "remember"),
    (r"\bmujhe yaad dilana\b", "remind me to"),
    (r"\btask dikha\b", "show tasks"),
    (r"\btasks dikha\b", "show tasks"),
    (r"\breminders dikha\b", "show reminders"),
    (r"\bcalendar dikha\b", "upcoming events"),
    (r"\baaj ka agenda\b", "today agenda"),
    (r"\bkal ka agenda\b", "tomorrow agenda"),
    (r"\bemail status bata\b", "email status"),
    (r"\bmail status bata\b", "email status"),
    (r"\binbox dikha\b", "read emails"),
    (r"\bcontacts dikha\b", "show contacts"),
    (r"\bclipboard padho\b", "read clipboard"),
    (r"\bfinance bata\b", "finance summary"),
    (r"\bhealth bata\b", "health summary"),
    (r"\bscreenshot lo\b", "take screenshot"),
    (r"\bscreen padho\b", "read screen"),
    (r"\bsecurity status bata\b", "security status"),
    (r"\banalytics dikha\b", "analytics summary"),
    (r"\bsuggestion do\b", "smart suggestions"),
    (r"\bsuggestions do\b", "smart suggestions"),
    (r"\bsmart home status bata\b", "smart home status"),
    (r"\bcloud sync karo\b", "cloud sync now"),
    (r"\bmobile notification bhejo\b", "send mobile notification"),
    (r"\b(.+?)\s+band\s+karo\b", r"close \1"),
    (r"\b(.+?)\s+band\s+kar\b", r"close \1"),
    (r"\b(.+?)\s+bandh\s+karo\b", r"close \1"),
    (r"\b(.+?)\s+bandh\s+kar\b", r"close \1"),
    (r"\b(.+?)\s+close\s+karo\b", r"close \1"),
    (r"\b(.+?)\s+close\s+kar\b", r"close \1"),
]

DEVANAGARI_REWRITES = [
    ("क्रोम खोलो", "open chrome"),
    ("व्हाट्सएप खोलो", "check whatsapp"),
    ("मेरा नाम क्या है", "what is my name"),
    ("क्या याद है", "what do you remember"),
    ("टास्क दिखाओ", "show tasks"),
    ("रिमाइंडर दिखाओ", "show reminders"),
    ("आज का एजेंडा", "today agenda"),
    ("कल का एजेंडा", "tomorrow agenda"),
    ("स्क्रीन पढ़ो", "read screen"),
    ("स्क्रीनशॉट लो", "take screenshot"),
    ("सुझाव दो", "smart suggestions"),
]


def has_non_ascii(text):
    return any(ord(char) > 127 for char in str(text))


def local_normalize(command):
    text = str(command).strip()
    lowered = text.lower()

    for needle, replacement in DEVANAGARI_REWRITES:
        if needle in text:
            return replacement

    normalized = lowered
    for pattern, replacement in LOCAL_REWRITES:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    normalized = " ".join(normalized.split()).strip()
    return normalized or text


def should_try_ai(original, normalized):
    if normalized != original.lower().strip():
        return False
    trigger_words = [
        "karo",
        "khol",
        "kholo",
        "dikha",
        "bata",
        "bhejo",
        "padho",
        "band",
        "bandh",
        "close kar",
        "yaad",
        "mujhe",
    ]
    lowered = original.lower()
    return has_non_ascii(original) or any(word in lowered for word in trigger_words)


def ai_normalize(command, client):
    if not client:
        return None

    prompt = f"""
Convert this user request into one concise English STAR assistant command.
Preserve names, numbers, emails, URLs, and message bodies.
If it is not an actionable command, return the original meaning in short English.
Reply with only the command text.

User request:
{command}
"""
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0,
            max_tokens=80,
            messages=[{"role": "user", "content": prompt}],
        )
        value = res.choices[0].message.content.strip()
        return value.strip('"')
    except Exception as exc:
        storage.add_log("warning", "language_ai_normalize_failed", str(exc))
        return None


def normalize_command(command, client=None):
    original = str(command).strip()
    local = local_normalize(original)
    if not should_try_ai(original, local):
        return local

    ai_value = ai_normalize(original, client)
    return ai_value or local
