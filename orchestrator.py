"""
orchestrator.py — Silver Tier Orchestrator for AI Employee.

The Orchestrator is the master process that:
  1. Watches /Approved for files approved by the human
  2. Routes each approved file to the correct handler:
       - APPROVAL_send_email_*.md     → Email MCP server
       - LINKEDIN_POST_*.md           → LinkedIn poster
       - APPROVAL_*.md (generic)      → Triggers Claude triage skill
  3. Watches /Approved for newly approved actions and executes them
  4. Manages process health (restarts crashed watchers)
  5. Triggers Claude Code via scheduled tasks

Usage:
    python orchestrator.py [--vault PATH] [--dry-run]

Required environment variables:
    VAULT_PATH            — Absolute path to the vault (or use --vault flag)
    GMAIL_SMTP_USER       — For email dispatch
    GMAIL_SMTP_PASSWORD   — For email dispatch
    LINKEDIN_ACCESS_TOKEN — For LinkedIn posting

Optional:
    DRY_RUN=true          — Prevent all external actions (safe default)

Dependencies:
    pip install watchdog requests python-dotenv
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
_vault_default = Path(__file__).parent
load_dotenv(dotenv_path=_vault_default / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Orchestrator] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("orchestrator")

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    logger.error("watchdog not installed. Run: pip install watchdog")
    sys.exit(1)

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# ---------------------------------------------------------------------------
# Config: child processes to manage
# ---------------------------------------------------------------------------
WATCHER_PROCESSES = {
    "filesystem_watcher": "python watchers/filesystem_watcher.py",
    "gmail_watcher": "python watchers/gmail_watcher.py",
    "linkedin_watcher": "python watchers/linkedin_watcher.py",
}


# ---------------------------------------------------------------------------
# Log helper
# ---------------------------------------------------------------------------
def _log_event(vault_path: Path, action_type: str, details: dict):
    logs_dir = vault_path / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"{today}.json"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "actor": "orchestrator",
        **details,
    }
    existing = []
    if log_file.exists():
        try:
            existing = json.loads(log_file.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing.append(entry)
    log_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------
def handle_email_approval(approval_file: Path, vault_path: Path) -> bool:
    """
    Read an approved email approval file and send the email via SMTP.
    Expects the approval file to contain recipient, subject, and body.
    """
    content = approval_file.read_text(encoding="utf-8")

    to_match = re.search(r"^to:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
    subject_match = re.search(r"^subject:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)

    # Extract body between ## Email Body / ## Body section
    body_match = re.search(
        r"## (?:Email )?Body\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL | re.IGNORECASE
    )

    if not to_match:
        logger.error(f"No 'to:' field found in {approval_file.name}")
        return False

    to = to_match.group(1).strip()
    subject = subject_match.group(1).strip() if subject_match else "(No Subject)"
    body = body_match.group(1).strip() if body_match else content

    if DRY_RUN:
        logger.info(f"[DRY RUN] Would send email to {to}: {subject}")
        _move_to_done(approval_file, vault_path)
        _log_event(vault_path, "email_sent_dry_run", {"to": to, "subject": subject})
        return True

    # Call email MCP server via subprocess (or use smtplib directly)
    smtp_user = os.getenv("GMAIL_SMTP_USER", "")
    smtp_pass = os.getenv("GMAIL_SMTP_PASSWORD", "")

    if not smtp_user or not smtp_pass:
        logger.error("Email credentials not set — cannot send. Check .env")
        return False

    try:
        import smtplib
        import ssl
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        msg = MIMEMultipart("alternative")
        msg["From"] = smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        smtp_host = os.getenv("GMAIL_SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("GMAIL_SMTP_PORT", "587"))

        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to], msg.as_string())

        logger.info(f"Email sent to {to}: {subject}")
        _move_to_done(approval_file, vault_path)
        _log_event(vault_path, "email_sent", {
            "to": to,
            "subject": subject,
            "approval_file": approval_file.name,
        })
        return True

    except Exception as e:
        logger.error(f"Email send failed: {e}")
        _log_event(vault_path, "email_send_failed", {
            "to": to,
            "subject": subject,
            "error": str(e),
        })
        return False


def handle_linkedin_approval(approval_file: Path, vault_path: Path) -> bool:
    """Route a LinkedIn post to the Selenium-based poster (no greenlet needed)."""
    sys.path.insert(0, str(vault_path / "watchers"))
    try:
        from linkedin_selenium_poster import post_from_file
        success = post_from_file(approval_file, dry_run=DRY_RUN)
        if success:
            _log_event(vault_path, "linkedin_post_dispatched", {
                "approval_file": approval_file.name,
                "method": "selenium",
            })
        return success
    except ImportError:
        logger.error("linkedin_selenium_poster not found — run: pip install selenium webdriver-manager")
        return False
    except Exception as e:
        logger.error(f"LinkedIn post failed: {e}")
        _log_event(vault_path, "linkedin_post_failed", {
            "approval_file": approval_file.name,
            "error": str(e),
        })
        return False


def handle_generic_approval(approval_file: Path, vault_path: Path) -> bool:
    """
    For generic approvals, trigger Claude Code triage skill to process.
    Logs and moves to done after logging (Claude will pick it up next cycle).
    """
    logger.info(f"Generic approval detected: {approval_file.name} — will be processed next Claude cycle")
    _log_event(vault_path, "generic_approval_noted", {
        "approval_file": approval_file.name,
    })
    return True


def _move_to_done(file: Path, vault_path: Path):
    done_dir = vault_path / "Done"
    done_dir.mkdir(parents=True, exist_ok=True)
    dest = done_dir / file.name
    if file.exists():
        file.rename(dest)
        logger.info(f"Moved {file.name} → /Done")


# ---------------------------------------------------------------------------
# Route approved files
# ---------------------------------------------------------------------------
def route_approved_file(approval_file: Path, vault_path: Path):
    """Determine what type of approval this is and call the right handler."""
    name = approval_file.name.lower()
    logger.info(f"Processing approved file: {approval_file.name}")

    if "send_email" in name or "email" in name and "linkedin" not in name:
        handle_email_approval(approval_file, vault_path)
    elif "linkedin" in name:
        handle_linkedin_approval(approval_file, vault_path)
    else:
        handle_generic_approval(approval_file, vault_path)


# ---------------------------------------------------------------------------
# Watchdog handler for /Approved folder
# ---------------------------------------------------------------------------
class ApprovedFolderHandler(FileSystemEventHandler):
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path

    def on_created(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if p.suffix.lower() == ".md":
            time.sleep(0.5)  # Wait for file write to complete
            route_approved_file(p, self.vault_path)

    def on_moved(self, event):
        """Handle files moved INTO /Approved (human approval action)."""
        if event.is_directory:
            return
        dest = Path(event.dest_path)
        approved_dir = self.vault_path / "Approved"
        if dest.parent == approved_dir and dest.suffix.lower() == ".md":
            time.sleep(0.5)
            route_approved_file(dest, self.vault_path)


# ---------------------------------------------------------------------------
# Process manager (simple watchdog for watcher sub-processes)
# ---------------------------------------------------------------------------
class ProcessManager:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.processes: dict[str, subprocess.Popen] = {}

    def start_watchers(self):
        """Start all watcher sub-processes."""
        for name, cmd in WATCHER_PROCESSES.items():
            self._start(name, cmd)

    def _start(self, name: str, cmd: str):
        """Start a named process."""
        try:
            parts = cmd.split()
            proc = subprocess.Popen(
                parts,
                cwd=str(self.vault_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.processes[name] = proc
            logger.info(f"Started {name} (PID: {proc.pid})")
            _log_event(self.vault_path, "process_started", {
                "process": name,
                "pid": proc.pid,
            })
        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")

    def check_and_restart(self):
        """Restart any crashed watcher processes."""
        for name, cmd in WATCHER_PROCESSES.items():
            proc = self.processes.get(name)
            if proc is None or proc.poll() is not None:
                exit_code = proc.poll() if proc else None
                logger.warning(f"{name} is not running (exit: {exit_code}). Restarting...")
                _log_event(self.vault_path, "process_restarted", {
                    "process": name,
                    "previous_exit_code": exit_code,
                })
                self._start(name, cmd)

    def stop_all(self):
        """Terminate all managed processes."""
        for name, proc in self.processes.items():
            if proc.poll() is None:
                proc.terminate()
                logger.info(f"Stopped {name}")


# ---------------------------------------------------------------------------
# Main orchestrator loop
# ---------------------------------------------------------------------------
def run_orchestrator(vault_path: Path, manage_watchers: bool = True):
    logger.info(f"Orchestrator starting — vault: {vault_path}")
    if DRY_RUN:
        logger.warning("DRY_RUN=true — no external actions will be executed")

    approved_dir = vault_path / "Approved"
    approved_dir.mkdir(parents=True, exist_ok=True)

    # Process any already-approved files on startup
    existing = list(approved_dir.glob("*.md"))
    if existing:
        logger.info(f"Processing {len(existing)} pre-existing approved file(s) on startup")
        for f in existing:
            route_approved_file(f, vault_path)

    # Start watchdog for /Approved folder
    handler = ApprovedFolderHandler(vault_path)
    observer = Observer()
    observer.schedule(handler, str(approved_dir), recursive=False)
    observer.start()
    logger.info(f"Watching /Approved for new approvals...")

    # Optionally start and manage watcher sub-processes
    proc_manager = None
    if manage_watchers:
        proc_manager = ProcessManager(vault_path)
        proc_manager.start_watchers()

    try:
        while True:
            # Health-check watcher processes every 60 seconds
            if proc_manager:
                proc_manager.check_and_restart()
            time.sleep(60)

    except KeyboardInterrupt:
        logger.info("Orchestrator stopped by user (Ctrl+C).")
    finally:
        observer.stop()
        observer.join()
        if proc_manager:
            proc_manager.stop_all()
        logger.info("Orchestrator shut down cleanly.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AI Employee — Silver Tier Orchestrator")
    parser.add_argument(
        "--vault",
        default=str(_vault_default),
        help="Path to the Obsidian vault",
    )
    parser.add_argument(
        "--no-watchers",
        action="store_true",
        help="Don't auto-start watcher sub-processes (manage them separately)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log intended actions without executing",
    )
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        global DRY_RUN
        DRY_RUN = True

    vault_path = Path(args.vault)
    if not vault_path.exists():
        logger.error(f"Vault path does not exist: {vault_path}")
        sys.exit(1)

    run_orchestrator(vault_path, manage_watchers=not args.no_watchers)


if __name__ == "__main__":
    main()
