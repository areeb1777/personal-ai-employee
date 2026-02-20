"""
base_watcher.py — Abstract base class for all AI Employee Watchers.

All watchers share the same loop: check for updates → create action files.
"""

import time
import logging
import sys
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime


# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)


class BaseWatcher(ABC):
    """
    Base class for all vault watchers.

    Subclasses implement check_for_updates() and create_action_file()
    to define what is watched and how action files are generated.
    """

    def __init__(self, vault_path: str, check_interval: int = 60):
        self.vault_path = Path(vault_path)
        self.inbox = self.vault_path / "Inbox"
        self.needs_action = self.vault_path / "Needs_Action"
        self.done = self.vault_path / "Done"
        self.logs = self.vault_path / "Logs"
        self.check_interval = check_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create required vault directories if they don't exist."""
        for folder in [self.inbox, self.needs_action, self.done, self.logs]:
            folder.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def check_for_updates(self) -> list:
        """Return a list of new items to process."""
        pass

    @abstractmethod
    def create_action_file(self, item) -> Path:
        """Create a .md action file in /Needs_Action for the given item."""
        pass

    def log_event(self, action_type: str, details: dict):
        """Write a structured audit log entry to /Logs/YYYY-MM-DD.json."""
        import json

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs / f"{today}.json"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "watcher": self.__class__.__name__,
            "action_type": action_type,
            **details,
        }

        # Append to today's log file
        existing = []
        if log_file.exists():
            try:
                existing = json.loads(log_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = []

        existing.append(entry)
        log_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    def run(self):
        """Main watcher loop — runs indefinitely until interrupted."""
        self.logger.info(f"Starting {self.__class__.__name__} (interval: {self.check_interval}s)")
        self.logger.info(f"Vault: {self.vault_path}")

        while True:
            try:
                items = self.check_for_updates()
                if items:
                    self.logger.info(f"Found {len(items)} new item(s) to process")
                for item in items:
                    action_file = self.create_action_file(item)
                    self.logger.info(f"Created action file: {action_file.name}")
            except KeyboardInterrupt:
                self.logger.info("Watcher stopped by user.")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
                self.log_event("watcher_error", {"error": str(e)})

            time.sleep(self.check_interval)
