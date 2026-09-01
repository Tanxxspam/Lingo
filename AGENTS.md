# Agents — Agentic Checkout Concierge

This document describes the agent itself: what it perceives, how it decides, what it's allowed to do, and how it's constrained. There is deliberately **one agent with two layers**, not multiple autonomous agents — this keeps the system simple enough to fully audit within a hackathon timeframe.

---

## 1. Agent Overview

| Property | Value |
|---|---|
| Name | Checkout Concierge Agent |
| Inputs | Hesitation event stream for a single checkout session |
| Outputs | An intervention decision (or no action) + a phrased message |
| Decision authority | Bounded — cannot choose arbitrary discount amounts, payment methods not available on the order, or exceed stopping-rule limits |
| Autonomy | Semi-autonomous — decides and speaks, but every money-relevant parameter is pre-capped in code |

## 2. Layer 1 — Rules Engine (Decision Layer)

This is a deterministic Python component. It does not call any LLM and its behavior is fully predictable from its inputs.

### Inputs
- Full event history for the session: `[{type: "idle", timestamp}, {type: "back_button", timestamp}, {type: "otp_fail", timestamp}, ...]`
- Prior interventions already made in this session
- Order details from Razorpay (amount, available payment methods)

### Example decision conditions

| Condition | Decision |
|---|---|
| Idle time > 20s, no prior intervention | Offer a discount (capped %) |
| OTP failed once | Suggest switching to a different payment method |
| OTP failed twice | Suggest netbanking or UPI as a fallback, skip further OTP-based methods |
| Back-button pressed, no prior intervention | Offer EMI option if order amount is above a threshold |
| Any signal, but 2 interventions already made this session | No action (stopping rule reached) |
| Discount already rejected once | Do not offer discount again — escalate to a different intervention type |

### Output format
```json
{
  "action": "offer_discount",
  "value": "10%",
  "reason": "idle_time_exceeded_20s AND no_prior_intervention"
}
```
or
```json
{ "action": "no_action", "reason": "stopping_rule: max_interventions_reached" }
```

## 3. Layer 2 — Message Generation (LLM Layer)

This layer receives the rules engine's output and turns it into a short, conversational message. It has **no visibility into raw money-decision logic** beyond the specific decision it's asked to phrase — it cannot invent a different discount value or suggest a payment method that wasn't specified.

### Example prompt shape
```
You are a checkout assistant. Phrase this offer in one friendly sentence.
Do not change the discount value or offer type.
Decision: offer_discount, value: 10%
```

### Example output
> "Looks like you're taking your time — here's 10% off if you complete your order in the next few minutes!"

### Why this separation matters
If the LLM were allowed to decide *both* the offer type and the amount, the system would be much harder to audit and cap. By constraining the LLM to phrasing only, every money-affecting number in the system traces back to a single, testable Python function.

## 4. Stopping Rules (Enforced in Layer 1, Not Prompted)

- Max 2 interventions per session
- Minimum 15-second cooldown between interventions
- Discount capped at a fixed maximum percentage
- No repeat of a rejected intervention type within the same session
- Payment-method offers restricted to methods actually available on the Razorpay order

These are implemented as plain conditionals/config values in the rules engine — not as instructions to the LLM — so they cannot be bypassed by unexpected model output.

## 5. Audit Trail

Every decision (including `no_action`) is logged with:
- Session ID
- Triggering event(s)
- Decision made
- Reason string
- Timestamp
- Eventual outcome (accepted / rejected / no response / session converted)

This log is what the Metrics Dashboard reads from, and it's also what a judge (or you, live) can point to when explaining *why* the agent did what it did in any given session.

## 6. What This Agent Is Not

- It is **not** a fully autonomous LLM agent making free-form money decisions
- It does **not** call external tools beyond the Razorpay test-mode API and the Claude API for phrasing
- It does **not** persist or act across merchants — each session is independent
- It is **not** designed for production-scale traffic — this is a hackathon-scope proof of concept with a clear, documented upgrade path (see `README.md`, Section 9)
