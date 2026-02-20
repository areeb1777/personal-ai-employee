---
created: 2026-02-20T16:30:00
status: in_progress
related_item: FILE_20260220_162039_urgent_invoice_test.md
source_file: urgent_invoice_test.txt
priority: high
created_by: claude_code
---

## Objective

Review and process an invoice received from an unknown client. Determine legitimacy, identify the sender, and escalate any financial action for human approval before proceeding.

## Context

An invoice was dropped into /Inbox with the content:
> "Test invoice from client"

The sender is unidentified. No amount, due date, or line items are present in the file. This may be a test drop or an incomplete submission. Business Goal: invoice payment rate target is >90% — all invoices should be actioned promptly.

## Steps

- [ ] **Step 1 — Identify the sender**
  - Who dropped this file? Check email/inbox/communications for a matching invoice from a known client.
  - If sender is unknown → do NOT proceed with payment until identified (Handbook §3: unknown contacts require approval).

- [ ] **Step 2 — Locate the full invoice document**
  - The file content is minimal ("Test invoice from client") — the actual invoice details (amount, due date, line items, payment terms) may be in a separate document or attachment.
  - Request the full invoice from the sender if incomplete.

- [ ] **Step 3 — Verify invoice legitimacy**
  - Match against active projects listed in `Business_Goals.md`
  - Confirm work/goods were received
  - Check for duplicate invoice numbers

- [ ] **Step 4 — Human review and approval**
  - Present verified invoice details to human owner
  - Request approval via `/Pending_Approval/` before any payment action
  - Per Handbook §3: all financial actions require approval regardless of amount

- [ ] **Step 5 — Process payment (post-approval only)**
  - Only after explicit human approval
  - Log payment action in `/Logs/`
  - Note: Payment transfers are "Never Do Autonomously" per Handbook §3

- [ ] **Step 6 — File and archive**
  - Move `urgent_invoice_test.txt` to `/Done/`
  - Mark action file as `status: completed`
  - Update Dashboard.md

## Constraints

- ⚠️ **Do not make any payment without explicit human approval**
- ⚠️ **Do not contact the sender until identity is confirmed** (unknown contact rule)
- Invoice payment rate KPI: > 90% — timely processing matters

## Notes

This item arrived as a plain text file with minimal content. It may be a system test or an incomplete invoice drop. Human should clarify if this is a real invoice or a test before proceeding to Steps 2–6.

**Waiting on human:** Please confirm whether this is a real invoice or a test, and provide sender identity.
