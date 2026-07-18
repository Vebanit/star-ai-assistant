import re

import star_storage as storage


EXCITED_MARKERS = ["!", "wow", "yay", "awesome", "mast", "badhiya", "lets go", "chalo", "yess"]
FRUSTRATED_MARKERS = ["angry", "gussa", "frustrated", "kyu", "why", "nahi ho raha", "not working", "bekar"]
SAD_MARKERS = ["sad", "dukhi", "upset", "tired", "thak", "pareshan", "depressed"]
POLITE_MARKERS = ["please", "pls", "kripya", "kindly"]
HINGLISH_MARKERS = ["bhai", "karo", "kar", "kya", "hai", "nahi", "haan", "bata", "kholo", "band"]


def detect_emotion(text):
    lower = str(text or "").lower()
    if any(marker in lower for marker in EXCITED_MARKERS) or lower.count("!") >= 2:
        return "excited"
    if any(marker in lower for marker in FRUSTRATED_MARKERS):
        return "frustrated"
    if any(marker in lower for marker in SAD_MARKERS):
        return "sad"
    if any(marker in lower for marker in POLITE_MARKERS):
        return "polite"
    return "neutral"


def detect_language_hint(text):
    value = str(text or "")
    lower = value.lower()
    if re.search(r"[\u3040-\u30ff]", value):
        return "Japanese"
    if re.search(r"[\u4e00-\u9fff]", value):
        return "Chinese"
    if re.search(r"[\uac00-\ud7af]", value):
        return "Korean"
    if re.search(r"[\u0900-\u097f]", value):
        return "Hindi"
    if re.search(r"[\u0600-\u06ff]", value):
        return "Arabic/Urdu"
    if re.search(r"[\u0400-\u04ff]", value):
        return "Russian"
    if any(marker in lower for marker in HINGLISH_MARKERS):
        return "Hinglish"
    return "same language as the user"


def should_adapt(reply):
    text = str(reply or "").strip()
    if not text:
        return False
    if len(text) > 700:
        return False
    if "```" in text:
        return False
    if text.count("\n") > 6:
        return False
    return True


def fallback_adapt(reply, user_text):
    emotion = detect_emotion(user_text)
    hint = detect_language_hint(user_text)
    if hint == "Hinglish":
        if emotion == "excited":
            return f"Haan bhai! {reply}"
        if emotion == "frustrated":
            return f"Samjha bhai, {reply}"
        if emotion == "sad":
            return f"Aram se bhai, {reply}"
    return reply


def adapt_reply(reply, user_text, client=None):
    clean_reply = str(reply or "").strip()
    if not should_adapt(clean_reply):
        return clean_reply

    if not client:
        return fallback_adapt(clean_reply, user_text)

    language_hint = detect_language_hint(user_text)
    emotion = detect_emotion(user_text)
    prompt = f"""
Rewrite STAR's reply for the user.

Rules:
- Reply in the same language/script as the user's message. If the user uses Japanese, reply in Japanese. If Hinglish, reply in natural Hinglish.
- Match the user's emotional tone: {emotion}.
- Keep the meaning and facts exactly the same.
- Keep it short and natural.
- Do not add new claims.
- Do not mention translation, language detection, or emotion detection.

User message:
{user_text}

Detected language hint:
{language_hint}

STAR reply:
{clean_reply}
"""
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.35,
            max_tokens=140,
            messages=[{"role": "user", "content": prompt}],
        )
        adapted = res.choices[0].message.content.strip().strip('"')
        return adapted or fallback_adapt(clean_reply, user_text)
    except Exception as exc:
        storage.add_log("warning", "emotion_reply_adapt_failed", str(exc))
        return fallback_adapt(clean_reply, user_text)
