# messaging.py — FLOAT AI Desktop Assistant
# WhatsApp (Selenium via whatsapp.py) and Gmail (SMTP send + IMAP read)

import json
import re
import smtplib
import imaplib
import email
import logging
from difflib import get_close_matches
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, BASE_DIR, log
from brain import ask_groq

logger = logging.getLogger("FLOAT.messaging")

CONTACTS_FILE = BASE_DIR / "contacts.json"


# ─── Contact Lookup ───────────────────────────────────────────────────────────
def _load_contacts() -> dict:
    try:
        if CONTACTS_FILE.exists():
            with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Contacts load error: {e}")
    return {}


def _save_contacts(contacts: dict) -> None:
    try:
        with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(contacts, f, indent=2)
    except Exception as e:
        logger.error(f"Contacts save error: {e}")


def get_phone(name: str) -> str | None:
    """Look up a contact's phone number by name (case-insensitive, fuzzy)."""
    contacts = _load_contacts()
    key = name.lower().strip()

    # Exact match first
    if key in contacts:
        return contacts[key]

    # Fuzzy match
    names = list(contacts.keys())
    matches = get_close_matches(key, names, n=1, cutoff=0.6)
    if matches:
        logger.info(f"Fuzzy matched '{name}' → '{matches[0]}'")
        return contacts[matches[0]]

    return None


def add_contact(name: str, phone: str) -> str:
    """Add or update a contact in contacts.json."""
    # Validate phone number format
    clean_phone = phone.strip().replace(" ", "").replace("-", "")
    if not re.match(r"^\+\d{7,15}$", clean_phone):
        return (f"'{phone}' doesn't look like a valid phone number. "
                "Please include the country code, like +919876543210.")

    contacts = _load_contacts()
    contacts[name.lower().strip()] = clean_phone
    _save_contacts(contacts)
    return f"Saved {name}'s number as {clean_phone}."


def lookup_contact(name: str) -> str:
    """Look up a contact's number and return a spoken response."""
    phone = get_phone(name)
    if phone:
        return f"{name}'s number is {phone}."
    return f"I don't have a number saved for {name}."


─── WhatsApp (via Selenium) ─────────────────────────────────────────────────
def send_whatsapp(contact: str, message: str) -> str:
    """Send a WhatsApp message to a contact by name."""
    try:
        import whatsapp as wa

        phone = get_phone(contact)
        if not phone:
            return (f"I don't have {contact}'s number. "
                    f"You can add it by saying: save {contact}'s number as "
                    f"plus 91 and the number.")

        logger.info(f"Sending WhatsApp to {contact} ({phone})")
        return wa.send_message(phone, message)

    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return "I couldn't send the WhatsApp message."


def send_whatsapp_group(group_name: str, message: str) -> str:
    """Send a WhatsApp message to a group by name."""
    try:
        import whatsapp as wa
        logger.info(f"Sending group message to '{group_name}'")
        return wa.send_group_message(group_name, message)
    except Exception as e:
        logger.error(f"WhatsApp group send error: {e}")
        return f"I couldn't send the message to the {group_name} group."


# ─── Gmail SMTP — Send ────────────────────────────────────────────────────────
def send_email(to_address: str, subject: str, body: str) -> str:
    """Send an email via Gmail SMTP."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return "Email credentials are not configured in the .env file."
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = to_address
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, to_address, msg.as_string())

        result = f"Email sent to {to_address}."
        logger.info(result)
        return result
    except Exception as e:
        logger.error(f"Email send error: {e}")
        return "I couldn't send the email. Please check your Gmail app password."


# ─── Gmail IMAP — Read ────────────────────────────────────────────────────────
def read_emails(count: int = 5) -> str:
    """Fetch the last N unread emails and return a Groq-summarised string."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return "Email credentials are not configured."
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        status, data = mail.search(None, "UNSEEN")
        ids = data[0].split()
        if not ids:
            return "You have no unread emails."

        # Get last N
        fetch_ids = ids[-count:]
        summaries = []
        for eid in reversed(fetch_ids):
            _, msg_data = mail.fetch(eid, "(RFC822)")
            for part in msg_data:
                if isinstance(part, tuple):
                    msg = email.message_from_bytes(part[1])
                    sender  = msg.get("From", "Unknown")
                    subject = msg.get("Subject", "No subject")
                    body    = ""
                    if msg.is_multipart():
                        for p in msg.walk():
                            if p.get_content_type() == "text/plain":
                                body = p.get_payload(decode=True).decode(errors="replace")[:500]
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="replace")[:500]
                    summaries.append(f"From: {sender}\nSubject: {subject}\nBody: {body}")

        mail.logout()

        if not summaries:
            return "I couldn't retrieve your emails."

        combined = "\n\n---\n\n".join(summaries)
        prompt = (
            f"Summarise these {len(summaries)} emails in a few sentences for a voice assistant:\n\n"
            + combined
        )
        summary = ask_groq(prompt)
        return summary

    except Exception as e:
        logger.error(f"Email read error: {e}")
        return "I couldn't read your emails. Please check your credentials."
