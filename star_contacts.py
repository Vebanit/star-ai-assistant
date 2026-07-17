import re

import star_storage as storage


EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_PATTERN = re.compile(r"\+?\d[\d\s().-]{6,}\d")


def clean_phone(value):
    if not value:
        return None
    cleaned = re.sub(r"[^\d+]", "", str(value))
    return cleaned or None


def add_contact(name, email=None, phone=None, company=None, notes=None):
    clean_name = str(name).strip()
    if not clean_name:
        return None

    current = storage.utc_now()
    with storage.connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO contacts(name, email, phone, company, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (clean_name, email, clean_phone(phone), company, notes, current, current),
        )

    storage.add_log("info", "contact_created", {"id": cur.lastrowid, "name": clean_name})
    return cur.lastrowid


def update_contact(contact_id, name=None, email=None, phone=None, company=None, notes=None):
    fields = {}
    if name is not None:
        fields["name"] = str(name).strip()
    if email is not None:
        fields["email"] = str(email).strip() or None
    if phone is not None:
        fields["phone"] = clean_phone(phone)
    if company is not None:
        fields["company"] = str(company).strip() or None
    if notes is not None:
        fields["notes"] = str(notes).strip() or None

    fields = {key: value for key, value in fields.items() if value is not None or key in {"email", "phone", "company", "notes"}}
    if not fields:
        return False

    fields["updated_at"] = storage.utc_now()
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [int(contact_id)]
    with storage.connect() as conn:
        cur = conn.execute(f"UPDATE contacts SET {assignments} WHERE id = ?", values)

    updated = cur.rowcount > 0
    if updated:
        storage.add_log("info", "contact_updated", {"id": int(contact_id)})
    return updated


def list_contacts(limit=50):
    with storage.connect() as conn:
        rows = conn.execute("SELECT * FROM contacts ORDER BY name COLLATE NOCASE ASC LIMIT ?", (int(limit),)).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def search_contacts(query, limit=10):
    pattern = f"%{str(query).lower().strip()}%"
    with storage.connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM contacts
            WHERE lower(name) LIKE ? OR lower(email) LIKE ? OR lower(phone) LIKE ? OR lower(company) LIKE ? OR lower(notes) LIKE ?
            ORDER BY name COLLATE NOCASE ASC LIMIT ?
            """,
            (pattern, pattern, pattern, pattern, pattern, int(limit)),
        ).fetchall()
    return [storage.row_to_dict(row) for row in rows]


def get_contact(contact_id):
    with storage.connect() as conn:
        row = conn.execute("SELECT * FROM contacts WHERE id = ?", (int(contact_id),)).fetchone()
    return storage.row_to_dict(row)


def find_one(query):
    matches = search_contacts(query, limit=1)
    return matches[0] if matches else None


def resolve_email(value):
    text = str(value).strip()
    if "@" in text:
        return text
    contact = find_one(text)
    if contact and contact.get("email"):
        return contact["email"]
    return None


def resolve_phone(value):
    text = str(value).strip()
    if any(char.isdigit() for char in text):
        return clean_phone(text)
    contact = find_one(text)
    if contact and contact.get("phone"):
        return contact["phone"]
    return None


def delete_contact(contact_id):
    with storage.connect() as conn:
        cur = conn.execute("DELETE FROM contacts WHERE id = ?", (int(contact_id),))
    deleted = cur.rowcount > 0
    if deleted:
        storage.add_log("info", "contact_deleted", {"id": int(contact_id)})
    return deleted


def parse_contact_payload(payload):
    text = str(payload).strip()
    email_match = EMAIL_PATTERN.search(text)
    phone_match = PHONE_PATTERN.search(text)
    email = email_match.group(0) if email_match else None
    phone = phone_match.group(0) if phone_match else None

    name_text = text
    if email:
        name_text = name_text.replace(email, " ")
    if phone:
        name_text = name_text.replace(phone, " ")
    name_text = re.sub(r"\b(email|mail|phone|mobile|number|contact|with)\b", " ", name_text, flags=re.IGNORECASE)
    name = " ".join(name_text.split()).strip()
    return {"name": name, "email": email, "phone": phone}


def format_contact(contact):
    if not contact:
        return "Contact not found."
    parts = [f"{contact['id']}: {contact['name']}"]
    if contact.get("email"):
        parts.append(f"email {contact['email']}")
    if contact.get("phone"):
        parts.append(f"phone {contact['phone']}")
    if contact.get("company"):
        parts.append(f"company {contact['company']}")
    return ", ".join(parts) + "."


def format_contacts(contacts):
    if not contacts:
        return "No contacts found."
    return "Contacts: " + " ".join(format_contact(contact) for contact in contacts[:6])
