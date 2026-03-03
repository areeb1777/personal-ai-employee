# Personal AI Employee — Hackathon 0

> *Your life and business on autopilot. Local-first, agent-driven, human-in-the-loop.*

A **Digital Full-Time Employee** powered by **Claude Code** and **Obsidian**. It proactively monitors your Gmail, drafts replies, schedules LinkedIn posts, and delivers weekly CEO briefings — all with human approval before any external action is taken.

---

## Architecture Overview

```
                    ┌─────────────────────────────────┐
                    │         CLAUDE CODE (Brain)      │
                    │   Reasoning + Skill Execution    │
                    └────────────┬────────────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                       │
   ┌──────▼──────┐      ┌────────▼───────┐     ┌───────▼───────┐
   │   Watchers  │      │   Obsidian     │     │  MCP Server   │
   │  (Senses)   │      │  Vault (Memory)│     │  (Email Tool) │
   └──────┬──────┘      └────────┬───────┘     └───────────────┘
          │                      │
   Gmail / Files /       Dashboard.md
   LinkedIn / FS         Plans / Logs
          │                      │
          └──────────┬───────────┘
                     │
            ┌────────▼────────┐
            │   Orchestrator  │
            │ /Approved watcher│
            └────────┬────────┘
                     │
            External Actions
         (Email Send / LinkedIn Post)
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Brain | Claude Code (claude-sonnet-4-6) |
| Memory / GUI | Obsidian (local Markdown vault) |
| File Senses | Python `watchdog` filesystem watcher |
| Email Senses | Gmail API (OAuth2 + credentials.json) |
| Email Send | Gmail SMTP + MCP Server |
| LinkedIn Post | Selenium + Chrome (browser automation) |
| Approval Flow | Folder-based (Pending_Approval → Approved) |
| Scheduling | Windows Task Scheduler (.ps1 setup script) |
| Secrets | `.env` file (never committed) |

---

## Tier Status

### Bronze Tier — Complete

| Feature | File | Status |
|---------|------|--------|
| Obsidian vault structure | All folders | Done |
| Claude Code CLAUDE.md context | `CLAUDE.md` | Done |
| Filesystem watcher | `watchers/filesystem_watcher.py` | Done |
| /process-inbox skill | `.claude/skills/process-inbox/` | Done |
| /triage-needs-action skill | `.claude/skills/triage-needs-action/` | Done |
| /update-dashboard skill | `.claude/skills/update-dashboard/` | Done |
| Human-in-the-loop approval flow | `/Pending_Approval` → `/Approved` | Done |
| Structured JSON logging | `/Logs/YYYY-MM-DD.json` | Done |
| Dashboard | `Dashboard.md` | Done |

### Silver Tier — Complete

| Feature | File | Status |
|---------|------|--------|
| Gmail watcher (API polling) | `watchers/gmail_watcher.py` | Done |
| Email MCP server (send/draft) | `mcp-servers/email-mcp/server.py` | Done |
| LinkedIn poster (Selenium) | `watchers/linkedin_selenium_poster.py` | Done |
| Orchestrator (routes approvals) | `orchestrator.py` | Done |
| Process manager (restart watchers) | `orchestrator.py` | Done |
| /process-email skill | `.claude/skills/process-email/` | Done |
| /draft-linkedin-post skill | `.claude/skills/draft-linkedin-post/` | Done |
| /generate-weekly-briefing skill | `.claude/skills/generate-weekly-briefing/` | Done |
| Windows Task Scheduler setup | `scripts/setup_task_scheduler.ps1` | Done |
| Launch scripts | `scripts/start_all.bat` | Done |

---

## Folder Structure

```
AI_Employee_Vault/
├── .claude/
│   ├── settings.json                  # MCP server registration
│   └── skills/
│       ├── process-inbox/             # /process-inbox skill
│       ├── triage-needs-action/       # /triage-needs-action skill
│       ├── update-dashboard/          # /update-dashboard skill
│       ├── process-email/             # /process-email skill
│       ├── draft-linkedin-post/       # /draft-linkedin-post skill
│       └── generate-weekly-briefing/  # /generate-weekly-briefing skill
│
├── Inbox/              # Drop files here — filesystem_watcher picks them up
├── Needs_Action/       # Items requiring Claude processing
├── Plans/              # Multi-step plans created by Claude
├── Pending_Approval/   # Awaiting human review (Claude writes here)
├── Approved/           # Human moves files here — orchestrator acts
├── Rejected/           # Human-rejected items
├── Done/               # Completed items (auto-moved by orchestrator)
├── Logs/               # Daily JSON audit logs (YYYY-MM-DD.json)
├── Briefings/          # Weekly CEO briefings (auto-generated Mondays)
│
├── watchers/
│   ├── base_watcher.py                # Shared BaseWatcher class
│   ├── filesystem_watcher.py          # Watches /Inbox for file drops
│   ├── gmail_watcher.py               # Polls Gmail API every 2 min
│   ├── linkedin_watcher.py            # LinkedIn API notifications
│   └── linkedin_selenium_poster.py    # Posts to LinkedIn via Chrome (no greenlet)
│
├── mcp-servers/
│   └── email-mcp/
│       └── server.py                  # MCP server: send_email, draft_email
│
├── scripts/
│   ├── gmail_auth.py                  # One-time Gmail OAuth2 setup
│   ├── setup_task_scheduler.ps1       # Windows Task Scheduler setup
│   ├── start_all.bat                  # Start all services (one-click)
│   ├── start_orchestrator.bat         # Start orchestrator only
│   └── start_watchers.bat             # Start watchers only
│
├── orchestrator.py                    # Master process: routes approvals
├── CLAUDE.md                          # Claude Code context and rules
├── Dashboard.md                       # Live system status
├── Company_Handbook.md                # Operating rules for the AI Employee
├── Business_Goals.md                  # Business context and KPIs
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
└── .gitignore                         # Protects secrets from git
```

---

## Setup Guide

### Prerequisites

- Python 3.12+
- Google Chrome browser installed
- Obsidian (optional, for GUI)
- Windows 10/11 (for Task Scheduler scripts)

### Step 1 — Clone and Install

```bash
git clone <your-repo-url>
cd AI_Employee_Vault

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate    # Windows PowerShell

# Install dependencies
pip install -r requirements.txt
```

> **PowerShell Execution Policy fix** (if activation is blocked):
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Step 2 — Configure Environment

```bash
copy .env.example .env
```

Edit `.env` and fill in your values:

```env
VAULT_PATH=C:\path\to\AI_Employee_Vault
DRY_RUN=true                          # Keep true until fully tested

GMAIL_SMTP_USER=you@gmail.com
GMAIL_SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx   # Gmail App Password (not account password)
```

### Step 3 — Gmail Authentication (One-time)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable Gmail API
3. Create OAuth 2.0 credentials → select **Desktop app** type
4. Download `credentials.json` → place it in the vault root

```bash
python scripts/gmail_auth.py
```

Browser opens → authorize with your Google account → `token.json` is saved automatically.

### Step 4 — LinkedIn Session Setup (One-time)

```bash
python watchers/linkedin_selenium_poster.py --setup
```

Chrome opens → log in to LinkedIn → press Enter → session saved to `.linkedin_session_chrome/`.

```bash
# Verify session is still valid anytime:
python watchers/linkedin_selenium_poster.py --test
```

### Step 5 — Start All Services

**Option A: One-click launch (Windows)**
```
Double-click: scripts\start_all.bat
```

**Option B: Manual (separate PowerShell terminals)**
```powershell
# Terminal 1 — Orchestrator (watches /Approved)
python orchestrator.py

# Terminal 2 — Gmail Watcher (polls every 2 min)
python watchers/gmail_watcher.py

# Terminal 3 — LinkedIn Watcher
python watchers/linkedin_watcher.py

# Terminal 4 — Filesystem Watcher (watches /Inbox)
python watchers/filesystem_watcher.py
```

### Step 6 — Windows Task Scheduler (Auto-start on login)

```powershell
.\scripts\setup_task_scheduler.ps1 -VaultPath "C:\path\to\AI_Employee_Vault"
```

This schedules:
- Orchestrator: starts on login (always-on)
- Daily triage: 8:00 AM
- LinkedIn post draft: 9:00 AM weekdays
- Weekly CEO briefing: Monday 7:00 AM

---

## Testing Guide

### Bronze Tier Tests

**Test 1 — Filesystem Watcher**
```bash
# Drop a file in /Inbox
echo "Test task: Follow up with client" > Inbox/test_task.txt

# Run watcher — it creates Needs_Action/FILE_*.md
python watchers/filesystem_watcher.py
```

**Test 2 — Process Inbox Skill**
```
In Claude Code: /process-inbox
```
Files in `/Inbox` are classified, routed to `/Needs_Action`, dashboard updated.

**Test 3 — Triage**
```
In Claude Code: /triage-needs-action
```
Items in `/Needs_Action` are reasoned about, approval requests go to `/Pending_Approval`.

**Test 4 — Dashboard Update**
```
In Claude Code: /update-dashboard
```
`Dashboard.md` refreshed with current counts.

---

### Silver Tier Tests

**Test 5 — Gmail Watcher**
```bash
# Authenticate first (one-time):
python scripts/gmail_auth.py

# Run watcher — send yourself a test email:
python watchers/gmail_watcher.py
# New EMAIL_*.md appears in /Needs_Action
```

**Test 6 — Process Email Skill**
```
In Claude Code: /process-email
```
EMAIL_*.md files processed → draft reply written to `/Pending_Approval/APPROVAL_send_email_*.md`.

**Test 7 — Email Send via Orchestrator**
```bash
# Move approval file to /Approved/ to trigger send:
# (Windows Explorer or PowerShell)
Move-Item Pending_Approval\APPROVAL_send_email_*.md Approved\

# Run orchestrator with dry-run first:
python orchestrator.py --dry-run

# Set DRY_RUN=false in .env for real send, then:
python orchestrator.py
```

**Test 8 — LinkedIn Draft Post**
```
In Claude Code: /draft-linkedin-post
```
Draft written to `/Pending_Approval/LINKEDIN_POST_*.md`.

**Test 9 — LinkedIn Dry-Run**
```bash
python watchers/linkedin_selenium_poster.py \
  --post "Pending_Approval/LINKEDIN_POST_*.md" \
  --dry-run
# Shows post content (609 chars) without posting
```

**Test 10 — LinkedIn Real Post**
```bash
# 1. Set DRY_RUN=false in .env
# 2. Move post to /Approved/
Move-Item Pending_Approval\LINKEDIN_POST_*.md Approved\
# 3. Orchestrator detects and posts automatically
python orchestrator.py
```

**Test 11 — Weekly Briefing**
```
In Claude Code: /generate-weekly-briefing
```
Briefing written to `/Briefings/BRIEFING_YYYY-MM-DD.md`.

---

## Human-in-the-Loop Approval Flow

```
Claude drafts action
        |
        v
/Pending_Approval/APPROVAL_*.md    <- Claude writes here (never acts directly)
        |
   Human reviews file
        |
   +----+----+
   |         |
   v         v
/Approved/ /Rejected/
   |
   v
Orchestrator detects -> executes action -> moves to /Done/
```

**Rules:**
- Claude can NEVER send email or post to LinkedIn without an approved file in `/Approved/`
- `DRY_RUN=true` (default) prevents all external actions — safe for testing
- Set `DRY_RUN=false` in `.env` only when fully tested and ready

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `VAULT_PATH` | Yes | Absolute path to this vault |
| `DRY_RUN` | Yes | `true` = safe mode, `false` = real actions |
| `GMAIL_SMTP_USER` | Silver | Gmail address for sending |
| `GMAIL_SMTP_PASSWORD` | Silver | Gmail App Password (not your Google password) |
| `GMAIL_IMAP_USER` | Silver | Gmail address for reading |
| `GMAIL_IMAP_PASSWORD` | Silver | Gmail App Password for IMAP |
| `LINKEDIN_ACCESS_TOKEN` | Optional | LinkedIn API token (not needed for Selenium) |

See `.env.example` for the complete list with descriptions.

---

## Security Notes

1. **Never commit `.env`** — gitignored. Use `.env.example` as the template.
2. **Never commit `credentials.json` or `token.json`** — Gmail OAuth credentials.
3. **LinkedIn session** in `.linkedin_session_chrome/` is gitignored — contains browser cookies.
4. **Gmail App Password** is not your Google account password. Generate at
   [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
5. **DRY_RUN=true** is the safe default. The AI cannot take real external actions until
   you explicitly set it to `false`.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Selenium over Playwright | Playwright requires the `greenlet` C extension which fails with DLL errors on Windows. Selenium uses Chrome directly — no such dependency. |
| Gmail API over IMAP | More reliable, supports OAuth2, no App Password needed for reading. |
| Folder-based approvals | Simple, transparent, works with any file manager — no additional UI required. |
| JSON logs (not DB) | Human-readable, git-friendly, renderable as Obsidian notes. |
| MCP for email send | Exposes email as a Claude tool with built-in DRY_RUN guard and authentication. |

---

## Troubleshooting

**`greenlet DLL load failed`**
Playwright requires the `greenlet` C extension which fails on some Windows setups.
Fix: Use `linkedin_selenium_poster.py` — no greenlet required.

**Gmail `redirect_uri_mismatch` (Error 400)**
Your `credentials.json` was created as "Web application" type.
Fix: In Google Cloud Console, create new OAuth client → select **Desktop app** → download new `credentials.json`.

**PowerShell `.venv\Scripts\activate` blocked**
Fix:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**LinkedIn session expired**
Fix:
```bash
python watchers/linkedin_selenium_poster.py --setup
```

**Orchestrator can't find watcher module**
Fix: Always run orchestrator from vault root: `python orchestrator.py`

---

*Built for Hackathon 0: Personal AI Employee — AI-Native Hackathon 2026*
