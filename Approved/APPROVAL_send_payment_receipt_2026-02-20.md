---
type: approval_request
action: send_payment_receipt
requested_by: claude_code
requested_at: 2026-02-20T16:27:00
status: pending
expires_at: 2026-02-21T16:27:00
source_file: payment_receipt_request.txt
priority: high
---

## Approval Required — Send Payment Receipt

**Requested Action:** Send a payment receipt to an unspecified requester.

**Trigger File:** `payment_receipt_request.txt`

**File Content:**
> Please send me a payment receipt

---

## Why This Needs Approval

Per **Company_Handbook.md §3**, the following are required for this action:
1. **External communication** — Sending any document externally requires approval
2. **Financial record** — Payment receipts are financial documents
3. **Unknown contact** — The requester has not been identified

---

## Questions for Human Review

- [ ] Who is requesting this receipt? (Name / email / contact)
- [ ] Which payment does this receipt relate to? (Date, amount, invoice #)
- [ ] Is this requester a known client or contact?
- [ ] Which format should the receipt be sent in? (PDF, email, etc.)
- [ ] What channel should it be sent through?

---

## Actions

**To APPROVE:** Move this file to `/Approved/` and provide answers to the questions above in the Notes section.

**To REJECT:** Move this file to `/Rejected/` with a reason.

---

## Notes

_Add context, answers, or instructions here before approving._
