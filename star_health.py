import datetime
import re

import star_storage as storage


def now():
    return datetime.datetime.now().replace(microsecond=0)


def iso(dt):
    return dt.replace(microsecond=0).isoformat()


def day_range(day="today"):
    base = now()
    if day == "yesterday":
        base -= datetime.timedelta(days=1)
    start = base.replace(hour=0, minute=0, second=0)
    return start, start + datetime.timedelta(days=1)


def first_number(text):
    match = re.search(r"\b(\d+(?:\.\d+)?)\b", str(text))
    return float(match.group(1)) if match else None


def add_log(metric, value=None, unit=None, note=None, logged_at=None):
    clean_metric = storage.normalize_key(metric)
    if not clean_metric:
        return None

    current = logged_at or now()
    with storage.connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO health_logs(metric, value, unit, note, logged_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (clean_metric, value, unit, note, iso(current), storage.utc_now()),
        )

    storage.add_log("info", "health_log_created", {"id": cur.lastrowid, "metric": clean_metric})
    return cur.lastrowid


def log_water(text):
    amount = first_number(text)
    if amount is None:
        return {"error": "Tell me water amount, like log water 500 ml."}
    raw = str(text).lower()
    if "glass" in raw:
        value = amount * 250
    elif "liter" in raw or "litre" in raw:
        value = amount * 1000
    else:
        value = amount
    log_id = add_log("water_ml", value=value, unit="ml", note=None)
    return {"id": log_id, "metric": "water_ml", "value": value, "unit": "ml"}


def log_sleep(text):
    hours = first_number(text)
    if hours is None:
        return {"error": "Tell me sleep duration, like log sleep 7 hours."}
    log_id = add_log("sleep_hours", value=hours, unit="hours")
    return {"id": log_id, "metric": "sleep_hours", "value": hours, "unit": "hours"}


def log_workout(text):
    minutes = first_number(text)
    if minutes is None:
        return {"error": "Tell me workout duration, like log workout 30 minutes running."}
    note = re.sub(r"\b\d+(?:\.\d+)?\b", "", str(text), count=1).strip()
    note = re.sub(r"\b(minutes|minute|min|hours|hour|workout|exercise|log)\b", "", note, flags=re.IGNORECASE).strip()
    log_id = add_log("workout_minutes", value=minutes, unit="minutes", note=note or None)
    return {"id": log_id, "metric": "workout_minutes", "value": minutes, "unit": "minutes", "note": note or None}


def log_weight(text):
    weight = first_number(text)
    if weight is None:
        return {"error": "Tell me weight, like log weight 72 kg."}
    log_id = add_log("weight_kg", value=weight, unit="kg")
    return {"id": log_id, "metric": "weight_kg", "value": weight, "unit": "kg"}


def log_mood(text):
    payload = str(text).strip()
    value = first_number(payload)
    note = payload
    if value is not None:
        note = re.sub(r"\b\d+(?:\.\d+)?\b", "", payload, count=1).strip()
    note = re.sub(r"\b(log|mood|feeling|feel)\b", "", note, flags=re.IGNORECASE).strip()
    log_id = add_log("mood", value=value, unit="score" if value is not None else None, note=note or None)
    return {"id": log_id, "metric": "mood", "value": value, "unit": "score" if value is not None else None, "note": note or None}


def list_logs(limit=50, metric=None):
    with storage.connect() as conn:
        if metric:
            rows = conn.execute(
                "SELECT * FROM health_logs WHERE metric = ? ORDER BY logged_at DESC, id DESC LIMIT ?",
                (storage.normalize_key(metric), int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM health_logs ORDER BY logged_at DESC, id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def logs_between(start, end):
    with storage.connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM health_logs
            WHERE logged_at >= ? AND logged_at < ?
            ORDER BY logged_at DESC, id DESC
            """,
            (iso(start), iso(end)),
        ).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def summary(day="today"):
    start, end = day_range(day)
    rows = logs_between(start, end)
    totals = {"water_ml": 0, "sleep_hours": 0, "workout_minutes": 0}
    latest = {}
    for row in rows:
        metric = row["metric"]
        if metric in totals and row.get("value") is not None:
            totals[metric] += float(row["value"])
        if metric not in latest:
            latest[metric] = row
    return {
        "day": day,
        "start": iso(start),
        "end": iso(end),
        "total_logs": len(rows),
        "water_ml": round(totals["water_ml"], 1),
        "sleep_hours": round(totals["sleep_hours"], 1),
        "workout_minutes": round(totals["workout_minutes"], 1),
        "latest_mood": latest.get("mood"),
        "latest_weight": latest.get("weight_kg"),
        "logs": rows,
    }


def delete_log(log_id):
    with storage.connect() as conn:
        cur = conn.execute("DELETE FROM health_logs WHERE id = ?", (int(log_id),))
    deleted = cur.rowcount > 0
    if deleted:
        storage.add_log("info", "health_log_deleted", {"id": int(log_id)})
    return deleted


def format_value(item):
    if item.get("value") is None:
        return item.get("note") or "noted"
    unit = f" {item['unit']}" if item.get("unit") else ""
    return f"{item['value']:g}{unit}"


def format_logs(items):
    if not items:
        return "No health logs found."
    parts = []
    for item in items[:8]:
        note = f" - {item['note']}" if item.get("note") else ""
        parts.append(f"{item['id']}: {item['metric']} {format_value(item)}{note}")
    return "Health logs: " + ", ".join(parts) + "."


def format_summary(data):
    mood = data["latest_mood"]
    mood_text = ""
    if mood:
        mood_text = f" Mood: {format_value(mood)}."
    weight = data["latest_weight"]
    weight_text = ""
    if weight:
        weight_text = f" Latest weight: {format_value(weight)}."
    return (
        f"Today you logged {data['water_ml']:g} ml water, "
        f"{data['sleep_hours']:g} sleep hours, and "
        f"{data['workout_minutes']:g} workout minutes."
        f"{mood_text}{weight_text}"
    )
