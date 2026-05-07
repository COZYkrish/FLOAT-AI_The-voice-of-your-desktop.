"""
Import Google Contacts CSV into FLOAT AI contacts.json.

Usage:
  1. Export contacts from https://contacts.google.com as Google CSV
  2. Save the CSV file as 'contacts.csv' in the FLOAT AI folder
  3. Run: python import_contacts.py
"""

import csv
import json
import re
from pathlib import Path

CSV_FILE = Path(__file__).parent / "contacts.csv"
CONTACTS_FILE = Path(__file__).parent / "contacts.json"


def clean_phone(phone: str) -> str:
    """Normalize phone number to +XXXXXXXXXXX format."""
    phone = phone.strip()
    # Remove spaces, dashes, parentheses
    phone = re.sub(r"[\s\-\(\)]", "", phone)
    # Add +91 if no country code (Indian numbers)
    if phone and not phone.startswith("+"):
        if phone.startswith("0"):
            phone = phone[1:]  # Remove leading 0
        phone = "+91" + phone
    return phone


def import_contacts():
    if not CSV_FILE.exists():
        print(f"❌ File not found: {CSV_FILE}")
        print("   Please export your contacts from https://contacts.google.com")
        print("   as Google CSV and save it here as 'contacts.csv'")
        return

    # Load existing contacts
    existing = {}
    if CONTACTS_FILE.exists():
        with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)

    imported = 0
    skipped = 0

    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Google CSV has: "First Name", "Last Name", "Phone 1 - Value", etc.
            first = row.get("First Name", "").strip()
            last = row.get("Last Name", "").strip()
            phone = row.get("Phone 1 - Value", "").strip()

            if not first or not phone:
                skipped += 1
                continue

            # Build the contact name (lowercase for lookup)
            name = first.lower()
            full_name = f"{first} {last}".strip().lower() if last else name

            clean = clean_phone(phone)
            if not re.match(r"^\+\d{7,15}$", clean):
                skipped += 1
                continue

            # Add both first name and full name as keys
            existing[name] = clean
            if full_name != name:
                existing[full_name] = clean

            imported += 1

    # Save
    with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"✅ Imported {imported} contacts into contacts.json")
    print(f"   Skipped {skipped} entries (no name or invalid phone)")
    print(f"   Total contacts: {len(existing)}")
    print(f"\n   You can now say: 'text Mom hello' or 'text John meeting at 5'")


if __name__ == "__main__":
    import_contacts()
