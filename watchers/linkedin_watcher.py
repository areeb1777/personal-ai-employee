"""
linkedin_watcher.py — LinkedIn Watcher & Post Scheduler (Silver Tier).

Two responsibilities:
  1. CHECK: Polls /Pending_Approval for approved LinkedIn posts, then routes
     them to the LinkedIn poster (creates LINKEDIN_READY files).
  2. WATCH: Periodically calls LinkedIn API to check for new mentions/comments
     and creates Needs_Action files for Claude to respond to.

Usage:
    python linkedin_watcher.py [--vault PATH] [--interval SECONDS] [--dry-run]

Required environment variables:
    LINKEDIN_ACCESS_TOKEN   — OAuth2 access token (see README for setup)
    LINKEDIN_PERSON_URN     — Your LinkedIn person URN (urn:li:person:XXXXXX)

Optional:
    LINKEDIN_ORG_URN        — Organization URN for company page posts
    LINKEDIN_CHECK_INTERVAL — Polling interval in seconds (default: 300)

OAuth2 Setup:
    1. Create a LinkedIn Developer App at developer.linkedin.com
    2. Request 'w_member_social' and 'r_liteprofile' scopes
    3. Complete OAuth2 flow to get access token
    4. Store token in LINKEDIN_ACCESS_TOKEN env var
    (Token expires — see scripts/refresh_linkedin_token.py for refresh logic)

Dependencies:
    pip install requests python-dotenv
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).parent))
from base_watcher import BaseWatcher  # noqa: E402

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
PERSON_URN = os.getenv("LINKEDIN_PERSON_URN", "")
ORG_URN = os.getenv("LINKEDIN_ORG_URN", "")  # Optional: company page

DEFAULT_INTERVAL = int(os.getenv("LINKEDIN_CHECK_INTERVAL", "300"))

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }


class LinkedInWatcher(BaseWatcher):
    """
    Watches LinkedIn for mentions and routes approved posts for publishing.

    Flow for posting:
      1. Claude drafts a post via /draft-linkedin-post skill
      2. Approval file written to /Pending_Approval/
      3. Human approves (moves to /Approved/)
      4. Orchestrator calls LinkedInPoster.post_from_approval_file()
      5. Post goes live, approval file moved to /Done/

    Flow for monitoring:
      1. Every interval, check LinkedIn API for new notifications
      2. For mentions/comments: create Needs_Action file
      3. Claude triages and drafts response (requires approval before reply)
    """

    def __init__(self, vault_path: str, check_interval: int = DEFAULT_INTERVAL):
        super().__init__(vault_path, check_interval=check_interval)
        self.pending_approval = Path(vault_path) / "Pending_Approval"
        self.approved = Path(vault_path) / "Approved"
        self.done = Path(vault_path) / "Done"

        # Ensure directories exist
        for d in [self.pending_approval, self.approved, self.done]:
            d.mkdir(parents=True, exist_ok=True)

        if not ACCESS_TOKEN and not DRY_RUN:
            self.logger.warning(
                "LINKEDIN_ACCESS_TOKEN not set. Running in passive mode only."
            )

    # ------------------------------------------------------------------
    # Part 1: Check for approved posts ready to publish
    # ------------------------------------------------------------------
    def check_approved_posts(self) -> list:
        """Find approved LinkedIn post files ready to publish."""
        approved_posts = []
        if not self.approved.exists():
            return approved_posts

        for f in self.approved.glob("LINKEDIN_POST_*.md"):
            approved_posts.append(f)
        return approved_posts

    def publish_approved_post(self, approval_file: Path) -> bool:
        """
        Read an approved LinkedIn post file and publish it.
        Returns True on success, False on failure.
        """
        content = approval_file.read_text(encoding="utf-8")

        # Extract post content from the file
        post_text = self._extract_post_content(content)
        if not post_text:
            self.logger.error(f"Could not extract post content from {approval_file.name}")
            return False

        # Determine author URN (person or org)
        author_urn = ORG_URN if ORG_URN else PERSON_URN
        if not author_urn and not DRY_RUN:
            self.logger.error("LINKEDIN_PERSON_URN or LINKEDIN_ORG_URN must be set")
            return False

        if DRY_RUN:
            self.logger.info(f"[DRY RUN] Would post to LinkedIn:\n{post_text[:200]}...")
            self._move_to_done(approval_file, success=True, dry_run=True)
            return True

        # LinkedIn UGC Post API
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        try:
            resp = requests.post(
                f"{LINKEDIN_API_BASE}/ugcPosts",
                headers=_headers(),
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            post_id = resp.headers.get("X-RestLi-Id", "unknown")
            self.logger.info(f"Posted to LinkedIn: {post_id}")
            self._move_to_done(approval_file, success=True)
            self.log_event(
                "linkedin_post_published",
                {
                    "post_id": post_id,
                    "approval_file": approval_file.name,
                    "author": author_urn,
                    "dry_run": False,
                },
            )
            return True

        except requests.exceptions.HTTPError as e:
            self.logger.error(f"LinkedIn API error: {e.response.status_code} — {e.response.text}")
            self.log_event(
                "linkedin_post_failed",
                {
                    "approval_file": approval_file.name,
                    "error": str(e),
                    "status_code": e.response.status_code if e.response else None,
                },
            )
            return False

    def _extract_post_content(self, file_content: str) -> str:
        """Extract the POST CONTENT section from an approval file."""
        # Look for the marked section
        patterns = [
            r"## Post Content\s*\n(.*?)(?=\n## |\Z)",
            r"## LinkedIn Post\s*\n(.*?)(?=\n## |\Z)",
            r"## Content\s*\n(.*?)(?=\n## |\Z)",
        ]
        for pattern in patterns:
            match = re.search(pattern, file_content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Fallback: look for content between --- frontmatter and first ##
        parts = file_content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()
            # Remove headers
            lines = [l for l in body.split("\n") if not l.startswith("#")]
            return "\n".join(lines).strip()

        return ""

    def _move_to_done(self, approval_file: Path, success: bool, dry_run: bool = False):
        """Move processed approval file to /Done."""
        dest = self.done / approval_file.name
        if dry_run:
            self.logger.info(f"[DRY RUN] Would move {approval_file.name} → /Done")
        else:
            approval_file.rename(dest)
            self.logger.info(f"Moved {approval_file.name} → /Done")

    # ------------------------------------------------------------------
    # Part 2: Monitor LinkedIn for mentions (API polling)
    # ------------------------------------------------------------------
    def check_for_updates(self) -> list:
        """
        Poll LinkedIn API for new notifications/mentions.
        Returns list of items to create action files for.
        """
        new_items = []

        # Check approved posts first (always, even without API token)
        approved = self.check_approved_posts()
        for post_file in approved:
            self.logger.info(f"Publishing approved post: {post_file.name}")
            self.publish_approved_post(post_file)

        if not ACCESS_TOKEN:
            return new_items

        try:
            # Check LinkedIn notifications
            resp = requests.get(
                f"{LINKEDIN_API_BASE}/socialActions",
                headers=_headers(),
                params={"q": "socialActions", "count": 10},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("elements", [])
                for elem in elements:
                    new_items.append(elem)
            elif resp.status_code == 401:
                self.logger.error("LinkedIn token expired. Update LINKEDIN_ACCESS_TOKEN in .env")
            else:
                self.logger.warning(f"LinkedIn API returned {resp.status_code}")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"LinkedIn API request failed: {e}")

        return new_items

    def create_action_file(self, item: dict) -> Path:
        """Create a .md action file for a LinkedIn notification/mention."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        item_type = item.get("type", "notification")
        actor = item.get("actor", {}).get("name", "Unknown")

        md_path = self.needs_action / f"LINKEDIN_{timestamp}_{item_type}.md"

        md_content = f"""---
type: linkedin_notification
notification_type: {item_type}
actor: {actor}
received: {datetime.now().isoformat()}
priority: normal
status: pending
source: linkedin_watcher
---

## New LinkedIn Notification

**Type:** {item_type}
**From:** {actor}
**Received:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Details

```json
{str(item)[:500]}
```

## Suggested Actions

- [ ] Review notification content
- [ ] Determine if response is needed
- [ ] Draft response via /draft-linkedin-post skill if required
- [ ] All replies require human approval before posting

## Notes

_Add processing notes here._
"""

        md_path.write_text(md_content, encoding="utf-8")
        self.log_event(
            "linkedin_notification_received",
            {
                "type": item_type,
                "actor": actor,
                "action_file": md_path.name,
            },
        )
        return md_path


# ---------------------------------------------------------------------------
# LinkedIn Post Publisher (called by Orchestrator directly)
# ---------------------------------------------------------------------------
class LinkedInPoster:
    """
    Standalone poster — used by orchestrator.py to publish approved posts.
    """

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.approved = self.vault_path / "Approved"
        self.done = self.vault_path / "Done"

    def post_from_file(self, approval_file: Path) -> bool:
        """Publish a LinkedIn post from an approved file."""
        watcher = LinkedInWatcher(str(self.vault_path))
        return watcher.publish_approved_post(approval_file)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AI Employee — LinkedIn Watcher")
    parser.add_argument(
        "--vault",
        default=str(Path(__file__).parent.parent),
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
        help="Log intended actions without making API calls",
    )
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        global DRY_RUN
        DRY_RUN = True

    watcher = LinkedInWatcher(vault_path=args.vault, check_interval=args.interval)
    watcher.run()


if __name__ == "__main__":
    main()
