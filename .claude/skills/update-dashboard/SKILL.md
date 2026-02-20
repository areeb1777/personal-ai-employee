---
name: update-dashboard
description: |
  Reads the current state of all vault folders (/Inbox, /Needs_Action, /Done,
  /Pending_Approval, /Plans, /Logs) and rewrites Dashboard.md with accurate,
  up-to-date counts, recent activity, and system status.
  Use this skill to refresh the dashboard at any time.
---

# Update Dashboard

Count everything in the vault, read recent logs, and rewrite `Dashboard.md` with current data.

## Steps

### 1. Count Folder Contents

Count files in each folder:
- `/Inbox` — files waiting to be processed
- `/Needs_Action` — pending `.md` files (frontmatter `status: pending`)
- `/Pending_Approval` — approval requests awaiting human action
- `/Plans` — plans with `status: in_progress`
- `/Done` — files completed today

### 2. Read Recent Logs

Read today's log file `/Logs/{YYYY-MM-DD}.json` and extract:
- Last 5 actions taken
- Any errors in the last 24 hours
- Total tasks processed today

### 3. Check for Pending Approvals

List all `.md` files in `/Pending_Approval/` with `status: pending`:
- Approval action type
- Requested timestamp
- Expiry timestamp

### 4. Rewrite Dashboard.md

Overwrite `Dashboard.md` with the following structure:

```markdown
# AI Employee Dashboard
---
last_updated: {YYYY-MM-DD HH:MM:SS}
updated_by: claude_code
status: active
---

## System Status

| Component | Status | Last Check |
|-----------|--------|------------|
| File Watcher | ✅ Active | {timestamp} |
| Vault | ✅ Online | {timestamp} |
| Claude Code | ✅ Ready | {timestamp} |

---

## Inbox Summary

| Folder | Count |
|--------|-------|
| /Inbox | {N} |
| /Needs_Action | {N} |
| /Pending_Approval | {N} |
| /Done (today) | {N} |

---

## Recent Activity

{Last 5 log entries as bullet points:}
- [{timestamp}] {action_type}: {summary}

---

## Active Plans

{List each in-progress plan from /Plans/:}
- [{plan filename}] {objective}

---

## Pending Approvals

{List each pending approval from /Pending_Approval/:}
- [{filename}] {action} — expires {expiry}

---

## Quick Stats (This Week)

- **Tasks Processed:** {N}
- **Files Triaged:** {N}
- **Plans Created:** {N}
- **Items Completed:** {N}

---

## Notes

> Dashboard last refreshed: {timestamp}
> Run `/update-dashboard` anytime to refresh.

---
*AI Employee v0.1 — Bronze Tier*
```

### 5. Write Log Entry

Append to `/Logs/{YYYY-MM-DD}.json`:

```json
{
  "timestamp": "{ISO}",
  "action_type": "dashboard_updated",
  "actor": "claude_code",
  "result": "success"
}
```

## Rules
- Never delete or move files — read-only scan of all folders
- If a folder is empty, show `0` (not an error)
- If logs don't exist yet, show `No activity recorded today`
- Always write the log entry after updating the dashboard
