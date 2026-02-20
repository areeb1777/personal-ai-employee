---
name: process-inbox
description: |
  Scans the /Inbox folder for new files, reads their content, classifies each
  item by type and priority, and routes them to /Needs_Action or /Done.
  Also updates Dashboard.md with the results.
  Use this skill when there are unprocessed files in /Inbox.
---

# Process Inbox

Scan `/Inbox`, classify every file, route appropriately, and update the dashboard.

## Steps

### 1. Read Company Handbook
Before doing anything, read `Company_Handbook.md` to understand:
- Priority keywords
- Autonomy levels (what you can do vs. what needs approval)
- File naming conventions

### 2. Scan /Inbox
List all files in `/Inbox`. For each file:
- Read its content (if text-based) or inspect its name/extension
- Check if a companion `.md` action file already exists in `/Needs_Action`
- Skip files already processed (companion `.md` exists)

### 3. Classify Each Item
For each unprocessed file, determine:

| Attribute | Options |
|-----------|---------|
| `type` | document, spreadsheet, text, image, media, archive, unknown |
| `priority` | high (contains priority keyword), normal |
| `action_needed` | yes / no / review |

**Priority keywords** (from Company_Handbook.md):
`urgent`, `asap`, `deadline`, `overdue`, `critical`, `invoice`, `payment`, `help`, `important`

### 4. Route Each Item

| Condition | Action |
|-----------|--------|
| No action needed (e.g., reference doc) | Move to `/Done` |
| Action needed | Create `.md` file in `/Needs_Action` |
| Unknown / ambiguous | Create `.md` file in `/Needs_Action` with `status: needs_human_review` |

#### Action File Format
Create `/Needs_Action/FILE_{TIMESTAMP}_{NAME}.md`:

```markdown
---
type: file_drop
source: {original_filename}
file_type: {type}
priority: {priority}
received: {ISO timestamp}
status: pending
---

## New File Received

**File:** `{filename}`
**Type:** {type}
**Priority:** {priority}

## Suggested Actions

- [ ] {action 1}
- [ ] {action 2}

## Notes

_Add notes here._
```

### 5. Update Dashboard.md
After processing all files, update the **Inbox Summary** table in `Dashboard.md`:
- Count of files in each folder
- Add entries to **Recent Activity** section with format:
  `- [{YYYY-MM-DD HH:MM}] Processed {N} file(s) from /Inbox`

### 6. Write Log Entry
Append to `/Logs/{YYYY-MM-DD}.json`:

```json
{
  "timestamp": "{ISO}",
  "action_type": "inbox_processed",
  "actor": "claude_code",
  "files_processed": N,
  "result": "success"
}
```

## Example Output

After running this skill you should see:
- `/Needs_Action/` contains `.md` files for each processed inbox item
- `Dashboard.md` shows updated counts
- `/Logs/{today}.json` has a new entry

## Rules
- Never delete from `/Inbox` — only move to `/Needs_Action` or `/Done`
- Never send external communications — only create action files
- If unsure about a file, always route to `/Needs_Action` with `needs_human_review`
