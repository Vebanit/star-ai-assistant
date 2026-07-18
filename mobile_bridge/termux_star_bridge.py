#!/usr/bin/env python3
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request


BASE_URL = os.getenv("STAR_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
SECRET = os.getenv("MOBILE_SHARED_SECRET", "")
DEVICE_ID = os.getenv("STAR_DEVICE_ID") or socket.gethostname() or "android_phone"
DEVICE_NAME = os.getenv("STAR_DEVICE_NAME") or DEVICE_ID
POLL_SECONDS = float(os.getenv("STAR_POLL_SECONDS", "2"))

CAPABILITIES = [
    "notify",
    "speak",
    "vibrate",
    "open_url",
    "share_text",
    "call_intent",
    "sms_intent",
    "battery",
]


def with_secret(params=None):
    final = dict(params or {})
    if SECRET:
        final["secret"] = SECRET
    return final


def request_json(method, path, params=None, timeout=20):
    query = urllib.parse.urlencode(with_secret(params), doseq=True)
    url = f"{BASE_URL}{path}"
    if query:
        url = f"{url}?{query}"
    data = b"" if method.upper() == "POST" else None
    request = urllib.request.Request(url, data=data, method=method.upper())
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def command_exists(command):
    return shutil.which(command) is not None


def run_command(args, timeout=20):
    if not command_exists(args[0]):
        return {"status": "skipped", "message": f"{args[0]} not installed"}
    completed = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    return {
        "status": "done" if completed.returncode == 0 else "error",
        "code": completed.returncode,
        "stdout": completed.stdout[-500:],
        "stderr": completed.stderr[-500:],
    }


def safe_url(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if ":" not in text and "." in text:
        return "https://" + text
    return text


def execute_action(action):
    kind = action.get("action")
    payload = action.get("payload") or {}

    if kind == "notify":
        title = str(payload.get("title") or "STAR")
        body = str(payload.get("body") or "")
        return run_command(["termux-notification", "--title", title, "--content", body])

    if kind == "speak":
        text = str(payload.get("text") or "")
        return run_command(["termux-tts-speak", text])

    if kind == "vibrate":
        duration = str(int(payload.get("duration_ms") or 700))
        return run_command(["termux-vibrate", "-d", duration])

    if kind == "open_url":
        url = safe_url(payload.get("url"))
        if not url:
            return {"status": "error", "message": "missing url"}
        return run_command(["termux-open-url", url])

    if kind == "share_text":
        text = str(payload.get("text") or "")
        if not text:
            return {"status": "error", "message": "missing text"}
        return run_command(["termux-share", "-a", "send", text])

    if kind == "call_intent":
        number = urllib.parse.quote(str(payload.get("number") or ""))
        if not number:
            return {"status": "error", "message": "missing number"}
        return run_command(["termux-open-url", f"tel:{number}"])

    if kind == "sms_intent":
        number = urllib.parse.quote(str(payload.get("number") or ""))
        body = urllib.parse.quote(str(payload.get("body") or ""))
        if not number:
            return {"status": "error", "message": "missing number"}
        return run_command(["termux-open-url", f"sms:{number}?body={body}"])

    if kind == "battery":
        return run_command(["termux-battery-status"])

    return {"status": "skipped", "message": f"unknown action {kind}"}


def register():
    return request_json(
        "POST",
        "/mobile/devices/register",
        {
            "device_id": DEVICE_ID,
            "name": DEVICE_NAME,
            "platform": "termux_android",
            "capabilities": json.dumps(CAPABILITIES),
        },
    )


def complete(action_id, result):
    status = result.get("status") or "done"
    if status not in {"done", "error", "skipped"}:
        status = "done"
    return request_json(
        "POST",
        f"/mobile/actions/{action_id}/complete",
        {
            "device_id": DEVICE_ID,
            "status": status,
            "result": json.dumps(result),
        },
    )


def loop():
    print(f"STAR Termux bridge connecting to {BASE_URL}")
    registered = register()
    if not registered.get("authorized"):
        raise SystemExit(f"Registration failed: {registered}")
    print(f"Registered phone bridge as {DEVICE_ID}")

    while True:
        try:
            pulled = request_json("GET", "/mobile/actions/pull", {"device_id": DEVICE_ID, "limit": 5})
            if not pulled.get("authorized"):
                print("Pull failed:", pulled)
                time.sleep(POLL_SECONDS)
                continue
            for action in pulled.get("actions", []):
                print(f"Running action #{action['id']}: {action.get('action')}")
                result = execute_action(action)
                complete(action["id"], result)
        except KeyboardInterrupt:
            print("Stopping STAR Termux bridge.")
            return
        except Exception as exc:
            print("Bridge error:", exc, file=sys.stderr)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    loop()
