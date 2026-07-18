import json
import os
import time
from pathlib import Path

import requests

import star_storage as storage

REQUEST_TIMEOUT = int(os.getenv("INTEGRATION_TIMEOUT_SECONDS", "10"))
ALLOWED_HOME_ASSISTANT_SERVICES = {
    "turn_on",
    "turn_off",
    "toggle",
    "open_cover",
    "close_cover",
    "set_temperature",
    "lock",
    "unlock",
}


def request_with_retry(method, url, attempts=2, **kwargs):
    last_error = None
    timeout = kwargs.pop("timeout", REQUEST_TIMEOUT)
    for attempt in range(max(1, attempts)):
        try:
            return requests.request(method, url, timeout=timeout, **kwargs)
        except requests.RequestException as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            time.sleep(1)
    raise last_error


def integration_status():
    return {
        "cloud": {
            "configured": bool(os.getenv("CLOUD_SYNC_DIR")),
            "sync_dir": os.getenv("CLOUD_SYNC_DIR") or "cloud_sync",
        },
        "mobile": {
            "configured": bool(os.getenv("MOBILE_SHARED_SECRET")),
            "queued_notifications": len(list_mobile_notifications(status="queued", limit=100)),
            "registered_devices": len(list_mobile_devices(limit=100)),
            "queued_actions": len(list_mobile_actions(status="queued", limit=100)),
            "auth": "shared_secret" if os.getenv("MOBILE_SHARED_SECRET") else "local_open",
        },
        "smart_home": {
            "configured": bool(os.getenv("HOME_ASSISTANT_URL") and os.getenv("HOME_ASSISTANT_TOKEN")),
            "provider": "home_assistant",
        },
    }


def save_integration(name, kind, status="planned", config=None):
    current = storage.utc_now()
    with storage.connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO integrations(name, kind, status, config_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(name).strip(),
                storage.normalize_key(kind),
                storage.normalize_key(status) or "planned",
                json.dumps(config or {}, ensure_ascii=False),
                current,
                current,
            ),
        )
    storage.add_log("info", "integration_saved", {"id": cur.lastrowid, "kind": kind})
    return cur.lastrowid


def list_integrations(kind=None, limit=50):
    with storage.connect() as conn:
        if kind:
            rows = conn.execute(
                "SELECT * FROM integrations WHERE kind = ? ORDER BY id DESC LIMIT ?",
                (storage.normalize_key(kind), int(limit)),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM integrations ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def delete_integration(integration_id):
    with storage.connect() as conn:
        cur = conn.execute("DELETE FROM integrations WHERE id = ?", (int(integration_id),))
    deleted = cur.rowcount > 0
    if deleted:
        storage.add_log("info", "integration_deleted", {"id": int(integration_id)})
    return deleted


def cloud_sync_snapshot(base_dir):
    sync_dir = Path(os.getenv("CLOUD_SYNC_DIR") or Path(base_dir) / "cloud_sync")
    sync_dir.mkdir(parents=True, exist_ok=True)
    stats = storage.get_stats()
    snapshot = {
        "created_at": storage.utc_now(),
        "stats": stats,
        "memory_keys": sorted(storage.get_memory_dict().keys()),
        "settings": {
            "database": str(storage.DB_FILE),
        },
    }
    path = sync_dir / "star_snapshot.json"
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)
    storage.add_log("info", "cloud_snapshot_written", {"path": str(path)})
    return {"status": "synced", "path": str(path), "stats": stats}


def queue_mobile_notification(title, body):
    clean_title = str(title).strip()
    clean_body = str(body).strip()
    if not clean_title or not clean_body:
        return None
    with storage.connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO mobile_notifications(title, body, created_at)
            VALUES (?, ?, ?)
            """,
            (clean_title, clean_body, storage.utc_now()),
        )
    storage.add_log("info", "mobile_notification_queued", {"id": cur.lastrowid})
    return cur.lastrowid


def validate_mobile_secret(secret=None):
    expected = os.getenv("MOBILE_SHARED_SECRET")
    if not expected:
        return True
    return str(secret or "") == expected


def mobile_pull(secret=None, limit=20):
    if not validate_mobile_secret(secret):
        storage.add_log("warning", "mobile_auth_failed")
        return {"authorized": False, "items": [], "error": "invalid_secret"}
    items = list_mobile_notifications(status="queued", limit=limit)
    return {
        "authorized": True,
        "items": items,
        "count": len(items),
        "status": integration_status()["mobile"],
    }


def parse_json_payload(value, fallback=None):
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return fallback if fallback is not None else {}
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback if fallback is not None else {}


def register_mobile_device(device_id, name="STAR Phone", platform="android", capabilities=None):
    clean_device_id = storage.normalize_key(device_id)
    clean_name = str(name or "STAR Phone").strip()[:80]
    clean_platform = storage.normalize_key(platform or "android") or "android"
    capability_data = parse_json_payload(capabilities, fallback=[])
    now = storage.utc_now()
    with storage.connect() as conn:
        conn.execute(
            """
            INSERT INTO mobile_devices(device_id, name, platform, capabilities_json, status, created_at, updated_at, last_seen_at)
            VALUES (?, ?, ?, ?, 'online', ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                name = excluded.name,
                platform = excluded.platform,
                capabilities_json = excluded.capabilities_json,
                status = 'online',
                updated_at = excluded.updated_at,
                last_seen_at = excluded.last_seen_at
            """,
            (clean_device_id, clean_name, clean_platform, json.dumps(capability_data, ensure_ascii=False), now, now, now),
        )
    storage.add_log("info", "mobile_device_registered", {"device_id": clean_device_id, "name": clean_name})
    return get_mobile_device(clean_device_id)


def get_mobile_device(device_id):
    with storage.connect() as conn:
        row = conn.execute(
            "SELECT * FROM mobile_devices WHERE device_id = ?",
            (storage.normalize_key(device_id),),
        ).fetchone()
    device = storage.row_to_dict(row)
    if device:
        device["capabilities"] = parse_json_payload(device.get("capabilities_json"), fallback=[])
    return device


def list_mobile_devices(limit=50):
    with storage.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM mobile_devices ORDER BY last_seen_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    devices = [storage.row_to_dict(row) for row in rows]
    for device in devices:
        device["capabilities"] = parse_json_payload(device.get("capabilities_json"), fallback=[])
    return devices


def touch_mobile_device(device_id, status="online"):
    clean_device_id = storage.normalize_key(device_id)
    with storage.connect() as conn:
        cur = conn.execute(
            """
            UPDATE mobile_devices
            SET status = ?, updated_at = ?, last_seen_at = ?
            WHERE device_id = ?
            """,
            (storage.normalize_key(status) or "online", storage.utc_now(), storage.utc_now(), clean_device_id),
        )
    return cur.rowcount > 0


def default_mobile_device_id():
    devices = list_mobile_devices(limit=1)
    return devices[0]["device_id"] if devices else None


def queue_mobile_action(action, payload=None, device_id=None):
    clean_action = storage.normalize_key(action)
    if not clean_action:
        return None
    target_device = storage.normalize_key(device_id) if device_id else default_mobile_device_id()
    payload_data = payload if isinstance(payload, dict) else parse_json_payload(payload, fallback={})
    with storage.connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO mobile_actions(device_id, action, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (target_device, clean_action, json.dumps(payload_data or {}, ensure_ascii=False), storage.utc_now()),
        )
    storage.add_log("info", "mobile_action_queued", {"id": cur.lastrowid, "device_id": target_device, "action": clean_action})
    return cur.lastrowid


def list_mobile_actions(status="queued", limit=50):
    with storage.connect() as conn:
        if status == "all":
            rows = conn.execute("SELECT * FROM mobile_actions ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM mobile_actions WHERE status = ? ORDER BY id DESC LIMIT ?",
                (storage.normalize_key(status), int(limit)),
            ).fetchall()
    actions = [storage.row_to_dict(row) for row in rows]
    for action in actions:
        action["payload"] = parse_json_payload(action.get("payload_json"), fallback={})
        action["result"] = parse_json_payload(action.get("result_json"), fallback={})
    return actions


def mobile_action_pull(device_id, secret=None, limit=5):
    if not validate_mobile_secret(secret):
        storage.add_log("warning", "mobile_auth_failed", {"endpoint": "actions_pull"})
        return {"authorized": False, "actions": [], "error": "invalid_secret"}
    clean_device_id = storage.normalize_key(device_id)
    if not clean_device_id:
        return {"authorized": False, "actions": [], "error": "missing_device_id"}
    touch_mobile_device(clean_device_id)
    now = storage.utc_now()
    with storage.connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM mobile_actions
            WHERE status = 'queued' AND (device_id IS NULL OR device_id = ?)
            ORDER BY id ASC
            LIMIT ?
            """,
            (clean_device_id, int(limit)),
        ).fetchall()
        action_ids = [row["id"] for row in rows]
        if action_ids:
            placeholders = ",".join("?" for _ in action_ids)
            conn.execute(
                f"UPDATE mobile_actions SET status = 'running', claimed_at = ? WHERE id IN ({placeholders})",
                (now, *action_ids),
            )
    actions = [storage.row_to_dict(row) for row in rows]
    for action in actions:
        action["payload"] = parse_json_payload(action.get("payload_json"), fallback={})
    return {"authorized": True, "device_id": clean_device_id, "actions": actions, "count": len(actions)}


def complete_mobile_action(action_id, device_id, status="done", result=None):
    clean_status = storage.normalize_key(status) or "done"
    if clean_status not in {"done", "error", "skipped"}:
        clean_status = "done"
    result_data = parse_json_payload(result, fallback={"message": str(result or "")})
    with storage.connect() as conn:
        cur = conn.execute(
            """
            UPDATE mobile_actions
            SET status = ?, result_json = ?, completed_at = ?
            WHERE id = ? AND (device_id IS NULL OR device_id = ?)
            """,
            (clean_status, json.dumps(result_data, ensure_ascii=False), storage.utc_now(), int(action_id), storage.normalize_key(device_id)),
        )
    if cur.rowcount:
        touch_mobile_device(device_id)
        storage.add_log("info", "mobile_action_completed", {"id": int(action_id), "status": clean_status})
    return cur.rowcount > 0


def format_mobile_bridge_status():
    devices = list_mobile_devices(limit=5)
    queued = list_mobile_actions(status="queued", limit=10)
    if not devices:
        return "No phone bridge connected yet. Start the Termux STAR bridge on your phone."
    device_text = ", ".join(f"{item['name']} seen {item['last_seen_at']}" for item in devices[:3])
    return f"Phone bridge: {len(devices)} device(s), {len(queued)} queued action(s). {device_text}."


def list_mobile_notifications(status="queued", limit=50):
    with storage.connect() as conn:
        if status == "all":
            rows = conn.execute("SELECT * FROM mobile_notifications ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM mobile_notifications WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, int(limit)),
            ).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def mark_mobile_notification_read(notification_id):
    with storage.connect() as conn:
        cur = conn.execute(
            "UPDATE mobile_notifications SET status = 'read', read_at = ? WHERE id = ?",
            (storage.utc_now(), int(notification_id)),
        )
    return cur.rowcount > 0


def delete_mobile_notification(notification_id):
    with storage.connect() as conn:
        cur = conn.execute("DELETE FROM mobile_notifications WHERE id = ?", (int(notification_id),))
    deleted = cur.rowcount > 0
    if deleted:
        storage.add_log("info", "mobile_notification_deleted", {"id": int(notification_id)})
    return deleted


def home_assistant_headers():
    token = os.getenv("HOME_ASSISTANT_TOKEN")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def home_assistant_status():
    url = os.getenv("HOME_ASSISTANT_URL")
    token = os.getenv("HOME_ASSISTANT_TOKEN")
    if not url or not token:
        return {"configured": False, "status": "not_configured"}
    try:
        response = request_with_retry("GET", url.rstrip("/") + "/api/", headers=home_assistant_headers(), timeout=8)
        return {"configured": True, "status": "ok" if response.ok else "error", "code": response.status_code, "body": response.text[:300]}
    except requests.RequestException as exc:
        storage.add_log("warning", "home_assistant_status_failed", str(exc))
        return {"configured": True, "status": "error", "error": str(exc)}


def call_home_assistant_service(domain, service, entity_id=None, data=None):
    url = os.getenv("HOME_ASSISTANT_URL")
    token = os.getenv("HOME_ASSISTANT_TOKEN")
    if not url or not token:
        return {"status": "not_configured"}
    clean_domain = storage.normalize_key(domain)
    clean_service = storage.normalize_key(service)
    if not clean_domain or clean_service not in ALLOWED_HOME_ASSISTANT_SERVICES:
        return {"status": "invalid_service", "domain": clean_domain, "service": clean_service}
    payload = data.copy() if isinstance(data, dict) else {}
    if entity_id:
        payload["entity_id"] = entity_id
    endpoint = f"{url.rstrip('/')}/api/services/{clean_domain}/{clean_service}"
    try:
        response = request_with_retry("POST", endpoint, headers=home_assistant_headers(), json=payload, timeout=10)
        return {"status": "ok" if response.ok else "error", "code": response.status_code, "body": response.text[:500]}
    except requests.RequestException as exc:
        storage.add_log("warning", "home_assistant_service_failed", str(exc))
        return {"status": "error", "error": str(exc)}


def format_status(status):
    cloud = "ready" if status["cloud"]["configured"] else "local folder"
    mobile = f"{status['mobile']['queued_notifications']} queued"
    smart = "ready" if status["smart_home"]["configured"] else "not configured"
    return f"Integrations: cloud {cloud}, mobile {mobile}, smart home {smart}."
