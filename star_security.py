import os
from pathlib import Path

import star_storage as storage


DEFAULT_MODE = "normal"
MODES = {"relaxed", "normal", "strict"}
SECRET_KEYS = [
    "GROQ_API_KEY",
    "PICOVOICE_ACCESS_KEY",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "EMAIL_ADDRESS",
    "EMAIL_APP_PASSWORD",
    "GMAIL_ADDRESS",
    "GMAIL_APP_PASSWORD",
    "HOME_ASSISTANT_URL",
    "HOME_ASSISTANT_TOKEN",
    "MOBILE_SHARED_SECRET",
    "CLOUD_SYNC_DIR",
]

RISKY_PATTERNS = {
    "power": ["shutdown", "restart pc", "reboot", "sleep pc", "lock pc"],
    "git_write": ["git commit", "git push", "git pull"],
    "messaging": ["send whatsapp", "whatsapp message to", "send message to"],
    "email": ["send email", "send mail", "delete email", "archive email"],
    "clipboard": ["paste text", "paste snippet"],
    "smart_home": ["smart home turn on", "smart home turn off"],
    "browser_download": ["download file"],
    "automation": ["run automations", "run due automations", "create workflow", "schedule command"],
    "memory_clear": ["clear memory", "clear my memory", "forget all memory"],
    "file_write": ["delete file", "move file", "copy file", "rename file"],
}


def get_mode():
    mode = storage.get_setting("security_mode", DEFAULT_MODE)
    return mode if mode in MODES else DEFAULT_MODE


def set_mode(mode):
    clean = str(mode).strip().lower()
    if clean not in MODES:
        return False
    storage.set_setting("security_mode", clean)
    audit("security_mode_changed", "info", {"mode": clean})
    return True


def classify_command(command, tool=None):
    text = str(command).lower().strip()
    matched = []

    for category, patterns in RISKY_PATTERNS.items():
        if any(pattern in text for pattern in patterns):
            matched.append(category)

    if not matched:
        return {"risk": "safe", "categories": [], "requires_confirmation": False}

    mode = get_mode()
    if mode == "relaxed":
        requires_confirmation = any(category in {"power", "git_write", "file_write", "memory_clear", "email", "clipboard", "smart_home"} for category in matched)
    elif mode == "strict":
        requires_confirmation = True
    else:
        requires_confirmation = any(
            category in {"power", "git_write", "messaging", "email", "clipboard", "smart_home", "browser_download", "automation", "memory_clear", "file_write"}
            for category in matched
        )

    return {
        "risk": "risky" if requires_confirmation else "medium",
        "categories": matched,
        "requires_confirmation": requires_confirmation,
    }


def audit(event, level="info", details=None):
    storage.add_log(level, f"security_{event}", details)


def env_health():
    return {
        key: {
            "configured": bool(os.getenv(key)),
            "value": "configured" if os.getenv(key) else "missing",
        }
        for key in SECRET_KEYS
    }


def project_privacy_status(base_dir):
    base = Path(base_dir)
    sensitive = [".env", "star.db", "star_memory.json"]
    return {
        item: {
            "exists": (base / item).exists(),
            "should_be_ignored": True,
        }
        for item in sensitive
    }


def security_status(base_dir):
    return {
        "mode": get_mode(),
        "env": env_health(),
        "privacy_files": project_privacy_status(base_dir),
    }


def format_security_status(status):
    configured = [key for key, value in status["env"].items() if value["configured"]]
    missing = [key for key, value in status["env"].items() if not value["configured"]]
    return (
        f"Security mode is {status['mode']}. "
        f"Configured secrets: {len(configured)}. Missing optional secrets: {len(missing)}."
    )
