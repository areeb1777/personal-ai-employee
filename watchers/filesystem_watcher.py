"""
filesystem_watcher.py — File System Watcher for AI Employee (Bronze Tier).

Monitors the /Inbox folder for newly dropped files and creates structured
.md action files in /Needs_Action for Claude Code to process.

Usage:
    python filesystem_watcher.py [--vault PATH] [--dry-run]

Dependencies:
    pip install watchdog
"""

import argparse
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Dry-run guard — set DRY_RUN=true in environment or pass --dry-run flag
# ---------------------------------------------------------------------------
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# Add parent directory so base_watcher can be imported
sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher  # noqa: E402

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except ImportError:
    print("ERROR: watchdog is not installed. Run: pip install watchdog")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Priority keyword detection
# ---------------------------------------------------------------------------
PRIORITY_KEYWORDS = [
    "urgent", "asap", "deadline", "overdue", "critical",
    "invoice", "payment", "help", "important",
]

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls",
    ".csv", ".txt", ".md", ".png", ".jpg", ".jpeg",
    ".mp3", ".mp4", ".zip",
}


def detect_priority(filename: str) -> str:
    """Return 'high' if filename contains a priority keyword, else 'normal'."""
    name_lower = filename.lower()
    for kw in PRIORITY_KEYWORDS:
        if kw in name_lower:
            return "high"
    return "normal"


def detect_file_type(path: Path) -> str:
    """Return a human-readable file category."""
    ext = path.suffix.lower()
    categories = {
        (".pdf", ".docx", ".doc"): "document",
        (".xlsx", ".xls", ".csv"): "spreadsheet",
        (".txt", ".md"): "text",
        (".png", ".jpg", ".jpeg"): "image",
        (".mp3", ".mp4"): "media",
        (".zip",): "archive",
    }
    for exts, category in categories.items():
        if ext in exts:
            return category
    return "unknown"


# ---------------------------------------------------------------------------
# Watchdog event handler
# ---------------------------------------------------------------------------
class InboxEventHandler(FileSystemEventHandler):
    """
    Handles file-system events in the /Inbox folder.
    On file creation, triggers the watcher to create an action file.
    """

    def __init__(self, watcher: "FilesystemWatcher"):
        super().__init__()
        self.watcher = watcher

    def on_created(self, event):
        if event.is_directory:
            return
        # Small delay to ensure file write is complete
        time.sleep(0.5)
        source = Path(event.src_path)
        # Skip hidden/temp files
        if source.name.startswith(".") or source.name.startswith("~"):
            return
        self.watcher.logger.info(f"New file detected in Inbox: {source.name}")
        self.watcher.create_action_file(source)


# ---------------------------------------------------------------------------
# Main watcher class
# ---------------------------------------------------------------------------
class FilesystemWatcher(BaseWatcher):
    """
    Watches /Inbox for new file drops and creates .md action files
    in /Needs_Action for Claude Code to process.
    """

    def __init__(self, vault_path: str):
        super().__init__(vault_path, check_interval=5)
        self.processed: set[str] = set()

    def check_for_updates(self) -> list:
        """
        Fallback polling: find files in /Inbox not yet processed.
        The primary detection is event-driven (via watchdog).
        """
        new_files = []
        for f in self.inbox.iterdir():
            if f.is_file() and f.name not in self.processed:
                if not f.name.startswith("."):
                    new_files.append(f)
        return new_files

    def create_action_file(self, source: Path) -> Path:
        """
        Copy the source file to /Needs_Action and create a companion .md
        with metadata and suggested actions.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_type = detect_file_type(source)
        priority = detect_priority(source.name)

        # Destination in Needs_Action
        dest_name = f"FILE_{timestamp}_{source.stem}{source.suffix}"
        dest = self.needs_action / dest_name
        md_path = self.needs_action / f"FILE_{timestamp}_{source.stem}.md"

        if DRY_RUN:
            self.logger.info(f"[DRY RUN] Would copy {source.name} → {dest.name}")
            self.logger.info(f"[DRY RUN] Would create {md_path.name}")
        else:
            shutil.copy2(source, dest)
            self.logger.info(f"Copied {source.name} → {dest.name}")

        # Always write the .md action file (even in dry-run, so Claude can act)
        md_content = f"""---
type: file_drop
source: {source.name}
file_type: {file_type}
size_bytes: {source.stat().st_size if source.exists() else 'unknown'}
received: {datetime.now().isoformat()}
priority: {priority}
status: pending
dry_run: {str(DRY_RUN).lower()}
---

## New File Received

**File:** `{source.name}`
**Type:** {file_type}
**Priority:** {priority}
**Received:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Suggested Actions

- [ ] Review file content
- [ ] Categorize and tag appropriately
- [ ] Determine if action is required
- [ ] Move to /Done when complete

## Notes

_Add any processing notes here._
"""
        md_path.write_text(md_content, encoding="utf-8")

        self.processed.add(source.name)
        self.log_event(
            "file_received",
            {
                "source_file": source.name,
                "file_type": file_type,
                "priority": priority,
                "action_file": md_path.name,
                "dry_run": DRY_RUN,
            },
        )
        return md_path

    def run(self):
        """Start event-driven watching via watchdog + fallback polling."""
        self.logger.info(f"Starting FilesystemWatcher — watching: {self.inbox}")
        if DRY_RUN:
            self.logger.warning("DRY_RUN=true — files will NOT be copied. Set DRY_RUN=false to enable.")

        # Kick off watchdog observer
        handler = InboxEventHandler(self)
        observer = Observer()
        observer.schedule(handler, str(self.inbox), recursive=False)
        observer.start()

        try:
            # Also do a startup scan for any files already in /Inbox
            existing = self.check_for_updates()
            if existing:
                self.logger.info(f"Processing {len(existing)} existing file(s) in Inbox on startup")
                for f in existing:
                    self.create_action_file(f)

            while True:
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            self.logger.info("Watcher stopped by user (Ctrl+C).")
        finally:
            observer.stop()
            observer.join()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AI Employee — File System Watcher")
    parser.add_argument(
        "--vault",
        default=str(Path(__file__).parent.parent),
        help="Path to the Obsidian vault (default: parent of watchers/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log intended actions without copying files",
    )
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        global DRY_RUN
        DRY_RUN = True

    watcher = FilesystemWatcher(vault_path=args.vault)
    watcher.run()


if __name__ == "__main__":
    main()
