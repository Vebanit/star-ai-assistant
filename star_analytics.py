from collections import Counter

import star_storage as storage
import star_finance


def command_summary():
    with storage.connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS count FROM commands").fetchone()["count"]
        ok = conn.execute("SELECT COUNT(*) AS count FROM commands WHERE status = 'ok'").fetchone()["count"]
        errors = conn.execute("SELECT COUNT(*) AS count FROM commands WHERE status != 'ok'").fetchone()["count"]
        rows = conn.execute("SELECT tool FROM commands").fetchall()

    tool_counts = Counter(row["tool"] or "none" for row in rows)
    success_rate = round((ok / total) * 100, 1) if total else 0

    return {
        "total_commands": total,
        "successful_commands": ok,
        "failed_commands": errors,
        "success_rate": success_rate,
        "top_tools": [{"tool": tool, "count": count} for tool, count in tool_counts.most_common(10)],
    }


def daily_commands(limit=14):
    with storage.connect() as conn:
        rows = conn.execute(
            """
            SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count
            FROM commands
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def tool_breakdown():
    with storage.connect() as conn:
        rows = conn.execute(
            """
            SELECT tool, status, COUNT(*) AS count
            FROM commands
            GROUP BY tool, status
            ORDER BY count DESC
            """
        ).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def recent_errors(limit=10):
    with storage.connect() as conn:
        command_rows = conn.execute(
            """
            SELECT command, tool, status, reply, created_at
            FROM commands
            WHERE status != 'ok'
            ORDER BY id DESC LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        log_rows = conn.execute(
            """
            SELECT level, event, details, created_at
            FROM logs
            WHERE level IN ('warning', 'error')
            ORDER BY id DESC LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

    return {
        "commands": [storage.row_to_dict(row) for row in command_rows],
        "logs": [storage.row_to_dict(row) for row in log_rows],
    }


def productivity_summary():
    with storage.connect() as conn:
        notes = conn.execute("SELECT COUNT(*) AS count FROM notes").fetchone()["count"]
        open_tasks = conn.execute("SELECT COUNT(*) AS count FROM tasks WHERE status = 'open'").fetchone()["count"]
        done_tasks = conn.execute("SELECT COUNT(*) AS count FROM tasks WHERE status = 'done'").fetchone()["count"]
        open_reminders = conn.execute("SELECT COUNT(*) AS count FROM reminders WHERE status = 'open'").fetchone()["count"]
        done_reminders = conn.execute("SELECT COUNT(*) AS count FROM reminders WHERE status = 'done'").fetchone()["count"]
        calendar_events = conn.execute("SELECT COUNT(*) AS count FROM calendar_events WHERE status = 'scheduled'").fetchone()["count"]
        finance_transactions = conn.execute("SELECT COUNT(*) AS count FROM finance_transactions").fetchone()["count"]
        active_automations = conn.execute("SELECT COUNT(*) AS count FROM automations WHERE status = 'active'").fetchone()["count"]
        automation_runs = conn.execute("SELECT COUNT(*) AS count FROM automation_runs").fetchone()["count"]

    return {
        "notes": notes,
        "open_tasks": open_tasks,
        "done_tasks": done_tasks,
        "open_reminders": open_reminders,
        "done_reminders": done_reminders,
        "calendar_events": calendar_events,
        "finance_transactions": finance_transactions,
        "active_automations": active_automations,
        "automation_runs": automation_runs,
    }


def memory_summary():
    with storage.connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS count FROM memory").fetchone()["count"]
        rows = conn.execute(
            "SELECT category, COUNT(*) AS count FROM memory GROUP BY category ORDER BY count DESC"
        ).fetchall()

    return {
        "total_memory_items": total,
        "categories": [storage.row_to_dict(row) for row in rows],
    }


def conversation_summary():
    with storage.connect() as conn:
        total = conn.execute("SELECT COUNT(*) AS count FROM conversations").fetchone()["count"]
        rows = conn.execute(
            "SELECT role, COUNT(*) AS count FROM conversations GROUP BY role ORDER BY count DESC"
        ).fetchall()

    return {
        "total_messages": total,
        "roles": [storage.row_to_dict(row) for row in rows],
    }


def full_summary():
    return {
        "commands": command_summary(),
        "daily_commands": daily_commands(),
        "tools": tool_breakdown(),
        "productivity": productivity_summary(),
        "memory": memory_summary(),
        "conversation": conversation_summary(),
        "finance": star_finance.summary(),
        "recent_errors": recent_errors(),
    }


def format_summary(summary):
    commands = summary["commands"]
    productivity = summary["productivity"]
    return (
        f"STAR has handled {commands['total_commands']} commands with "
        f"{commands['success_rate']} percent success. "
        f"There are {productivity['open_tasks']} open tasks, "
        f"{productivity['open_reminders']} open reminders, "
        f"{productivity['calendar_events']} calendar events, and "
        f"{productivity['active_automations']} active automations. "
        f"Finance balance this month is {star_finance.format_money(summary['finance']['balance'])}."
    )
