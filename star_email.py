import email
import imaplib
import os
import smtplib
import time
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime


DEFAULT_IMAP_HOST = "imap.gmail.com"
DEFAULT_IMAP_PORT = 993
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_TIMEOUT = 12
RETRYABLE_ERRORS = (
    TimeoutError,
    OSError,
    imaplib.IMAP4.abort,
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPConnectError,
)


def config():
    return {
        "address": os.getenv("EMAIL_ADDRESS") or os.getenv("GMAIL_ADDRESS"),
        "password": os.getenv("EMAIL_APP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD"),
        "imap_host": os.getenv("EMAIL_IMAP_HOST", DEFAULT_IMAP_HOST),
        "imap_port": int(os.getenv("EMAIL_IMAP_PORT", DEFAULT_IMAP_PORT)),
        "smtp_host": os.getenv("EMAIL_SMTP_HOST", DEFAULT_SMTP_HOST),
        "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", DEFAULT_SMTP_PORT)),
        "timeout": int(os.getenv("EMAIL_TIMEOUT_SECONDS", DEFAULT_TIMEOUT)),
    }


def is_configured():
    cfg = config()
    return bool(cfg["address"] and cfg["password"])


def status():
    cfg = config()
    return {
        "configured": is_configured(),
        "address_configured": bool(cfg["address"]),
        "password_configured": bool(cfg["password"]),
        "imap_host": cfg["imap_host"],
        "imap_port": cfg["imap_port"],
        "smtp_host": cfg["smtp_host"],
        "smtp_port": cfg["smtp_port"],
        "timeout": cfg["timeout"],
    }


def require_config():
    cfg = config()
    if not cfg["address"] or not cfg["password"]:
        raise RuntimeError("Email is not configured. Add EMAIL_ADDRESS and EMAIL_APP_PASSWORD to .env.")
    return cfg


def imap_connect(mailbox="INBOX"):
    cfg = require_config()
    client = imaplib.IMAP4_SSL(cfg["imap_host"], cfg["imap_port"], timeout=cfg["timeout"])
    client.login(cfg["address"], cfg["password"])
    client.select(mailbox)
    return client


def smtp_connect():
    cfg = require_config()
    client = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"], timeout=cfg["timeout"])
    client.starttls()
    client.login(cfg["address"], cfg["password"])
    return client


def with_retry(callback, attempts=2):
    last_error = None
    for attempt in range(max(1, attempts)):
        try:
            return callback()
        except RETRYABLE_ERRORS as exc:
            last_error = exc
            if attempt + 1 >= attempts:
                break
            time.sleep(1)
    raise last_error


def test_connection():
    if not is_configured():
        return {"configured": False, "imap": "missing_config", "smtp": "missing_config"}

    result = {"configured": True, "imap": "unknown", "smtp": "unknown"}
    try:
        client = with_retry(lambda: imap_connect())
        safe_logout(client)
        result["imap"] = "ok"
    except Exception as exc:
        result["imap"] = "error"
        result["imap_error"] = str(exc)[:300]

    try:
        client = with_retry(smtp_connect)
        client.quit()
        result["smtp"] = "ok"
    except Exception as exc:
        result["smtp"] = "error"
        result["smtp_error"] = str(exc)[:300]

    return result


def list_emails(limit=10, mailbox="INBOX", unread_only=False):
    client = with_retry(lambda: imap_connect(mailbox))
    try:
        criterion = "UNSEEN" if unread_only else "ALL"
        status_code, data = client.search(None, criterion)
        if status_code != "OK":
            return []

        ids = data[0].split()[-int(limit):]
        emails = []
        for message_id in reversed(ids):
            item = fetch_email_by_id(client, message_id)
            if item:
                emails.append(item)
        return emails
    finally:
        safe_logout(client)


def search_emails(query, limit=10, mailbox="INBOX"):
    client = with_retry(lambda: imap_connect(mailbox))
    try:
        safe_query = str(query).replace('"', "")
        status_code, data = client.search(None, "TEXT", f'"{safe_query}"')
        if status_code != "OK":
            return []

        ids = data[0].split()[-int(limit):]
        return [item for item in (fetch_email_by_id(client, message_id) for message_id in reversed(ids)) if item]
    finally:
        safe_logout(client)


def fetch_email_by_id(client, message_id):
    status_code, data = client.fetch(message_id, "(RFC822)")
    if status_code != "OK" or not data or not data[0]:
        return None

    raw = data[0][1]
    message = email.message_from_bytes(raw)
    body = extract_body(message)
    date = message.get("Date")
    parsed_date = None
    if date:
        try:
            parsed_date = parsedate_to_datetime(date).isoformat()
        except (TypeError, ValueError):
            parsed_date = date

    return {
        "id": message_id.decode() if isinstance(message_id, bytes) else str(message_id),
        "from": message.get("From", ""),
        "to": message.get("To", ""),
        "subject": decode_header_value(message.get("Subject", "")),
        "date": parsed_date,
        "snippet": " ".join(body.split())[:300],
        "body": body[:8000],
    }


def extract_body(message):
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        return ""

    payload = message.get_payload(decode=True)
    if not payload:
        return ""
    return payload.decode(message.get_content_charset() or "utf-8", errors="replace")


def decode_header_value(value):
    if not value:
        return ""
    decoded = decode_header(value)
    parts = []
    for chunk, encoding in decoded:
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(encoding or "utf-8", errors="replace"))
        else:
            parts.append(chunk)
    return "".join(parts)


def send_email(to, subject, body):
    cfg = require_config()
    _, address = parseaddr(str(to))
    if "@" not in address:
        raise ValueError("Email address is invalid.")
    message = EmailMessage()
    message["From"] = cfg["address"]
    message["To"] = address
    message["Subject"] = subject
    message.set_content(body)

    client = with_retry(smtp_connect)
    try:
        client.send_message(message)
    finally:
        client.quit()

    return {"status": "sent", "to": address, "subject": subject}


def archive_email(message_id, mailbox="INBOX"):
    client = with_retry(lambda: imap_connect(mailbox))
    try:
        client.store(str(message_id), "+FLAGS", "\\Seen")
        try:
            client.store(str(message_id), "+X-GM-LABELS", "\\All")
        except imaplib.IMAP4.error:
            pass
        client.store(str(message_id), "+FLAGS", "\\Deleted")
        client.expunge()
        return {"status": "archived", "id": str(message_id)}
    finally:
        safe_logout(client)


def delete_email(message_id, mailbox="INBOX"):
    client = with_retry(lambda: imap_connect(mailbox))
    try:
        client.store(str(message_id), "+FLAGS", "\\Deleted")
        client.expunge()
        return {"status": "deleted", "id": str(message_id)}
    finally:
        safe_logout(client)


def summarize_email_item(item):
    subject = item.get("subject") or "(no subject)"
    sender = item.get("from") or "unknown sender"
    snippet = item.get("snippet") or ""
    return f"From {sender}. Subject: {subject}. {snippet}"


def format_email_list(items):
    if not items:
        return "No emails found."
    parts = [f"{item['id']}: {item['subject']} from {item['from']}" for item in items[:5]]
    return "Emails: " + ", ".join(parts) + "."


def safe_logout(client):
    try:
        client.close()
    except Exception:
        pass
    try:
        client.logout()
    except Exception:
        pass
