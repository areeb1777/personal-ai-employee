"""
linkedin_selenium_poster.py — LinkedIn Poster using Selenium (no greenlet needed).

Uses Chrome WebDriver via selenium + webdriver-manager.
No greenlet, no Playwright DLL issues. Works on Python 3.12+ Windows.

Usage:
    python watchers/linkedin_selenium_poster.py --setup
    python watchers/linkedin_selenium_poster.py --test
    python watchers/linkedin_selenium_poster.py --post "Pending_Approval/LINKEDIN_POST_*.md"
    python watchers/linkedin_selenium_poster.py --post "file.md" --dry-run

Dependencies:
    pip install selenium webdriver-manager python-dotenv
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

VAULT_ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=VAULT_ROOT / ".env")

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
SESSION_DIR = Path(__file__).parent / ".linkedin_session_chrome"
SESSION_DIR.mkdir(exist_ok=True)

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    print(
        f"\nERROR: Cannot import selenium or webdriver-manager\n"
        f"Error: {e}\n\n"
        f"Fix:\n"
        f"  pip install selenium webdriver-manager\n"
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_driver(headless: bool = True) -> webdriver.Chrome:
    """Create Chrome driver with persistent session (user-data-dir)."""
    options = Options()
    options.add_argument(f"--user-data-dir={SESSION_DIR}")
    options.add_argument("--profile-directory=Default")
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1280,800")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def extract_post_content(file_path: Path) -> str:
    content = file_path.read_text(encoding="utf-8")
    patterns = [
        r"## Post Content\s*\n(.*?)(?=\n---|\\n## |\Z)",
        r"## LinkedIn Post\s*\n(.*?)(?=\n---|\\n## |\Z)",
        r"## Content\s*\n(.*?)(?=\n---|\\n## |\Z)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
            if text:
                return text
    parts = content.split("---", 2)
    if len(parts) >= 3:
        lines = [l for l in parts[2].strip().split("\n") if not l.startswith("#")]
        return "\n".join(lines).strip()
    return ""


def log_event(action_type: str, details: dict):
    import json
    logs_dir = VAULT_ROOT / "Logs"
    logs_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_dir / f"{today}.json"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "actor": "linkedin_selenium_poster",
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
# Setup: manual login, session saved in SESSION_DIR
# ---------------------------------------------------------------------------

def setup_session():
    """Open visible Chrome browser for manual LinkedIn login."""
    print("=" * 60)
    print("  LinkedIn Session Setup (Selenium/Chrome)")
    print("=" * 60)
    print()
    print("A Chrome browser window will open.")
    print("1. Log in to LinkedIn with your email + password")
    print("2. Complete any 2FA/verification if asked")
    print("3. Once you see your LinkedIn feed — come back here and press Enter")
    print()
    input("Press Enter to open browser...")

    driver = get_driver(headless=False)
    try:
        driver.get("https://www.linkedin.com/login")
        print("\nBrowser open — log in to LinkedIn now.")
        input("Press Enter AFTER you see your LinkedIn feed (home page)...")

        url = driver.current_url
        if "feed" in url or "mynetwork" in url or "/in/" in url:
            print("Login detected! Session saved.")
        else:
            print(f"URL: {url} — session saved anyway.")
    finally:
        driver.quit()

    print(f"\nSession saved to: {SESSION_DIR}")
    print("\nNext: python watchers/linkedin_selenium_poster.py --test")


# ---------------------------------------------------------------------------
# Test: verify session valid
# ---------------------------------------------------------------------------

def test_session() -> bool:
    """Test if saved Chrome session is still logged in to LinkedIn."""
    print("Testing LinkedIn session...")
    try:
        driver = get_driver(headless=True)
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(4)
        url = driver.current_url
        driver.quit()

        if "login" in url or "authwall" in url:
            print("Session expired — run: python watchers/linkedin_selenium_poster.py --setup")
            return False
        print("LinkedIn session valid — logged in.")
        return True
    except Exception as e:
        print(f"Test failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Post: publish to LinkedIn
# ---------------------------------------------------------------------------

def post_to_linkedin(post_text: str, dry_run: bool = DRY_RUN) -> bool:
    """Automate LinkedIn web to create a post via Chrome/Selenium."""
    if dry_run:
        preview = (post_text[:300] + ("..." if len(post_text) > 300 else ""))
        safe_preview = preview.encode("ascii", "replace").decode("ascii")
        print(f"[DRY RUN] Would post to LinkedIn ({len(post_text)} chars):")
        print("-" * 40)
        print(safe_preview)
        print("-" * 40)
        return True

    print(f"Posting to LinkedIn ({len(post_text)} chars)...")

    try:
        driver = get_driver(headless=True)
        wait = WebDriverWait(driver, 12)

        driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)

        if "login" in driver.current_url or "authwall" in driver.current_url:
            print("Session expired — run --setup")
            driver.quit()
            return False

        # ---------------------------------------------------------------
        # Step 1: Click the "Start a post" text input (top of feed)
        # NOT the Video/Photo/Write article buttons below it
        # ---------------------------------------------------------------
        clicked = False

        # Try aria-label first (most reliable)
        for aria in ["Start a post", "start a post"]:
            try:
                btn = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, f'button[aria-label="{aria}"]')
                ))
                btn.click()
                clicked = True
                print("  Clicked 'Start a post' (aria-label)")
                break
            except Exception:
                pass

        # Try by visible text using XPath (the rounded text input box)
        if not clicked:
            try:
                btn = WebDriverWait(driver, 6).until(EC.element_to_be_clickable(
                    (By.XPATH, '//button[contains(normalize-space(.), "Start a post")]')
                ))
                btn.click()
                clicked = True
                print("  Clicked 'Start a post' (XPath text)")
            except Exception:
                pass

        # Try the placeholder span inside the share box
        if not clicked:
            try:
                btn = WebDriverWait(driver, 6).until(EC.element_to_be_clickable(
                    (By.XPATH, '//span[contains(text(),"Start a post")]/ancestor::button[1]')
                ))
                btn.click()
                clicked = True
                print("  Clicked 'Start a post' (span ancestor)")
            except Exception:
                pass

        if not clicked:
            print("Could not find 'Start a post' button.")
            driver.quit()
            return False

        # Wait for post creation modal to fully open
        time.sleep(3)

        # ---------------------------------------------------------------
        # Step 2: Find the text editor inside the modal
        # LinkedIn modal editor selector (2024-2025 UI)
        # ---------------------------------------------------------------
        typed = False

        # Try aria-label selectors first (most specific)
        editor_aria = [
            "Text editor for creating content",
            "Create a post",
            "What do you want to talk about?",
        ]
        for aria in editor_aria:
            try:
                editor = WebDriverWait(driver, 6).until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, f'div[aria-label="{aria}"]')
                ))
                editor.click()
                time.sleep(0.5)
                editor.send_keys(post_text)
                typed = True
                print("  Post text entered (aria editor)")
                break
            except Exception:
                pass

        # Try contenteditable inside the modal dialog
        if not typed:
            for sel in [
                'div[role="dialog"] div[contenteditable="true"]',
                'div[role="dialog"] div[role="textbox"]',
                'div.ql-editor[contenteditable="true"]',
                'div[contenteditable="true"][data-placeholder]',
                'div[contenteditable="true"]',
            ]:
                try:
                    editor = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    editor.click()
                    time.sleep(0.5)
                    editor.send_keys(post_text)
                    typed = True
                    print(f"  Post text entered ({sel})")
                    break
                except Exception:
                    continue

        if not typed:
            print("Could not find post editor inside modal.")
            driver.quit()
            return False

        time.sleep(1)

        # ---------------------------------------------------------------
        # Step 3: Click the Post / Submit button
        # ---------------------------------------------------------------
        submitted = False

        for sel in [
            'button[aria-label="Post"]',
            'button.share-actions__primary-action',
            'div[role="dialog"] button.artdeco-button--primary',
        ]:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                btn.click()
                submitted = True
                print("  Post submitted")
                break
            except Exception:
                continue

        # XPath fallback: button with text "Post" inside modal
        if not submitted:
            try:
                btn = WebDriverWait(driver, 6).until(EC.element_to_be_clickable(
                    (By.XPATH, '//div[@role="dialog"]//button[normalize-space(text())="Post"]')
                ))
                btn.click()
                submitted = True
                print("  Post submitted (XPath)")
            except Exception:
                pass

        if not submitted:
            print("Could not find Post submit button.")
            driver.quit()
            return False

        time.sleep(3)
        print("Posted to LinkedIn!")
        driver.quit()
        return True

    except Exception as e:
        print(f"Error during posting: {e}")
        try:
            driver.quit()
        except Exception:
            pass
        return False


# ---------------------------------------------------------------------------
# Post from approval file (called by orchestrator)
# ---------------------------------------------------------------------------

def post_from_file(file_path: Path, dry_run: bool = DRY_RUN) -> bool:
    """Read a LINKEDIN_POST_*.md approval file and post its content."""
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return False

    post_text = extract_post_content(file_path)
    if not post_text:
        print(f"No post content found in: {file_path.name}")
        return False

    print(f"File: {file_path.name}")
    success = post_to_linkedin(post_text, dry_run=dry_run)

    if success:
        done_dir = VAULT_ROOT / "Done"
        done_dir.mkdir(exist_ok=True)
        if not dry_run:
            file_path.rename(done_dir / file_path.name)
            print(f"Moved {file_path.name} to /Done/")
        log_event("linkedin_post_published", {
            "file": file_path.name,
            "chars": len(post_text),
            "dry_run": dry_run,
        })
    else:
        log_event("linkedin_post_failed", {"file": file_path.name})

    return success


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LinkedIn Selenium Poster (no greenlet required)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--setup", action="store_true", help="Login to LinkedIn and save Chrome session")
    group.add_argument("--test", action="store_true", help="Test if saved session is still logged in")
    group.add_argument("--post", metavar="FILE", help="Post from a LINKEDIN_POST_*.md approval file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be posted without posting")
    args = parser.parse_args()

    global DRY_RUN
    if args.dry_run:
        DRY_RUN = True

    if args.setup:
        setup_session()
    elif args.test:
        ok = test_session()
        sys.exit(0 if ok else 1)
    elif args.post:
        p = Path(args.post)
        if not p.is_absolute():
            p = VAULT_ROOT / p
        if "*" in str(p):
            matches = sorted(p.parent.glob(p.name))
            if not matches:
                print(f"No files found: {args.post}")
                sys.exit(1)
            p = matches[-1]
        success = post_from_file(p, dry_run=DRY_RUN)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
