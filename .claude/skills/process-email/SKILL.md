# Process Email

Read pending email action files in `/Needs_Action`, analyze each email, draft a response if needed, and route for approval or auto-resolve.

## When to Use

Invoke this skill when:
- New `EMAIL_*.md` files appear in `/Needs_Action` (created by gmail_watcher.py)
- The user asks to process incoming emails
- Running the daily inbox triage

## Steps

### 1. Pre-flight

Read:
- `Company_Handbook.md` — communication rules, known contacts, tone
- `Business_Goals.md` — active projects, client names

### 2. Scan /Needs_Action for Email Files

Find all files matching `EMAIL_*.md` with `status: pending`.

For each email file:

### 3. Analyze the Email

Determine:
- **Sender**: Is this a known client or contact? (Check Company_Handbook.md §5)
- **Intent**: What does the sender want? (reply, invoice, information, action, spam)
- **Priority**: High / Normal (from frontmatter `priority` field)
- **Action needed**: reply / forward / archive / escalate

### 4. Route Each Email

| Situation | Action |
|-----------|--------|
| Known contact, simple info request | Draft reply → write to /Pending_Approval |
| Invoice request from known client | Create plan → use triage-needs-action flow |
| Unknown sender | Flag as `needs_human_review` |
| Spam / no action needed | Update status to `completed`, move to /Done |
| Urgent / financial | Escalate immediately to /Pending_Approval |

### 5a. For Emails Needing a Reply — Create Approval Request

Create `/Pending_Approval/APPROVAL_send_email_{YYYY-MM-DD}_{safe_subject}.md`:

```markdown
---
type: approval_request
action: send_email
requested_by: claude_code
requested_at: {ISO timestamp}
expires_at: {ISO timestamp + 24h}
status: pending
to: {recipient email}
subject: Re: {original subject}
source_email: {EMAIL_*.md filename}
---

## Email Reply — Approval Required

**To:** {sender name} <{sender email}>
**Subject:** Re: {original subject}
**In reply to:** {brief original context}

---

## Draft Reply

{The complete email reply body — ready to send as-is or edit before approving}

---

## Original Email Summary

{1-2 sentence summary of what the original email said}

## Why I Drafted This

{1 sentence rationale}

## To Approve

Move this file to `/Approved/` — the orchestrator will send via Email MCP.

## To Reject / Edit

Move to `/Rejected/` or edit the Draft Reply above before approving.
```

### 5b. For Emails That Are Spam or No-Action-Needed

Update the email .md file frontmatter:
```yaml
status: completed
completed: {ISO timestamp}
resolution: archived — no action required
```
Move the file to `/Done/`.

### 5c. For Unknown Senders

Update frontmatter:
```yaml
status: needs_human_review
review_reason: unknown sender — cannot confirm identity
```

Add a note explaining what information is needed.

### 6. Update Dashboard.md

Update:
- **Inbox Summary** counts
- **Pending Approvals** section (add any new email drafts)
- **Recent Activity**: `- [{timestamp}] Processed {N} email(s) from /Needs_Action`

### 7. Write Log Entry

Append to `/Logs/{YYYY-MM-DD}.json`:
```json
{
  "timestamp": "{ISO}",
  "action_type": "emails_processed",
  "actor": "claude_code",
  "emails_processed": N,
  "replies_drafted": N,
  "auto_archived": N,
  "needs_human_review": N,
  "result": "success"
}
```

## Email Drafting Guidelines

- **Subject line**: Always prefix with "Re: " for replies
- **Greeting**: Use sender's first name if known
- **Tone**: Professional and concise (Company_Handbook.md §2)
- **Length**: Match the energy of the original — short email gets short reply
- **Sign-off**: "Best regards, [Owner Name]" — use name from Company_Handbook.md §1
- **Never**: Mention that this was drafted by AI unless instructed

## Rules

- NEVER send emails directly — always route through /Pending_Approval
- NEVER reply to unknown contacts without human review
- NEVER include sensitive information (credentials, private data) in drafts
- All financial email actions (invoices, payments) require plan creation first
