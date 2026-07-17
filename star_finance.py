import datetime
import re

import star_storage as storage


DEFAULT_CURRENCY = "INR"


def now():
    return datetime.datetime.now().replace(microsecond=0)


def iso(dt):
    return dt.replace(microsecond=0).isoformat()


def month_range(reference=None):
    base = reference or now()
    start = base.replace(day=1, hour=0, minute=0, second=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def parse_amount(text):
    match = re.search(r"(?:rs\.?|inr|₹)?\s*(\d+(?:,\d{2,3})*(?:\.\d+)?)", str(text), flags=re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def parse_category(text, default="general"):
    raw = str(text)
    lower = raw.lower()
    for marker in [" category ", " for ", " on "]:
        if marker in lower:
            index = lower.index(marker)
            category = raw[index + len(marker):].strip()
            category = re.split(r"\s+(note|because|as)\s+", category, flags=re.IGNORECASE)[0].strip()
            return storage.normalize_key(category) or default
    return default


def parse_note(text):
    raw = str(text)
    lower = raw.lower()
    for marker in [" note ", " because ", " as "]:
        if marker in lower:
            index = lower.index(marker)
            return raw[index + len(marker):].strip()
    return None


def add_transaction(kind, amount, category="general", note=None, happened_at=None, currency=DEFAULT_CURRENCY):
    clean_kind = str(kind).lower().strip()
    if clean_kind not in {"expense", "income"}:
        return None
    value = float(amount)
    if value <= 0:
        return None

    happened = happened_at or now()
    clean_category = storage.normalize_key(category or "general") or "general"
    with storage.connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO finance_transactions(kind, amount, category, note, currency, happened_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (clean_kind, value, clean_category, note, currency or DEFAULT_CURRENCY, iso(happened), storage.utc_now()),
        )

    storage.add_log("info", "finance_transaction_created", {"id": cur.lastrowid, "kind": clean_kind, "amount": value})
    return cur.lastrowid


def create_from_text(kind, payload):
    amount = parse_amount(payload)
    if amount is None:
        return {"error": "Tell me the amount, like add expense 250 for food."}
    category = parse_category(payload)
    note = parse_note(payload)
    tx_id = add_transaction(kind, amount, category=category, note=note)
    return {"id": tx_id, "kind": kind, "amount": amount, "category": category, "note": note}


def list_transactions(limit=20, kind=None):
    with storage.connect() as conn:
        if kind in {"expense", "income"}:
            rows = conn.execute(
                "SELECT * FROM finance_transactions WHERE kind = ? ORDER BY happened_at DESC, id DESC LIMIT ?",
                (kind, int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM finance_transactions ORDER BY happened_at DESC, id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def transactions_between(start, end, kind=None, limit=200):
    with storage.connect() as conn:
        if kind in {"expense", "income"}:
            rows = conn.execute(
                """
                SELECT * FROM finance_transactions
                WHERE kind = ? AND happened_at >= ? AND happened_at < ?
                ORDER BY happened_at DESC, id DESC LIMIT ?
                """,
                (kind, iso(start), iso(end), int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM finance_transactions
                WHERE happened_at >= ? AND happened_at < ?
                ORDER BY happened_at DESC, id DESC LIMIT ?
                """,
                (iso(start), iso(end), int(limit)),
            ).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def summary(start=None, end=None):
    if start is None or end is None:
        start, end = month_range()
    with storage.connect() as conn:
        rows = conn.execute(
            """
            SELECT kind, COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count
            FROM finance_transactions
            WHERE happened_at >= ? AND happened_at < ?
            GROUP BY kind
            """,
            (iso(start), iso(end)),
        ).fetchall()
        categories = conn.execute(
            """
            SELECT category, COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count
            FROM finance_transactions
            WHERE kind = 'expense' AND happened_at >= ? AND happened_at < ?
            GROUP BY category
            ORDER BY total DESC
            """,
            (iso(start), iso(end)),
        ).fetchall()

    totals = {"income": 0.0, "expense": 0.0}
    counts = {"income": 0, "expense": 0}
    for row in rows:
        totals[row["kind"]] = float(row["total"] or 0)
        counts[row["kind"]] = int(row["count"] or 0)

    return {
        "start": iso(start),
        "end": iso(end),
        "income": round(totals["income"], 2),
        "expense": round(totals["expense"], 2),
        "balance": round(totals["income"] - totals["expense"], 2),
        "income_count": counts["income"],
        "expense_count": counts["expense"],
        "expense_categories": [storage.row_to_dict(row) for row in categories],
    }


def category_summary(limit=10):
    start, end = month_range()
    return summary(start, end)["expense_categories"][:limit]


def delete_transaction(transaction_id):
    with storage.connect() as conn:
        cur = conn.execute("DELETE FROM finance_transactions WHERE id = ?", (int(transaction_id),))
    deleted = cur.rowcount > 0
    if deleted:
        storage.add_log("info", "finance_transaction_deleted", {"id": int(transaction_id)})
    return deleted


def format_money(value, currency=DEFAULT_CURRENCY):
    amount = round(float(value or 0), 2)
    return f"{currency} {amount:g}"


def format_transactions(items):
    if not items:
        return "No finance transactions found."
    parts = []
    for item in items[:8]:
        note = f" - {item['note']}" if item.get("note") else ""
        parts.append(f"{item['id']}: {item['kind']} {format_money(item['amount'], item['currency'])} for {item['category']}{note}")
    return "Transactions: " + ", ".join(parts) + "."


def format_summary(data):
    top = data.get("expense_categories") or []
    top_text = ""
    if top:
        top_text = " Top expenses: " + ", ".join(f"{row['category']} {format_money(row['total'])}" for row in top[:3]) + "."
    return (
        f"This month income is {format_money(data['income'])}, expenses are {format_money(data['expense'])}, "
        f"balance is {format_money(data['balance'])}."
        f"{top_text}"
    )
