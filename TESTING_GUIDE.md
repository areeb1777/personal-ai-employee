# AI Employee — Complete Testing Guide

Step-by-step guide to test every feature from Bronze Tier to Silver Tier.
Run these tests in order — each builds on the previous.

---

## Prerequisites — Setup (Do This First)

### 1. Install Python 3.12+
Download from https://python.org — version 3.12.5 recommended.

### 2. Clone the repo and install dependencies
```bash
git clone <your-repo-url>
cd AI_Employee_Vault

python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
# If blocked: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

pip install -r requirements.txt
```

> All packages install in one command. No manual pip installs needed.

### 3. Copy and configure .env
```bash
copy .env.example .env
```

Edit `.env` — minimum required fields:
```
VAULT_PATH=D:\path\to\AI_Employee_Vault
DRY_RUN=true
GMAIL_SMTP_USER=your.email@gmail.com
GMAIL_SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

---

## Part 1 — Bronze Tier Tests

### TEST-B1: Filesystem Watcher

**What it does:** Watches `/Inbox` folder. When you drop a file, it auto-creates a structured `FILE_*.md` in `/Needs_Action`.

**Step 1** — Start the watcher in a terminal:
```bash
python watchers/filesystem_watcher.py
```
Expected output:
```
[FileSystemWatcher] Watching: D:\...\Inbox
[FileSystemWatcher] Press Ctrl+C to stop
```

**Step 2** — In a new terminal, drop a test file in Inbox:
```bash
echo "Urgent: Client wants invoice by Friday" > Inbox/test_task.txt
```

**Step 3** — Back in watcher terminal, you should see:
```
[FileSystemWatcher] New file detected: test_task.txt
[FileSystemWatcher] Created: Needs_Action/FILE_20260303_XXXXXX_test_task.md
```

**Step 4** — Verify the file was created:
```bash
ls Needs_Action/
```
A `FILE_*.md` file should appear with the task details.

**PASS criteria:** FILE_*.md created in Needs_Action within 5 seconds of dropping file.

---

### TEST-B2: Process Inbox Skill

**What it does:** Claude reads all files in `/Inbox`, classifies them by type/priority, and routes them to `/Needs_Action` or `/Done`.

**Step 1** — Make sure there are files in Inbox:
```bash
echo "Meeting notes from Monday call" > Inbox/meeting_notes.txt
echo "URGENT: Server down, need fix now" > Inbox/urgent_alert.txt
```

**Step 2** — In Claude Code terminal, run the skill:
```
/process-inbox
```

**Step 3** — Claude reads Inbox, outputs reasoning, creates action files.

**PASS criteria:**
- Files from `/Inbox` moved to `/Needs_Action/`
- Each file gets a structured `FILE_*.md` with type + priority
- Dashboard.md updated with new counts

---

### TEST-B3: Triage Needs Action Skill

**What it does:** Claude reads all pending items in `/Needs_Action`, reasons about each, and routes them: creates Plans for complex tasks, writes approval requests to `/Pending_Approval`.

**Step 1** — Make sure there are items in Needs_Action (from TEST-B1 or B2).

**Step 2** — In Claude Code terminal:
```
/triage-needs-action
```

**Step 3** — Claude processes each item and outputs reasoning.

**PASS criteria:**
- Simple items: moved to `/Done/`
- Complex items: `PLAN_*.md` created in `/Plans/`
- Items needing approval: `APPROVAL_*.md` in `/Pending_Approval/`
- Dashboard updated

---

### TEST-B4: Update Dashboard Skill

**What it does:** Refreshes `Dashboard.md` with current counts from all folders.

**Step 1** — In Claude Code terminal:
```
/update-dashboard
```

**PASS criteria:** `Dashboard.md` shows accurate counts for all folders (Inbox, Needs_Action, Pending_Approval, Done, etc.)

---

## Part 2 — Silver Tier Tests

### TEST-S1: Gmail Authentication (One-time Setup)

**What it does:** Authorizes Claude to read your Gmail using OAuth2. Saves `token.json`.

**Prerequisites:**
1. Go to https://console.cloud.google.com/
2. Create project → Enable Gmail API
3. APIs & Services → Credentials → Create → OAuth 2.0 Client ID → **Desktop app**
4. Download `credentials.json` → place in vault root folder

**Step 1** — Run the auth script:
```bash
python scripts/gmail_auth.py
```

**Step 2** — Browser opens → Select your Google account → Allow access

**Step 3** — Expected output:
```
Connected as: your.email@gmail.com
Total messages in inbox: 301
Gmail authentication successful!
token.json saved.
```

**PASS criteria:** `token.json` created in vault root, email address shown.

> **Note:** If you see `redirect_uri_mismatch` error, your credentials.json is "Web application" type. Create a new one as **Desktop app** type.

---

### TEST-S2: Gmail Watcher (Auto Email Detection)

**What it does:** Polls Gmail API every 2 minutes. When new unread emails arrive, creates `EMAIL_*.md` files in `/Needs_Action`.

**Step 1** — Start the Gmail watcher:
```bash
python watchers/gmail_watcher.py
```
Expected output:
```
[GmailWatcher] Starting — polling every 120s
[GmailWatcher] Authenticated as: your.email@gmail.com
[GmailWatcher] Checking Gmail...
[GmailWatcher] No new messages.
```

**Step 2** — Send yourself a test email (from another account or Gmail web).

Subject: `Test AI Employee`
Body: `This is a test email to verify the AI Employee Gmail integration.`

**Step 3** — Wait up to 2 minutes, or restart the watcher. Expected output:
```
[GmailWatcher] New email from: testaccount@gmail.com
[GmailWatcher] Created: Needs_Action/EMAIL_20260303_XXXXXX_Test_AI_Employee.md
```

**Step 4** — Verify file created:
```bash
ls Needs_Action/
# Should show: EMAIL_20260303_XXXXXX_Test_AI_Employee.md
```

**PASS criteria:** EMAIL_*.md appears in `/Needs_Action` with sender, subject, body extracted.

---

### TEST-S3: Process Email Skill

**What it does:** Claude reads EMAIL_*.md files in `/Needs_Action`, drafts a professional reply, and writes it to `/Pending_Approval/` as `APPROVAL_send_email_*.md`. Does NOT send anything.

**Step 1** — Make sure there's an EMAIL_*.md in `/Needs_Action` (from TEST-S2).

**Step 2** — In Claude Code terminal:
```
/process-email
```

**Step 3** — Claude reads the email, drafts a reply, outputs reasoning.

**Step 4** — Check Pending_Approval:
```bash
ls Pending_Approval/
# Should show: APPROVAL_send_email_2026-XX-XX_Re_Test_AI_Employee.md
```

**Step 5** — Open the file, review the draft reply.

**PASS criteria:** `APPROVAL_send_email_*.md` created with `to:`, `subject:`, and email body.

---

### TEST-S4: Email Send via Approval Flow (Orchestrator)

**What it does:** After you approve an email draft, the orchestrator detects it and sends the actual email via Gmail SMTP.

**Step 1** — Set up Gmail App Password (if not done):
1. Go to https://myaccount.google.com/apppasswords
2. Generate password for "Mail" on your device
3. Copy the 16-character password into `.env`:
   ```
   GMAIL_SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx
   ```

**Step 2** — Set DRY_RUN=false in `.env`:
```
DRY_RUN=false
```

**Step 3** — Move approval file to `/Approved/` (simulate human approval):
```bash
# PowerShell:
Move-Item "Pending_Approval\APPROVAL_send_email_*.md" "Approved\"
```
Or drag and drop the file in Windows Explorer.

**Step 4** — Start the orchestrator:
```bash
python orchestrator.py
```
Expected output:
```
[Orchestrator] Processing approved file: APPROVAL_send_email_*.md
[Orchestrator] Email sent to: recipient@email.com: Test AI Employee
[Orchestrator] Moved APPROVAL_send_email_*.md to /Done
```

**Step 5** — Check your email inbox — reply should have arrived.

**PASS criteria:** Email received, approval file moved to `/Done/`.

> **Safe test first:** Run `python orchestrator.py --dry-run` to verify without sending.

---

### TEST-S5: LinkedIn Session Setup (One-time)

**What it does:** Opens Chrome browser for you to log in to LinkedIn. Saves the session so future posts are headless (no login needed).

**Step 1** — Run setup:
```bash
python watchers/linkedin_selenium_poster.py --setup
```

**Step 2** — Press Enter → Chrome opens → Log in to LinkedIn with your email + password.

**Step 3** — Complete any 2FA if prompted.

**Step 4** — Once you see your LinkedIn feed → come back to terminal → press Enter.

**Step 5** — Verify session saved:
```bash
python watchers/linkedin_selenium_poster.py --test
```
Expected:
```
LinkedIn session valid — logged in.
```

**PASS criteria:** `--test` returns "session valid" without opening browser.

---

### TEST-S6: Draft LinkedIn Post Skill

**What it does:** Claude drafts a LinkedIn post based on recent activity/goals and saves it to `/Pending_Approval/` for your review.

**Step 1** — In Claude Code terminal:
```
/draft-linkedin-post
```

**Step 2** — Claude generates a professional post, writes it to:
```
Pending_Approval/LINKEDIN_POST_2026-XX-XX_*.md
```

**Step 3** — Open the file, review and edit if needed.

**PASS criteria:** `LINKEDIN_POST_*.md` appears in `/Pending_Approval/` with a `## Post Content` section.

---

### TEST-S7: LinkedIn Dry-Run Post

**What it does:** Tests the posting flow without actually posting to LinkedIn. Shows what would be posted.

**Step 1** — Make sure DRY_RUN=true in `.env` (safe default).

**Step 2** — Run dry-run:
```bash
python watchers/linkedin_selenium_poster.py \
  --post "Pending_Approval/LINKEDIN_POST_*.md" \
  --dry-run
```

Expected output:
```
File: LINKEDIN_POST_2026-XX-XX_*.md
[DRY RUN] Would post to LinkedIn (609 chars):
----------------------------------------
Your post content here...
----------------------------------------
```

**PASS criteria:** Post content displayed, no browser opened, no actual post.

---

### TEST-S8: LinkedIn Real Post

**What it does:** Actually posts to LinkedIn using Chrome automation. No LinkedIn Developer App needed.

**Step 1** — Set DRY_RUN=false in `.env`.

**Step 2** — Move post file to `/Approved/`:
```bash
Move-Item "Pending_Approval\LINKEDIN_POST_*.md" "Approved\"
```
Or use Windows Explorer drag & drop.

**Option A — Via Orchestrator (recommended, automatic):**
```bash
python orchestrator.py
```
Expected:
```
[Orchestrator] Processing approved file: LINKEDIN_POST_*.md
Clicked 'Start a post' (XPath text)
Post text entered (aria editor)
Post submitted
Posted to LinkedIn!
Moved LINKEDIN_POST_*.md to /Done/
```

**Option B — Direct (manual trigger):**
```bash
python watchers/linkedin_selenium_poster.py \
  --post "Approved/LINKEDIN_POST_*.md"
```

**Step 3** — Check your LinkedIn profile — post should appear.

**PASS criteria:** Post live on LinkedIn, file moved to `/Done/`.

---

### TEST-S9: Weekly Briefing Skill

**What it does:** Claude generates a CEO-style weekly summary of all activity — emails processed, posts published, tasks completed.

**Step 1** — In Claude Code terminal:
```
/generate-weekly-briefing
```

**Step 2** — Claude reviews Logs, Done folder, Needs_Action history.

**Step 3** — Briefing saved to:
```
Briefings/BRIEFING_2026-03-03.md
```

**PASS criteria:** Briefing file created with activity summary, counts, and highlights.

---

### TEST-S10: Full Orchestrator Flow

**What it does:** Orchestrator runs as always-on process, watches `/Approved/`, and automatically routes files the moment you approve them.

**Step 1** — Start orchestrator with all watchers:
```bash
python orchestrator.py
```
Or use the one-click launcher:
```
scripts\start_all.bat
```

**Step 2** — Drop a file in Inbox:
```bash
echo "Test: Full pipeline check" > Inbox/pipeline_test.txt
```

**Step 3** — Watch the full pipeline run automatically:
```
filesystem_watcher  → creates Needs_Action/FILE_*.md
(run /triage-needs-action in Claude Code)
→ creates Pending_Approval/APPROVAL_*.md
(move file to Approved/ in Explorer)
orchestrator        → detects and executes
→ file moved to Done/
```

**PASS criteria:** File moves through entire pipeline from Inbox → Done with logs in `/Logs/`.

---

## Quick Reference — Commands

### Start Services
```bash
# All services (one-click)
scripts\start_all.bat

# Individual services
python orchestrator.py
python watchers/filesystem_watcher.py
python watchers/gmail_watcher.py
python watchers/linkedin_watcher.py
```

### Claude Code Skills
```
/process-inbox              # Process files in /Inbox
/triage-needs-action        # Reason about /Needs_Action items
/update-dashboard           # Refresh Dashboard.md
/process-email              # Draft replies for EMAIL_*.md files
/draft-linkedin-post        # Generate a LinkedIn post draft
/generate-weekly-briefing   # Monday CEO briefing
```

### LinkedIn Commands
```bash
python watchers/linkedin_selenium_poster.py --setup    # First-time login
python watchers/linkedin_selenium_poster.py --test     # Verify session
python watchers/linkedin_selenium_poster.py --post "Pending_Approval/LINKEDIN_POST_*.md" --dry-run
python watchers/linkedin_selenium_poster.py --post "Approved/LINKEDIN_POST_*.md"
```

### Gmail Commands
```bash
python scripts/gmail_auth.py           # One-time OAuth2 setup
python watchers/gmail_watcher.py       # Start Gmail polling watcher
```

---

## Checklist — All Tests

| # | Test | Component | Pass? |
|---|------|-----------|-------|
| B1 | File drop triggers FILE_*.md creation | filesystem_watcher.py | |
| B2 | /process-inbox routes inbox files | Claude Skill | |
| B3 | /triage-needs-action creates approvals | Claude Skill | |
| B4 | /update-dashboard refreshes counts | Claude Skill | |
| S1 | Gmail OAuth2 completes, token.json saved | gmail_auth.py | |
| S2 | New email creates EMAIL_*.md | gmail_watcher.py | |
| S3 | /process-email drafts reply to Pending_Approval | Claude Skill | |
| S4 | Approved email is sent via SMTP | orchestrator.py | |
| S5 | LinkedIn session saved, --test passes | linkedin_selenium_poster.py | |
| S6 | /draft-linkedin-post creates LINKEDIN_POST_*.md | Claude Skill | |
| S7 | Dry-run shows post content without posting | linkedin_selenium_poster.py | |
| S8 | Real post appears on LinkedIn | linkedin_selenium_poster.py | |
| S9 | /generate-weekly-briefing creates briefing | Claude Skill | |
| S10 | Full Inbox→Done pipeline with orchestrator | orchestrator.py | |

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `redirect_uri_mismatch` | credentials.json is "Web app" type | Create new OAuth client as "Desktop app" |
| `ModuleNotFoundError` | Package not installed | `pip install -r requirements.txt` |
| `LinkedIn session expired` | Session cookie expired | `python watchers/linkedin_selenium_poster.py --setup` |
| `Could not find 'Start a post'` | LinkedIn UI changed | Check `scripts/debug_screenshots/` — run debug script |
| `DLL load failed (greenlet)` | Playwright on Windows | Use Selenium poster — already configured |
| PowerShell `activate` blocked | Execution policy | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `token.json` not found | Gmail not authenticated | Run `python scripts/gmail_auth.py` first |
| Email not sent | GMAIL_SMTP_PASSWORD wrong | Use App Password from myaccount.google.com/apppasswords |
| `DRY_RUN=true` blocking actions | Safe default | Set `DRY_RUN=false` in `.env` for real actions |
