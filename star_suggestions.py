import json

import star_analytics
import star_finance
import star_health
import star_productivity
import star_storage as storage


def dismissed_keys():
    with storage.connect() as conn:
        rows = conn.execute(
            "SELECT suggestion_key FROM suggestion_feedback WHERE action = 'dismiss'"
        ).fetchall()
    return {row["suggestion_key"] for row in rows}


def add_feedback(suggestion_key, action, details=None):
    clean_action = str(action).strip().lower()
    if clean_action not in {"accept", "dismiss", "snooze"}:
        clean_action = "accept"
    with storage.connect() as conn:
        conn.execute(
            """
            INSERT INTO suggestion_feedback(suggestion_key, action, details, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                str(suggestion_key).strip(),
                clean_action,
                json.dumps(details, ensure_ascii=False) if isinstance(details, (dict, list)) else details,
                storage.utc_now(),
            ),
        )
    storage.add_log("info", "suggestion_feedback_saved", {"key": suggestion_key, "action": clean_action})
    return True


def suggestion(key, title, command, reason, priority=5):
    return {
        "key": key,
        "title": title,
        "command": command,
        "reason": reason,
        "priority": priority,
    }


def command_pattern_suggestions():
    summary = star_analytics.command_summary()
    tools = summary.get("top_tools", [])
    items = []
    if not tools:
        items.append(
            suggestion(
                "try_daily_briefing",
                "Start with a daily briefing",
                "daily briefing",
                "You have not used STAR much yet, so a briefing is a good starting habit.",
                4,
            )
        )
        return items

    top = tools[0]
    if top["tool"] == "productivity":
        items.append(suggestion("review_tasks", "Review your open tasks", "show tasks", "Productivity is one of your top STAR uses.", 7))
    if top["tool"] == "git":
        items.append(suggestion("git_status", "Check repository status", "git status", "You use git commands often.", 6))
    if top["tool"] == "health":
        items.append(suggestion("health_summary", "Review today's health", "health summary", "You are tracking health logs.", 6))
    return items


def productivity_suggestions():
    items = []
    tasks = star_productivity.list_tasks(limit=5)
    reminders = star_productivity.due_reminders(limit=5)
    if tasks:
        items.append(suggestion("open_tasks", "You have open tasks", "show tasks", f"{len(tasks)} task(s) are waiting.", 8))
    if reminders:
        items.append(suggestion("due_reminders", "Reminders are due", "due reminders", f"{len(reminders)} reminder(s) are due now.", 9))
    return items


def finance_suggestions():
    data = star_finance.summary()
    items = []
    if data["expense"] > data["income"] and data["expense"] > 0:
        items.append(suggestion("finance_negative_balance", "Spending is above income", "finance summary", "This month's finance balance is negative.", 8))
    if data["expense_categories"]:
        top = data["expense_categories"][0]
        items.append(
            suggestion(
                "finance_top_category",
                f"Top spend: {top['category']}",
                "expense categories",
                f"{top['category']} is your largest expense category this month.",
                5,
            )
        )
    return items


def health_suggestions():
    data = star_health.summary()
    items = []
    if data["water_ml"] == 0:
        items.append(suggestion("log_water", "Log water intake", "log water 500 ml", "No water logged today.", 6))
    if data["workout_minutes"] == 0:
        items.append(suggestion("log_workout", "Log or plan movement", "log workout 20 minutes walk", "No workout logged today.", 4))
    return items


def error_suggestions():
    errors = star_analytics.recent_errors(limit=5)
    logs = errors.get("logs", [])
    if logs:
        return [suggestion("review_errors", "Review recent issues", "recent errors", f"{len(logs)} warning/error log(s) were found.", 6)]
    return []


def generate_suggestions(limit=10):
    keys_to_skip = dismissed_keys()
    suggestions = []
    for provider in [productivity_suggestions, health_suggestions, finance_suggestions, error_suggestions, command_pattern_suggestions]:
        suggestions.extend(provider())

    unique = {}
    for item in suggestions:
        if item["key"] not in keys_to_skip:
            unique[item["key"]] = item

    return sorted(unique.values(), key=lambda item: item["priority"], reverse=True)[: int(limit)]


def format_suggestions(items):
    if not items:
        return "No smart suggestions right now."
    parts = [f"{idx + 1}. {item['title']} - say: {item['command']}" for idx, item in enumerate(items[:5])]
    return "Smart suggestions: " + " ".join(parts)
