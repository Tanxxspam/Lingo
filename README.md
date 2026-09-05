# Agentic Checkout Concierge

> Real-time behavioral intervention engine that detects cart abandonment signals and recovers lost revenue before the tab closes.

Built for Hackathon (August 31 – September 4)

---
cd
## The Problem

Cart abandonment rates average 70%. Merchants typically attempt recovery via email or SMS 2 to 4 hours after a drop-off, when buyer purchase intent has cooled. The Agentic Checkout Concierge detects micro-hesitations directly on the checkout screen (idle delays, navigation drop-off, OTP errors) and intervenes dynamically before abandonment occurs.

---

## Features

- **Deterministic Guardrails:** Business decisions, discount caps, and cooldowns are managed by pure Python logic — zero hallucinated numbers.
- **Micro-Hesitation Triggers:** Detects idle timeouts (>20s), back-button clicks, and OTP entry failures.
- **Contextual Interventions:** Dynamically serves UPI method switches, capped instant discounts, or cardless EMI options.
- **Test-Mode Razorpay Integration:** Generates valid recovery payment links and verifies method availability.
- **Synthetic Batch Simulation Engine:** Evaluates recovery rates and recovered GMV over batches of up to 5,000 simulated user sessions.

---

## Evaluation & Results

Results from a 50-session synthetic batch simulation:

| Metric | Without Concierge | With Concierge | Lift / Delta |
| :--- | :--- | :--- | :--- |
| **Total Sessions** | 50 | 50 | — |
| **Drop-off / Hesitation Rate** | 70.0% (35 sessions) | 38.0% (19 unrecovered) | **-32.0%** abandonment |
| **Recovery Conversion Rate** | 0.0% | 45.7% (16 saved) | **+45.7%** conversion |
| **Recovered Revenue (GMV)** | ₹0.00 | ₹42,850.00 | **+₹42,850.00** recovered |

---

## Why This Design (Judging Criteria Alignment)

The Buildathon's bar for this track is: *"Don't just identify the problem. Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail."*

| Requirement | How it's met |
| :--- | :--- |
| Explainable, bounded, gated actions | Rules engine decides offers via explicit, inspectable conditions — no black-box agent decisions on money actions |
| Stopping rules | Max 2 interventions per session, 15s cooldown between nudges, hard cap on discount % |
| Audit trail | Every event, decision, and outcome is persisted with a `reason` string |
| Measured money recovered | Batch simulation runs N synthetic sessions and reports recovered revenue, not a single cherry-picked demo |

---

## Tech Stack

- **Backend:** Python, FastAPI, SQLite
- **Frontend:** React + Vite, Tailwind CSS
- **Payments:** Razorpay Orders API + Payment Links API (test mode)
- **Conversational layer:** Claude API (message phrasing only — not decisioning)

---

## Project Structure

```text
├── backend/
│   ├── main.py              # FastAPI application and route endpoints
│   ├── database.py          # SQLite schema and connection helpers
│   ├── rules_engine.py      # Deterministic state machine & stopping rules
│   ├── agent_messaging.py   # Claude API wrapper (phrasing only)
│   ├── razorpay_client.py   # Orders API + Payment Links integration
│   ├── simulate.py          # Synthetic batch session generator
│   └── test_rules_engine.py # Unit tests for the rules engine
├── frontend/
│   └── my-react-app/
│       └── src/
│           ├── components/  # CheckoutPage, ConciergeWidget, MetricsDashboard, BatchSimulationPanel
│           ├── lib/         # Formatting utilities
│           └── api.js       # Typed API client
├── ARCHITECTURE.md          # Guardrails, sequence diagrams & audit design
├── AGENTS.md                # Agent design: layers, stopping rules, audit trail
└── README.md
```

---

## Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

Create a `.env` file inside `backend/`:

```
RAZORPAY_KEY_ID=your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
ANTHROPIC_API_KEY=your_api_key
```

### Frontend

```bash
cd frontend/my-react-app
npm install
npm run dev
```

The Vite dev server proxies all `/api/*` requests to `http://127.0.0.1:8000` automatically.

---

## Demo Instructions

1. Start backend and frontend as above.
2. Open `http://localhost:5173` in your browser.
3. On the checkout page, either:
   - Use the **demo controls** to manually fire idle / back-button / OTP-failure signals, or
   - Simply sit idle for 20 seconds to trigger a real detection
4. Watch the Concierge Widget appear with a contextual offer.
5. Click **"Run Batch Simulation"** to generate N synthetic sessions at once and see recovered revenue at scale.
6. Open the **Metrics Dashboard** to track live conversion and revenue numbers.

---

## Agent Architecture (Summary)

The agent has two deliberate layers:

**Layer 1 — Rules Engine (deterministic Python)**
Decides *whether* to intervene and *what* to offer, based on the session's event history and stopping rules. No LLM involvement. Every decision produces a logged `reason` string.

**Layer 2 — Message Generation (Claude API)**
Receives the already-made decision and phrases it as a single friendly sentence. Cannot change the offer type or value — only words it naturally.

This separation means every money-affecting number in the system traces back to a single, testable Python function. See `AGENTS.md` for full detail.

---

## Limitations & Future Work

- Hesitation signals are synthetic for demo purposes; production would use real behavioral telemetry
- EMI offer surfaces as a payment-method option, not a full EMI calculator
- Single-merchant simulation; multi-merchant support is a natural next step
- No real OTP/SMS integration — OTP failure is mocked on the frontend

---

## Track & Submission

- **Track:** AI Revenue Recovery — Razorpay AI Buildathon
- **Repo:** public (this repo)
- **Architecture:** see `ARCHITECTURE.md`
- **Agent design:** see `AGENTS.md`
- **Pitch video:** [link]
