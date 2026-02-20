---
name: triage-needs-action
description: |
  Reads all pending items in /Needs_Action, reasons about each one, creates
  Plan.md files for multi-step tasks, and routes items that need human approval
  to /Pending_Approval. Updates Dashboard.md afterward.
  Use this skill to process the /Needs_Action queue.
---

# Triage Needs Action

Process every pending item in `/Needs_Action`, create plans, and request approvals where needed.

## Pre-flight Checks

1. Read `Company_Handbook.md` — understand autonomy levels and approval rules
2. Read `Dashboard.md` — understand current system state
3. Read `Business_Goals.md` — understand business context

## Step-by-Step Process

### 1. Scan /Needs_Action
List all `.md` files where frontmatter `status: pending`.

For each pending file:

### 2. Analyze the Item
Read the full content and determine:
- **What is this?** (email, file drop, task, request, etc.)
- **What action is needed?** (reply, review, forward, create document, etc.)
- **Can I act autonomously?** (check Company_Handbook.md autonomy levels)
- **Is this high priority?** (check priority field or keywords)

### 3. Decide the Route

| Situation | Action |
|-----------|--------|
| Simple, auto-approved action | Complete it and move item to `/Done` |
| Multi-step task | Create a Plan.md in `/Plans/` |
| Needs human approval | Write approval request to `/Pending_Approval/` |
| Needs more information | Update item with `status: needs_human_review` and note |

### 4a. For Multi-Step Tasks — Create a Plan

Create `/Plans/PLAN_{TOPIC}_{YYYY-MM-DD}.md`:

```markdown
---
created: {ISO timestamp}
status: in_progress
related_item: {source filename}
---

## Objective
{Clear description of the goal}

## Steps
- [ ] Step 1: {action}
- [ ] Step 2: {action}
- [ ] Step 3: {action}

## Notes
{Any context, constraints, or considerations}
```

### 4b. For Actions Requiring Approval — Write to /Pending_Approval

Create `/Pending_Approval/APPROVAL_{ACTION}_{YYYY-MM-DD}.md`:

```markdown
---
type: approval_request
action: {action type}
requested: {ISO timestamp}
expires: {ISO timestamp + 24h}
status: pending
---

## What I Want to Do
{Clear description of the proposed action}

## Why
{Reasoning and context}

## Risk Assessment
- **Reversible?** {yes/no}
- **Impact:** {low/medium/high}

## To Approve
Move this file to `/Approved`

## To Reject
Move this file to `/Rejected`
```

### 4c. For Items That Can Be Auto-Resolved
Update the `.md` file frontmatter:
```yaml
status: completed
completed: {ISO timestamp}
resolution: {brief description}
```
Then move the file to `/Done/`.

### 5. Update Dashboard.md
After processing all items, update:
- **Inbox Summary** counts
- **Active Plans** section (list any new plans)
- **Pending Approvals** section (list any new approval requests)
- **Recent Activity** with: `- [{timestamp}] Triaged {N} item(s) from /Needs_Action`

### 6. Write Log Entry
Append to `/Logs/{YYYY-MM-DD}.json`:

```json
{
  "timestamp": "{ISO}",
  "action_type": "needs_action_triaged",
  "actor": "claude_code",
  "items_processed": N,
  "plans_created": N,
  "approvals_requested": N,
  "auto_resolved": N,
  "result": "success"
}
```

## Rules
- High-priority items are processed first
- Never take irreversible actions without an approval file
- Never send external messages — only draft and request approval
- Always update Dashboard.md at the end
- Log every action taken
