# Draft LinkedIn Post

Generate a LinkedIn post for business promotion, write it to `/Pending_Approval/`, and update the dashboard.

## When to Use

Invoke this skill to:
- Automatically post about business wins, services, or updates on LinkedIn
- Draft posts for human review before publishing
- Create thought-leadership content based on Business_Goals.md

## Steps

### 1. Read Business Context

Read these files to understand what to post about:
- `Business_Goals.md` — current objectives, revenue targets, active projects
- `Company_Handbook.md` — tone, style, communication rules
- `Dashboard.md` — recent completions and wins

### 2. Generate Post Content

Write a LinkedIn post that:
- Is **professional and concise** (150–300 words optimal)
- Highlights a **business win, service, insight, or update**
- Uses **3-5 relevant hashtags** at the end
- Does NOT include pricing unless explicitly instructed
- Matches the tone in Company_Handbook.md (professional, no slang)
- Ends with a clear **call-to-action** (e.g., "DM me", "Learn more", "Let's connect")

### 3. Write Approval Request

Create `/Pending_Approval/LINKEDIN_POST_{YYYY-MM-DD}_{TOPIC}.md`:

```markdown
---
type: approval_request
action: linkedin_post
requested_by: claude_code
requested_at: {ISO timestamp}
expires_at: {ISO timestamp + 48h}
status: pending
topic: {brief topic description}
---

## LinkedIn Post — Approval Required

**Action:** Publish a LinkedIn post
**Scheduled for:** Upon approval
**Author:** {PERSON_URN or ORG_URN from .env}

---

## Post Content

{The complete LinkedIn post text goes here — exactly as it will appear}

---

## Why This Post

{1-2 sentences explaining the business rationale and expected impact}

## To Approve

Move this file to `/Approved/` — the LinkedIn watcher will publish it automatically.

## To Reject

Move this file to `/Rejected/` with an optional note.

## To Edit

Edit the "Post Content" section above, then move to `/Approved/`.
```

### 4. Update Dashboard.md

Add an entry to **Pending Approvals**:
```
- [LINKEDIN_POST_{date}_{topic}.md] LinkedIn post draft — expires {expiry}
```

Add to **Recent Activity**:
```
- [{timestamp}] LinkedIn post drafted: {topic} — awaiting approval
```

### 5. Write Log Entry

Append to `/Logs/{YYYY-MM-DD}.json`:
```json
{
  "timestamp": "{ISO}",
  "action_type": "linkedin_post_drafted",
  "actor": "claude_code",
  "topic": "{topic}",
  "approval_file": "LINKEDIN_POST_{date}_{topic}.md",
  "result": "pending_approval"
}
```

## Post Quality Rules

- **One clear message per post** — don't cram multiple topics
- **Hook in first line** — the first sentence must grab attention (no "Hello LinkedIn!")
- **Hashtags**: 3-5, placed at end, relevant to content
- **No direct selling** unless user explicitly requests promotional post
- **Always professional** — per Company_Handbook.md §2 tone guidelines

## Example Post Topics (pick based on Business_Goals.md)

- Project completion announcement
- Industry insight or tip
- Client success story (anonymized if needed)
- Service spotlight
- Business milestone (revenue, clients, etc.)
- Thought leadership on a relevant topic

## Rules

- NEVER publish directly — always write to `/Pending_Approval/` first
- NEVER share client names without instruction
- The LinkedIn watcher (orchestrator.py) handles actual publishing after approval
- Always base content on real context from vault files — never fabricate
