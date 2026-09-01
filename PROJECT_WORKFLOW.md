# Project Workflow — Agentic Checkout Concierge

Build timeline: **August 31 – September 4** (4 days, solo build)

This document tracks the phase-by-phase process for building and submitting the project. Check items off as you go.

---

## Phase 0 — Scope Lock (Day 1, morning)

**Goal:** Define exactly what "done" looks like before writing code.

- [ ] Write a one-paragraph problem statement
- [ ] Define the 3 hesitation signals to detect: idle time, back-button, OTP failure
- [ ] Define the 3 intervention types: payment method switch, discount, EMI offer
- [ ] Define the single success metric: recovered revenue across a batch of simulated sessions
- [ ] Get Razorpay test-mode API keys from the dashboard

## Phase 1 — Architecture & Data Model (Day 1, afternoon)

**Goal:** Lock the schema and API contract before building either side.

- [ ] Design `sessions`, `events`, `interventions`, `outcomes` tables
- [ ] Define API routes: `/api/checkout/session`, `/api/checkout/event`, `/api/agent/decide`, `/api/agent/intervene`, `/api/metrics/summary`
- [ ] Sketch the sequence diagram (signal → decision → message → outcome → metrics)
- [ ] Set up the FastAPI project skeleton and SQLite DB

## Phase 2 — Agent Decision Engine (Day 1 evening – Day 2)

**Goal:** Build the deterministic core before touching the LLM.

- [ ] Implement the rules engine as plain Python conditionals or a small state machine
- [ ] Implement stopping rules: max interventions per session, cooldown, discount cap, no-repeat-offer rule
- [ ] Log every decision with a `reason` string
- [ ] Write unit tests for the rules engine using scripted event sequences (no server needed yet)
- [ ] Integrate Claude API for message phrasing only — confirm it never influences the decision itself

## Phase 3 — Razorpay Integration (Day 2)

**Goal:** Make the offers real, even in test mode.

- [ ] Create test-mode orders via Orders API
- [ ] Pull available payment methods for an order (UPI, card, netbanking, EMI-on-card)
- [ ] Generate a Payment Link for the recovered checkout flow
- [ ] Confirm the rules engine only offers payment methods that are actually available on the order

## Phase 4 — React Frontend (Day 2 – Day 3)

**Goal:** Make the hesitation signals and the agent's response visible and demoable.

- [ ] Build the simulated Checkout Page with idle timer, back-button listener, OTP failure trigger
- [ ] Build the Concierge Widget (chat-style intervention UI with accept/reject buttons)
- [ ] Wire both to the backend event and intervention endpoints
- [ ] Build the "Run Batch Simulation" control to generate N synthetic sessions at once

## Phase 5 — Metrics Dashboard (Day 3)

**Goal:** Turn logged data into the numbers judges are asked to look for.

- [ ] Build `/api/metrics/summary` aggregation endpoint
- [ ] Build the dashboard UI: baseline abandonment rate, post-intervention conversion rate, estimated revenue recovered, breakdown by intervention type
- [ ] Run a full batch simulation and record real output numbers

## Phase 6 — Polish, Docs, Submission (Day 3 evening – Day 4)

**Goal:** Package everything the judges asked for.

- [ ] Fill in the Results table in `README.md` with actual batch-run numbers
- [ ] Finalize `ARCHITECTURE.md` diagram and decision-flow description
- [ ] Record the 5-minute pitch video:
  - ~30s problem framing
  - ~2 min live demo (batch simulation + one manual walkthrough)
  - ~1 min architecture / agent logic explanation
  - ~30s metrics + future work
- [ ] Push all code and docs to the public GitHub repo
- [ ] Double-check repo visibility is public
- [ ] Submit before the September 4 deadline

---

## Definition of Done

A judge should be able to, in under 10 minutes:
1. Read `README.md` and understand the problem and approach
2. Read `ARCHITECTURE.md` and understand how the agent is bounded and audited
3. Watch the pitch video and see a batch simulation produce a real recovered-revenue number
4. Skim the code and see the rules engine as plain, inspectable logic — not a prompt doing money math
