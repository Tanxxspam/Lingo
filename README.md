# Agentic Checkout Concierge

**Track:** AI Revenue Recovery — Razorpay AI Buildathon
**Author:** [Your Name]
**Status:** Hackathon submission (solo build)

An AI agent that watches for checkout hesitation signals — idle time, back-button presses, failed OTP attempts — and steps in conversationally to save the sale before the customer bounces, by offering the right payment method switch, an instant discount, or an EMI option.

---

## 1. Problem Statement

Checkout abandonment rarely happens for one clean reason. A customer stalls, hits back, or fails an OTP — and most merchants only find out after the fact, from a drop in conversion numbers. By then the revenue is already gone.

**Agentic Checkout Concierge** detects hesitation *while it's happening* and intervenes in real time with a bounded, explainable offer — instead of a generic "complete your order!" popup.

## 2. What It Does

1. Monitors a live checkout session for hesitation signals:
   - Idle time above a threshold
   - Browser back-button press
   - Failed OTP attempt(s)
2. A rule-based decision layer decides **whether** to intervene and **what type** of offer to make (payment method switch, discount, EMI) — kept fully deterministic and auditable.
3. An LLM layer (Claude API) generates the **natural-language message** for that decision — it phrases the offer, it does not decide the offer.
4. The offer is shown in a conversational widget on the checkout page. Every decision, offer, and outcome is logged.
5. A metrics dashboard aggregates results across simulated sessions: baseline abandonment rate vs. post-intervention conversion, and estimated revenue recovered.

## 3. Why This Design (Judging Criteria Alignment)

The Buildathon's bar for this track is: *"Don't just identify the problem. Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail."*

This project is built directly around that bar:

| Requirement | How it's met |
|---|---|
| Explainable, bounded, gated actions | Rule engine decides offers via explicit, inspectable conditions — no black-box agent decisions on money actions |
| Stopping rules | Max interventions per session, cooldown between nudges, hard cap on discount % (see `ARCHITECTURE.md`) |
| Audit trail | Every event, decision, and outcome is persisted with a reason string |
| Measured money recovered | Batch simulation mode runs N synthetic sessions and reports recovered revenue, not a single cherry-picked demo |

## 4. Tech Stack

- **Backend:** Python, FastAPI, SQLite (demo-scale storage)
- **Frontend:** React
- **Payments:** Razorpay Orders API + Payment Links API (test mode)
- **Conversational layer:** Claude API (message generation only, not decisioning)

## 5. Project Structure

```
agentic-checkout-concierge/
├── backend/
│   ├── main.py                # FastAPI app entrypoint
│   ├── models.py               # DB models (sessions, events, interventions, outcomes)
│   ├── rules_engine.py         # Deterministic decision logic + stopping rules
│   ├── agent_messaging.py      # Claude API call for offer phrasing
│   ├── razorpay_client.py      # Test-mode Orders/Payment Links integration
│   └── metrics.py              # Aggregation for the dashboard
├── frontend/
│   ├── src/
│   │   ├── CheckoutPage.jsx    # Simulated checkout with hesitation triggers
│   │   ├── ConciergeWidget.jsx # Chat-style intervention UI
│   │   └── MetricsDashboard.jsx
├── ARCHITECTURE.md
└── README.md
```

## 6. Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Create a `.env` file with:
```
RAZORPAY_KEY_ID=your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
ANTHROPIC_API_KEY=your_api_key
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 7. Demo Instructions

1. Start backend and frontend as above.
2. Open the checkout page and either:
   - Manually trigger signals (sit idle, click back, fail the OTP field), **or**
   - Click **"Run Batch Simulation"** to generate N synthetic sessions at once
3. Open the Metrics Dashboard to see:
   - Baseline abandonment rate
   - Post-intervention conversion rate
   - Estimated revenue recovered
   - Breakdown by intervention type

## 8. Results (fill in after your batch run)

| Metric | Value |
|---|---|
| Sessions simulated | — |
| Baseline abandonment rate | — |
| Recovery rate after intervention | — |
| Estimated revenue recovered | — |
| Best-performing intervention type | — |

## 9. Limitations & Future Work

- Synthetic hesitation signals for demo purposes; production would use real behavioral telemetry
- EMI offer is surfaced as a payment-method option, not a full EMI calculator
- Single-merchant simulation; multi-merchant support is a natural next step
- No real OTP/SMS integration — OTP failure is mocked

## 10. Track & Submission

- **Track:** AI Revenue Recovery
- **Repo:** public (this repo)
- **Architecture:** see `ARCHITECTURE.md`
- **Pitch video:** [link]
