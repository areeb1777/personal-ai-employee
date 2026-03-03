"""
gmail_auth.py — One-time Gmail OAuth2 Authorization Setup

Run this ONCE to authorize the AI Employee to access your Gmail.
It will open a browser window, ask you to sign in and approve access,
then save a token.json file that the gmail_watcher.py uses to run.

Usage:
    python scripts/gmail_auth.py

After running:
    - token.json is created in the vault root
    - Start the watcher: python watchers/gmail_watcher.py

Requirements:
    pip install google-auth google-auth-oauthlib google-api-python-client

What permissions are requested (scopes):
    - gmail.readonly   → Read emails (for detection)
    - gmail.modify     → Mark emails as read after processing
"""

import sys
from pathlib import Path

# Vault root = parent of scripts/
VAULT_ROOT = Path(__file__).parent.parent
CREDENTIALS_FILE = VAULT_ROOT / "credentials.json"
TOKEN_FILE = VAULT_ROOT / "token.json"

# Gmail API scopes needed
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    print(
        "\n❌ Google API libraries not installed.\n"
        "Run: pip install google-auth google-auth-oauthlib google-api-python-client\n"
    )
    sys.exit(1)


def main():
    print("=" * 60)
    print("  AI Employee — Gmail OAuth2 Setup")
    print("=" * 60)
    print()

    # Check credentials.json exists
    if not CREDENTIALS_FILE.exists():
        print(f"❌ credentials.json not found at:\n   {CREDENTIALS_FILE}")
        print()
        print("Steps to get credentials.json:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Create a project (or select existing)")
        print("  3. APIs & Services → Enable APIs → search 'Gmail API' → Enable")
        print("  4. APIs & Services → Credentials → Create Credentials → OAuth client ID")
        print("  5. Application type: Desktop app")
        print("  6. Download JSON → rename to credentials.json → place in vault root")
        sys.exit(1)

    print(f"✅ Found credentials.json at:\n   {CREDENTIALS_FILE}")
    print()

    creds = None

    # Reuse existing token if valid
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh or re-authorize
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            creds.refresh(Request())
            print("✅ Token refreshed successfully.")
        else:
            print("🌐 Opening browser for Gmail authorization...")
            print("   Sign in with the Gmail account you want the AI Employee to monitor.")
            print()
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
            print()
            print("✅ Authorization granted!")

        # Save token for future runs
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print(f"✅ Token saved to:\n   {TOKEN_FILE}")
    else:
        print("✅ Existing token is still valid — no re-authorization needed.")

    # Quick connectivity test
    print()
    print("🧪 Testing Gmail API connection...")
    try:
        from googleapiclient.discovery import build
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", "unknown")
        total = profile.get("messagesTotal", "?")
        print(f"✅ Connected as: {email}")
        print(f"   Total messages in mailbox: {total}")
    except Exception as e:
        print(f"⚠️  Connection test failed: {e}")
        print("   token.json was saved — try running the watcher anyway.")

    print()
    print("=" * 60)
    print("  Setup complete! Next steps:")
    print("=" * 60)
    print()
    print("  1. Ensure your .env has VAULT_PATH set:")
    print(f"     VAULT_PATH={VAULT_ROOT}")
    print()
    print("  2. Start the Gmail watcher:")
    print("     python watchers/gmail_watcher.py")
    print()
    print("  3. Or start the full orchestrator (manages all watchers):")
    print("     python orchestrator.py")
    print()
    print("  NOTE: token.json is in .gitignore — it will NOT be committed to git.")
    print()


if __name__ == "__main__":
    main()
