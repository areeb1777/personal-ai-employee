"""
gmail_watcher.py — Gmail API Watcher for AI Employee (Silver Tier).

Polls Gmail via the official Gmail API for unread important emails and creates
structured .md action files in /Needs_Action for Claude Code to process.

Prerequisites (run ONCE before starting this watcher):
    python scripts/gmail_auth.py
    → Opens browser to authorize Gmail access
    → Creates token.json in the vault root

Usage:
    python watchers/gmail_watcher.py [--vault PATH] [--interval SECONDS] [--dry-run]

Environment variables (set in .env):
    VAULT_PATH            — Absolute path to vault (default: parent of watchers/)
    GMAIL_CHECK_INTERVAL  — Polling interval in seconds (default: 120)
    DRY_RUN               — Set "false" to enable file creation (default: "true")

Token files:
    credentials.json  — OAuth2 client secrets (from Google Cloud Console)
    token.json        — Auto-generated after running gmail_auth.py (in vault root)

Dependencies:
    pip install google-auth google-auth-oauthlib google-api-python-client python-dotenv
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths and config
# ---------------------------------------------------------------------------
WATCHER_DIR = Path(__file__).parent
VAULT_ROOT = WATCHER_DIR.parent

load_dotenv(dotenv_path=VAULT_ROOT / ".env")

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
DEFAULT_INTERVAL = int(os.getenv("GMAIL_CHECK_INTERVAL", "120"))

CREDENTIALS_FILE = VAULT_ROOT / "credentials.json"
TOKEN_FILE = VAULT_ROOT / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

# Processed IDs persist across restarts
PROCESSED_IDS_FILE = WATCHER_DIR / ".gmail_processed_ids.json"

# Priority keywords
PRIORITY_KEYWORDS = [
    "urgent", "asap", "deadline", "overdue", "critical",
    "invoice", "payment", "help", "important", "follow up",
]

# ---------------------------------------------------------------------------
# Import base watcher
# ---------------------------------------------------------------------------
sys.path.insert(0, str(WATCHER_DIR))
from base_watcher import BaseWatcher  # noqa: E402

# ---------------------------------------------------------------------------
# Google API imports
# ---------------------------------------------------------------------------
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print(
        "\nERROR: Google API libraries not installed.\n"
        "Run: pip install google-auth google-auth-oauthlib google-api-python-client\n"
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_processed_ids() -> set:
    if PROCESSED_IDS_FILE.exists():
        try:
            return set(json.loads(PROCESSED_IDS_FILE.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def save_processed_ids(ids: set):
    PROCESSED_IDS_FILE.write_text(json.dumps(list(ids)), encoding="utf-8")


def detect_priority(subject: str, snippet: str) -> str:
    text = (subject + " " + snippet).lower()
    for kw in PRIORITY_KEYWORDS:
        if kw in text:
            return "high"
    return "normal"


def get_header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def extract_plain_text(payload: dict) -> str:
    """Recursively extract plain text body from Gmail message payload."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    parts = payload.get("parts", [])
    for part in parts:
        text = extract_plain_text(part)
        if text:
            return text

    return ""


def sanitize_filename(text: str, max_len: int = 40) -> str:
    return re.sub(r"[^\w\-]", "_", text[:max_len]).strip("_")


# ---------------------------------------------------------------------------
# Gmail Watcher class
# ---------------------------------------------------------------------------
class GmailWatcher(BaseWatcher):
    """
    Polls Gmail API for unread emails every check_interval seconds.
    Creates .md action files in /Needs_Action for Claude to process.
    """

    def __init__(self, vault_path: str, check_interval: int = DEFAULT_INTERVAL):
        super().__init__(vault_path, check_interval=check_interval)
        self.processed_ids = load_processed_ids()
        self.service = self._build_service()

    def _build_service(self):
        """Load credentials and build the Gmail API service client."""
        if not CREDENTIALS_FILE.exists():
            self.logger.error(
                f"credentials.json not found at {CREDENTIALS_FILE}\n"
                "Run: python scripts/gmail_auth.py"
            )
            sys.exit(1)

        if not TOKEN_FILE.exists():
            self.logger.error(
                f"token.json not found at {TOKEN_FILE}\n"
                "Run: python scripts/gmail_auth.py"
            )
            sys.exit(1)

        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        # Refresh token if expired
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                self.logger.info("Refreshing expired Gmail token...")
                creds.refresh(Request())
                TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
                self.logger.info("Token refreshed and saved.")
            else:
                self.logger.error(
                    "Gmail token is invalid and cannot be refreshed.\n"
                    "Run: python scripts/gmail_auth.py"
                )
                sys.exit(1)

        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def check_for_updates(self) -> list:
        """
        Fetch unread emails from Gmail API.
        Returns a list of message dicts with full details.
        """
        try:
            # Query: unread, in inbox
            result = self.service.users().messages().list(
                userId="me",
                q="is:unread in:inbox",
                maxResults=20,
            ).execute()

            messages = result.get("messages", [])
            new_items = []

            for msg_ref in messages:
                msg_id = msg_ref["id"]
                if msg_id in self.processed_ids:
                    continue

                # Fetch full message details
                msg = self.service.users().messages().get(
                    userId="me",
                    id=msg_id,
                    format="full",
                ).execute()

                new_items.append(msg)

            return new_items

        except HttpError as e:
            self.logger.error(f"Gmail API error: {e}")
            if e.status_code == 401:
                self.logger.error("Token expired. Run: python scripts/gmail_auth.py")
            return []
        except Exception as e:
            self.logger.error(f"Gmail check failed: {e}", exc_info=True)
            return []

    def create_action_file(self, msg: dict) -> Path:
        """Create a .md action file in /Needs_Action for a new Gmail message."""
        msg_id = msg["id"]
        headers = msg.get("payload", {}).get("headers", [])

        subject = get_header(headers, "Subject") or "(No Subject)"
        from_header = get_header(headers, "From") or "Unknown"
        to_header = get_header(headers, "To") or ""
        date_str = get_header(headers, "Date") or ""
        snippet = msg.get("snippet", "")

        # Extract full body
        body_text = extract_plain_text(msg.get("payload", {}))
        body_preview = (body_text or snippet).strip()[:500]

        # Clean up body preview
        body_preview = body_preview.replace("\r\n", "\n").replace("\r", "\n")

        priority = detect_priority(subject, snippet)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_subject = sanitize_filename(subject)

        md_path = self.needs_action / f"EMAIL_{timestamp}_{safe_subject}.md"

        md_content = f"""---
type: email
email_id: {msg_id}
from: {from_header}
subject: {subject}
date: {date_str}
received: {datetime.now().isoformat()}
priority: {priority}
status: pending
source: gmail_watcher
dry_run: {str(DRY_RUN).lower()}
---

## New Email Received

**From:** {from_header}
**Subject:** {subject}
**Date:** {date_str}
**Priority:** {priority.upper()}

## Email Content

```
{body_preview}{"..." if len(body_preview) >= 500 else ""}
```

## Suggested Actions

- [ ] Review email content
- [ ] Determine if reply is required
- [ ] Draft reply via `/process-email` skill (requires approval before sending)
- [ ] Forward to relevant party if needed
- [ ] Archive once processed

## Notes

_Add processing notes here._
"""

        if DRY_RUN:
            self.logger.info(f"[DRY RUN] Would create: {md_path.name}")
        else:
            self.logger.info(f"Creating: {md_path.name}")

        md_path.write_text(md_content, encoding="utf-8")

        # Track as processed so we don't re-create on next poll
        self.processed_ids.add(msg_id)
        save_processed_ids(self.processed_ids)

        self.log_event(
            "email_received",
            {
                "email_id": msg_id,
                "from": from_header,
                "subject": subject,
                "priority": priority,
                "action_file": md_path.name,
                "dry_run": DRY_RUN,
            },
        )

        return md_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AI Employee — Gmail API Watcher")
    parser.add_argument(
        "--vault",
        default=str(VAULT_ROOT),
        help="Path to the Obsidian vault",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"Check interval in seconds (default: {DEFAULT_INTERVAL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log intended actions without writing files",
    )
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        global DRY_RUN
        DRY_RUN = True

    watcher = GmailWatcher(vault_path=args.vault, check_interval=args.interval)
    watcher.run()


if __name__ == "__main__":
    main()
