# Personal AI Employee — AI_Employee_Vault

> **Hackathon:** Personal AI Employee Hackathon 0 — Building Autonomous FTEs in 2026
> **Tier:** Bronze (Foundation)
> **Stack:** Claude Code + Obsidian + Python Watchdog

---

## What This Is

A local-first, autonomous AI Employee that:
- **Watches** your filesystem for new files (Watcher script)
- **Reasons** about tasks using Claude Code
- **Routes** items through Inbox → Needs_Action → Done
- **Escalates** sensitive actions via human-in-the-loop approval files
- **Reports** system state via a live Dashboard.md

---

## Bronze Tier Deliverables

| Requirement | Status | Location |
|-------------|--------|----------|
| Dashboard.md | ✅ Done | `/Dashboard.md` |
| Company_Handbook.md | ✅ Done | `/Company_Handbook.md` |
| File System Watcher | ✅ Done | `/watchers/filesystem_watcher.py` |
| Claude reads/writes vault | ✅ Done | Via Agent Skills |
| Folder structure (Inbox/Needs_Action/Done) | ✅ Done | Root of vault |
| Agent Skills | ✅ Done | `/.claude/skills/` |

---

## Folder Structure

```
AI_Employee_Vault/
├── .claude/
│   └── skills/
│       ├── process-inbox/        ← Skill: scan and route inbox files
│       ├── triage-needs-action/  ← Skill: reason about and plan actions
│       └── update-dashboard/     ← Skill: refresh Dashboard.md
├── Inbox/                        ← Drop files here for AI processing
├── Needs_Action/                 ← Items awaiting AI reasoning
├── Plans/                        ← AI-created multi-step plans
├── Pending_Approval/             ← Awaiting human approval
├── Approved/                     ← Human-approved actions
├── Rejected/                     ← Human-rejected actions
├── Done/                         ← Completed items
├── Logs/                         ← Audit logs (JSON, daily)
├── watchers/
│   ├── base_watcher.py           ← Abstract watcher base class
│   ├── filesystem_watcher.py     ← File system watcher (Bronze Tier)
│   └── requirements.txt          ← Python dependencies
├── CLAUDE.md                     ← Claude Code operating instructions
├── Dashboard.md                  ← Live system status
├── Company_Handbook.md           ← AI rules of engagement
└── Business_Goals.md             ← Business KPIs and context
```

---

## Quick Start

### 1. Install Python Dependencies

```bash
cd watchers/
pip install -r requirements.txt
```

### 2. Start the File System Watcher

```bash
# Dry run (safe, recommended for testing first)
python watchers/filesystem_watcher.py --dry-run

# Live mode (actually copies files)
DRY_RUN=false python watchers/filesystem_watcher.py
```

### 3. Use Claude Code Agent Skills

Open Claude Code in this vault directory:

```bash
cd AI_Employee_Vault/
claude
```

Then use the skills:

```
/process-inbox          ← Process files in /Inbox
/triage-needs-action    ← Reason about /Needs_Action items
/update-dashboard       ← Refresh Dashboard.md
```

### 4. Human-in-the-Loop Workflow

When Claude creates a file in `/Pending_Approval/`:
- **Read** the approval file to understand what action is requested
- **Move it to `/Approved/`** to authorize the action
- **Move it to `/Rejected/`** to deny the action

---

## How It Works

```
[File Dropped in /Inbox]
        │
        ▼
[filesystem_watcher.py detects it]
        │
        ▼
[Creates .md action file in /Needs_Action]
        │
        ▼
[Claude Code reads /Needs_Action via /triage-needs-action skill]
        │
        ├─── Simple task ──────────────→ Auto-resolve → Move to /Done
        │
        ├─── Multi-step task ──────────→ Create Plan.md in /Plans
        │
        └─── Needs approval ───────────→ Write to /Pending_Approval
                                              │
                                         [Human reviews]
                                              │
                                    ┌────────┴────────┐
                                    ▼                 ▼
                               /Approved/        /Rejected/
```

---

## Agent Skills Reference

| Skill | Description |
|-------|-------------|
| `/process-inbox` | Scans /Inbox, classifies files by type/priority, routes to /Needs_Action or /Done |
| `/triage-needs-action` | Reads pending items, creates plans, writes approval requests |
| `/update-dashboard` | Counts all folders, reads logs, rewrites Dashboard.md |

---

## Security

- Credentials are **never** stored in vault files
- Use `.env` file (git-ignored) for API keys
- Dry-run mode is enabled by default — set `DRY_RUN=false` to go live
- All AI actions are logged to `/Logs/YYYY-MM-DD.json`
- Sensitive actions always require human approval via `/Pending_Approval/`

---

## Next Steps (Silver Tier)

- [ ] Add Gmail Watcher (`watchers/gmail_watcher.py`)
- [ ] Add LinkedIn posting capability (MCP server)
- [ ] Implement cron scheduling for daily briefings
- [ ] Human-in-the-loop approval watcher (monitors /Approved folder)
- [ ] Ralph Wiggum loop for autonomous multi-step task completion

---

## Hackathon Submission

- **Tier:** Bronze
- **GitHub:** _Add your repo link here_
- **Demo Video:** _Add link here_
- **Submit:** https://forms.gle/JR9T1SJq5rmQyGkGA

---
*Built for Personal AI Employee Hackathon 0 — 2026*
