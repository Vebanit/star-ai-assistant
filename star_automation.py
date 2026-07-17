import datetime
import json
import re

import star_storage as storage


def now():
    return datetime.datetime.now().replace(microsecond=0)


def iso(dt):
    return dt.replace(microsecond=0).isoformat()


def parse_schedule(text):
    raw = str(text).lower().strip()
    current = now()

    match = re.search(r"\bin\s+(\d+)\s+(minute|minutes|min|hour|hours|day|days)\b", raw)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("min"):
            return current + datetime.timedelta(minutes=amount)
        if unit.startswith("hour"):
            return current + datetime.timedelta(hours=amount)
        return current + datetime.timedelta(days=amount)

    if "tomorrow" in raw:
        base = current + datetime.timedelta(days=1)
    else:
        base = current

    time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", raw)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        suffix = time_match.group(3)
        if suffix == "pm" and hour != 12:
            hour += 12
        if suffix == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            due = base.replace(hour=hour, minute=minute, second=0)
            if "tomorrow" not in raw and due < current:
                due += datetime.timedelta(days=1)
            return due

    return None


def strip_schedule_phrase(text):
    cleaned = re.sub(r"\bin\s+\d+\s+(minute|minutes|min|hour|hours|day|days)\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(tomorrow|today)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bat\s+\d{1,2}(?::\d{2})?\s*(am|pm)?\b", "", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split()).strip()


def parse_interval(text):
    raw = str(text).lower()
    match = re.search(r"\bevery\s+(\d+)\s+(minute|minutes|min|hour|hours|day|days)\b", raw)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)
    if unit.startswith("min"):
        return amount
    if unit.startswith("hour"):
        return amount * 60
    return amount * 60 * 24


def create_command_automation(name, command, next_run_at, interval_minutes=None):
    clean_name = str(name).strip() or str(command).strip()[:60]
    clean_command = str(command).strip()
    if not clean_command or not next_run_at:
        return None

    with storage.connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO automations(name, kind, command, status, next_run_at, interval_minutes, created_at)
            VALUES (?, 'command', ?, 'active', ?, ?, ?)
            """,
            (clean_name, clean_command, iso(next_run_at), interval_minutes, storage.utc_now()),
        )

    storage.add_log("info", "automation_created", {"id": cur.lastrowid, "name": clean_name})
    return cur.lastrowid


def create_workflow(name, steps, next_run_at=None, interval_minutes=None):
    clean_steps = [str(step).strip() for step in steps if str(step).strip()]
    if not clean_steps:
        return None

    first_run = next_run_at or now()
    with storage.connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO automations(name, kind, steps_json, status, next_run_at, interval_minutes, created_at)
            VALUES (?, 'workflow', ?, 'active', ?, ?, ?)
            """,
            (str(name).strip() or "workflow", json.dumps(clean_steps), iso(first_run), interval_minutes, storage.utc_now()),
        )

    storage.add_log("info", "workflow_created", {"id": cur.lastrowid, "steps": len(clean_steps)})
    return cur.lastrowid


def list_automations(status="active", limit=50):
    with storage.connect() as conn:
        if status == "all":
            rows = conn.execute("SELECT * FROM automations ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM automations WHERE status = ? ORDER BY next_run_at ASC LIMIT ?",
                (status, int(limit)),
            ).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def get_automation(automation_id):
    with storage.connect() as conn:
        row = conn.execute("SELECT * FROM automations WHERE id = ?", (int(automation_id),)).fetchone()
    return storage.row_to_dict(row)


def due_automations(limit=20):
    current = iso(now())
    with storage.connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM automations
            WHERE status = 'active' AND next_run_at IS NOT NULL AND next_run_at <= ?
            ORDER BY next_run_at ASC LIMIT ?
            """,
            (current, int(limit)),
        ).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def delete_automation(automation_id):
    with storage.connect() as conn:
        cur = conn.execute("DELETE FROM automations WHERE id = ?", (int(automation_id),))
    deleted = cur.rowcount > 0
    if deleted:
        storage.add_log("info", "automation_deleted", {"id": int(automation_id)})
    return deleted


def pause_automation(automation_id):
    return set_status(automation_id, "paused")


def resume_automation(automation_id):
    return set_status(automation_id, "active")


def set_status(automation_id, status):
    with storage.connect() as conn:
        cur = conn.execute("UPDATE automations SET status = ? WHERE id = ?", (status, int(automation_id)))
    changed = cur.rowcount > 0
    if changed:
        storage.add_log("info", "automation_status_changed", {"id": int(automation_id), "status": status})
    return changed


def automation_steps(automation):
    if automation.get("kind") == "workflow":
        try:
            return json.loads(automation.get("steps_json") or "[]")
        except json.JSONDecodeError:
            return []
    return [automation.get("command")]


def mark_run_started(automation_id):
    current = storage.utc_now()
    with storage.connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO automation_runs(automation_id, status, started_at, finished_at)
            VALUES (?, 'running', ?, ?)
            """,
            (int(automation_id), current, current),
        )
    return cur.lastrowid


def finish_run(run_id, automation, status, output):
    finished = storage.utc_now()
    next_run_at = None
    if automation.get("interval_minutes") and status == "ok":
        next_run_at = iso(now() + datetime.timedelta(minutes=int(automation["interval_minutes"])))

    with storage.connect() as conn:
        conn.execute(
            "UPDATE automation_runs SET status = ?, output = ?, finished_at = ? WHERE id = ?",
            (status, str(output)[:4000], finished, int(run_id)),
        )
        if next_run_at:
            conn.execute(
                "UPDATE automations SET last_run_at = ?, next_run_at = ? WHERE id = ?",
                (finished, next_run_at, int(automation["id"])),
            )
        else:
            conn.execute(
                "UPDATE automations SET last_run_at = ?, status = 'done' WHERE id = ?",
                (finished, int(automation["id"])),
            )


def list_runs(automation_id=None, limit=50):
    with storage.connect() as conn:
        if automation_id:
            rows = conn.execute(
                "SELECT * FROM automation_runs WHERE automation_id = ? ORDER BY id DESC LIMIT ?",
                (int(automation_id), int(limit)),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM automation_runs ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def format_automations(items):
    if not items:
        return "No active automations."

    parts = []
    for item in items[:8]:
        label = item.get("command") or item.get("name")
        parts.append(f"{item['id']}: {label} at {item.get('next_run_at')}")
    return "Automations: " + ", ".join(parts) + "."
