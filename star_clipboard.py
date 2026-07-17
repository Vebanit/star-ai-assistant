import subprocess

import pyautogui

import star_storage as storage


def get_text():
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Could not read clipboard.")
    return result.stdout.rstrip("\r\n")


def set_text(text):
    value = str(text)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "$value = [Console]::In.ReadToEnd(); Set-Clipboard -Value $value"],
        input=value,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Could not set clipboard.")
    storage.add_log("info", "clipboard_set", {"chars": len(value)})
    return {"status": "copied", "chars": len(value)}


def paste_text(text):
    set_text(text)
    pyautogui.hotkey("ctrl", "v")
    storage.add_log("info", "clipboard_pasted", {"chars": len(str(text))})
    return {"status": "pasted", "chars": len(str(text))}


def add_snippet(name, content, tags=None):
    clean_name = str(name).strip()
    clean_content = str(content).strip()
    if not clean_name or not clean_content:
        return None

    current = storage.utc_now()
    with storage.connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO snippets(name, content, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (clean_name, clean_content, tags, current, current),
        )

    storage.add_log("info", "snippet_created", {"id": cur.lastrowid, "name": clean_name})
    return cur.lastrowid


def update_snippet(snippet_id, name=None, content=None, tags=None):
    fields = {}
    if name is not None:
        fields["name"] = str(name).strip()
    if content is not None:
        fields["content"] = str(content).strip()
    if tags is not None:
        fields["tags"] = str(tags).strip() or None
    if not fields:
        return False

    fields["updated_at"] = storage.utc_now()
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [int(snippet_id)]
    with storage.connect() as conn:
        cur = conn.execute(f"UPDATE snippets SET {assignments} WHERE id = ?", values)

    updated = cur.rowcount > 0
    if updated:
        storage.add_log("info", "snippet_updated", {"id": int(snippet_id)})
    return updated


def list_snippets(limit=50):
    with storage.connect() as conn:
        rows = conn.execute("SELECT * FROM snippets ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def search_snippets(query, limit=20):
    pattern = f"%{str(query).lower().strip()}%"
    with storage.connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM snippets
            WHERE lower(name) LIKE ? OR lower(content) LIKE ? OR lower(tags) LIKE ?
            ORDER BY id DESC LIMIT ?
            """,
            (pattern, pattern, pattern, int(limit)),
        ).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def get_snippet(snippet_id):
    with storage.connect() as conn:
        row = conn.execute("SELECT * FROM snippets WHERE id = ?", (int(snippet_id),)).fetchone()
    return storage.row_to_dict(row)


def delete_snippet(snippet_id):
    with storage.connect() as conn:
        cur = conn.execute("DELETE FROM snippets WHERE id = ?", (int(snippet_id),))
    deleted = cur.rowcount > 0
    if deleted:
        storage.add_log("info", "snippet_deleted", {"id": int(snippet_id)})
    return deleted


def format_clipboard_text(text, limit=600):
    if not text:
        return "Clipboard is empty."
    preview = text[:limit]
    suffix = "..." if len(text) > limit else ""
    return f"Clipboard has {len(text)} characters: {preview}{suffix}"


def format_snippets(snippets):
    if not snippets:
        return "No snippets found."
    parts = [f"{item['id']}: {item['name']} ({len(item['content'])} chars)" for item in snippets[:8]]
    return "Snippets: " + ", ".join(parts) + "."
