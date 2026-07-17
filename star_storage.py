import datetime
import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "star.db"


def utc_now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                source TEXT NOT NULL DEFAULT 'user',
                confidence REAL NOT NULL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                tool TEXT NOT NULL DEFAULT 'none',
                status TEXT NOT NULL DEFAULT 'ok',
                reply TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                event TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                priority TEXT NOT NULL DEFAULT 'normal',
                due_at TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                due_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                starts_at TEXT NOT NULL,
                ends_at TEXT,
                location TEXT,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'scheduled',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                company TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS automations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'command',
                command TEXT,
                steps_json TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                next_run_at TEXT,
                interval_minutes INTEGER,
                created_at TEXT NOT NULL,
                last_run_at TEXT
            );

            CREATE TABLE IF NOT EXISTS automation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                automation_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                output TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                FOREIGN KEY (automation_id) REFERENCES automations(id)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_memory_category ON memory(category);
            CREATE INDEX IF NOT EXISTS idx_conversations_created ON conversations(created_at);
            CREATE INDEX IF NOT EXISTS idx_commands_created ON commands(created_at);
            CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_notes_created ON notes(created_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_reminders_due ON reminders(due_at, status);
            CREATE INDEX IF NOT EXISTS idx_calendar_events_start ON calendar_events(starts_at, status);
            CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name);
            CREATE INDEX IF NOT EXISTS idx_snippets_name ON snippets(name);
            CREATE INDEX IF NOT EXISTS idx_automations_due ON automations(next_run_at, status);
            CREATE INDEX IF NOT EXISTS idx_automation_runs_id ON automation_runs(automation_id);
            """
        )


def row_to_dict(row):
    return dict(row) if row else None


def add_log(level, event, details=None):
    now = utc_now()
    details_text = json.dumps(details, ensure_ascii=False) if isinstance(details, (dict, list)) else details

    with connect() as conn:
        conn.execute(
            "INSERT INTO logs(level, event, details, created_at) VALUES (?, ?, ?, ?)",
            (level, event, details_text, now),
        )


def list_logs(limit=50):
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def set_memory(key, value, category="general", source="user", confidence=1.0):
    clean_key = normalize_key(key)
    clean_value = str(value).strip()
    if not clean_key or not clean_value:
        return False

    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO memory(key, value, category, source, confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                category = excluded.category,
                source = excluded.source,
                confidence = excluded.confidence,
                updated_at = excluded.updated_at
            """,
            (clean_key, clean_value, category, source, confidence, now, now),
        )

    add_log("info", "memory_saved", {"key": clean_key, "category": category, "source": source})
    return True


def get_memory(key):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM memory WHERE key = ?",
            (normalize_key(key),),
        ).fetchone()
    return row_to_dict(row)


def get_memory_value(key):
    memory = get_memory(key)
    return memory["value"] if memory else None


def get_memory_dict():
    with connect() as conn:
        rows = conn.execute("SELECT key, value FROM memory ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}


def list_memory(category=None, limit=100):
    with connect() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM memory WHERE category = ? ORDER BY updated_at DESC LIMIT ?",
                (category, int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memory ORDER BY updated_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()

    return [row_to_dict(row) for row in rows]


def search_memory(query, limit=10):
    pattern = f"%{query.lower().strip()}%"
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM memory
            WHERE lower(key) LIKE ? OR lower(value) LIKE ? OR lower(category) LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (pattern, pattern, pattern, int(limit)),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def delete_memory(key):
    clean_key = normalize_key(key)
    with connect() as conn:
        cur = conn.execute("DELETE FROM memory WHERE key = ?", (clean_key,))
    deleted = cur.rowcount > 0
    if deleted:
        add_log("info", "memory_deleted", {"key": clean_key})
    return deleted


def clear_memory():
    with connect() as conn:
        conn.execute("DELETE FROM memory")
    add_log("warning", "memory_cleared")


def add_conversation(role, content):
    clean_content = str(content).strip()
    if not clean_content:
        return

    with connect() as conn:
        conn.execute(
            "INSERT INTO conversations(role, content, created_at) VALUES (?, ?, ?)",
            (role, clean_content, utc_now()),
        )


def list_conversations(limit=20):
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def recent_conversation_text(limit=8):
    rows = list(reversed(list_conversations(limit)))
    return "\n".join(f"{row['role']}: {row['content']}" for row in rows)


def add_command(command, tool="none", status="ok", reply=None):
    with connect() as conn:
        conn.execute(
            "INSERT INTO commands(command, tool, status, reply, created_at) VALUES (?, ?, ?, ?, ?)",
            (command, tool, status, reply, utc_now()),
        )


def list_commands(limit=50):
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM commands ORDER BY id DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def get_stats():
    with connect() as conn:
        memory_count = conn.execute("SELECT COUNT(*) AS count FROM memory").fetchone()["count"]
        conversation_count = conn.execute("SELECT COUNT(*) AS count FROM conversations").fetchone()["count"]
        command_count = conn.execute("SELECT COUNT(*) AS count FROM commands").fetchone()["count"]
        log_count = conn.execute("SELECT COUNT(*) AS count FROM logs").fetchone()["count"]
        note_count = conn.execute("SELECT COUNT(*) AS count FROM notes").fetchone()["count"]
        open_task_count = conn.execute("SELECT COUNT(*) AS count FROM tasks WHERE status = 'open'").fetchone()["count"]
        open_reminder_count = conn.execute("SELECT COUNT(*) AS count FROM reminders WHERE status = 'open'").fetchone()["count"]
        upcoming_event_count = conn.execute("SELECT COUNT(*) AS count FROM calendar_events WHERE status = 'scheduled'").fetchone()["count"]
        contact_count = conn.execute("SELECT COUNT(*) AS count FROM contacts").fetchone()["count"]
        snippet_count = conn.execute("SELECT COUNT(*) AS count FROM snippets").fetchone()["count"]
        active_automation_count = conn.execute("SELECT COUNT(*) AS count FROM automations WHERE status = 'active'").fetchone()["count"]

    return {
        "memory_items": memory_count,
        "conversation_messages": conversation_count,
        "commands": command_count,
        "logs": log_count,
        "notes": note_count,
        "open_tasks": open_task_count,
        "open_reminders": open_reminder_count,
        "upcoming_calendar_events": upcoming_event_count,
        "contacts": contact_count,
        "snippets": snippet_count,
        "active_automations": active_automation_count,
    }


def get_setting(key, default=None):
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO settings(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, str(value), utc_now()),
        )
    add_log("info", "setting_updated", {"key": key})


def list_settings():
    with connect() as conn:
        rows = conn.execute("SELECT * FROM settings ORDER BY key").fetchall()
    return [row_to_dict(row) for row in rows]


def normalize_key(key):
    clean = str(key).strip().lower()
    clean = clean.replace(" ", "_").replace("-", "_")
    return "".join(char for char in clean if char.isalnum() or char == "_").strip("_")
