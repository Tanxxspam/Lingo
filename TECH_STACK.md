# Tech Stack — Agentic Checkout Concierge

## Backend

| Component | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Personal stack, fast to iterate in a hackathon timeframe |
| Web framework | FastAPI | Async support for real-time event ingestion; auto-generated OpenAPI docs help with quick testing |
| Server | Uvicorn | Standard ASGI server for FastAPI |
| Database | SQLite | Zero-setup, file-based, sufficient for hackathon-scale demo data; upgrade path to Postgres if needed |
| ORM | SQLAlchemy (or raw `sqlite3` if time is tight) | Simple schema, four tables |
| Env management | `python-dotenv` | Keep API keys out of source |

## Frontend

| Component | Choice | Why |
|---|---|---|
| Framework | React (Vite) | Personal stack; Vite gives fast dev server startup, important under time pressure |
| Styling | Plain CSS or Tailwind | Tailwind speeds up building the checkout + widget UI without custom CSS overhead |
| State | React `useState`/`useEffect` | No need for Redux at this scale |
| Charts | Recharts or Chart.js | For the Metrics Dashboard (conversion rates, revenue recovered) |
| HTTP client | `fetch` or Axios | Either is fine; Axios simplifies error handling slightly |

## Payments

| Component | Choice | Why |
|---|---|---|
| Payment gateway | Razorpay (test mode) | Required by the hackathon; free test-mode keys, no real transactions |
| APIs used | Orders API, Payment Links API | Orders API creates the checkout order; Payment Links generates a shareable/completable payment flow for the "recovered" checkout |
| Payment methods surfaced | UPI, Card, Netbanking, EMI-on-card | These map directly to the three intervention types (method switch, discount via order amount adjustment, EMI offer) |

## AI / Agent Layer

| Component | Choice | Why |
|---|---|---|
| Decision logic | Plain Python (rules engine / state machine) | Keeps money-affecting decisions deterministic, inspectable, and bounded — required by the hackathon's judging bar |
| Message generation | Claude API (Anthropic) | Used only to phrase the already-decided offer in natural language — not to make the offer decision |
| Prompting approach | Structured input (decision type + value) → natural-language output | Prevents the LLM from having any say in *what* is offered, only *how* it's worded |

## Dev / Ops

| Component | Choice | Why |
|---|---|---|
| Version control | Git + public GitHub repo | Required submission format |
| Environment variables | `.env` (gitignored) | Keeps Razorpay and Anthropic keys out of the public repo |
| Testing | `pytest` for the rules engine | Rules engine is the most judge-scrutinized part — worth having explicit test cases for stopping rules |
| Docs | Markdown (`README.md`, `ARCHITECTURE.md`, `PROJECT_WORKFLOW.md`, `AGENTS.md`) | Required alongside the code and pitch video |

## Explicit Non-Choices (and why)

- **No message queue / Kafka** — overkill for a single-session demo; direct HTTP calls are sufficient
- **No Postgres/Redis** — adds setup time with no benefit at this scale; SQLite is enough to demonstrate the audit trail
- **No fine-tuned model** — the Claude API's base model is more than sufficient for phrasing short offers; fine-tuning would cost time with no judging benefit
- **No real OTP/SMS provider** — OTP failure is mocked client-side; wiring a real SMS provider adds cost and complexity without adding signal for judges
