"""
Agentic Checkout Concierge — FastAPI entrypoint.

Phase 1 scope: project skeleton + working routes wired to the DB.
Rules engine logic (Phase 2) and Razorpay integration (Phase 3) are
stubbed here with clear TODOs and will replace the placeholder logic.
"""

import json
import uuid
from datetime import datetime
from typing import Optional


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db, get_connection, row_to_dict
import rules_engine
import agent_messaging
import razorpay_client
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Agentic Checkout Concierge API")

# Allow the React dev server to call this API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# Request/response schemas
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    order_amount: int  # in paise


class CreateSessionResponse(BaseModel):
    session_id: str
    razorpay_order_id: str
    order_amount: int
    status: str


class EventRequest(BaseModel):
    session_id: str
    event_type: str  # "idle" | "back_button" | "otp_fail"
    metadata: Optional[dict] = None


class InterventionOutcomeRequest(BaseModel):
    intervention_id: int
    response: str  # "accepted" | "rejected" | "no_response"
    session_converted: bool
    revenue_amount: Optional[int] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/checkout/session", response_model=CreateSessionResponse)
def create_session(req: CreateSessionRequest):
    """Create a new checkout session backed by a real Razorpay test-mode order."""
    session_id = str(uuid.uuid4())
    order = razorpay_client.create_order(req.order_amount, receipt=session_id)

    with get_connection() as conn:
        conn.execute(
            """INSERT INTO sessions (id, razorpay_order_id, order_amount, status)
               VALUES (?, ?, ?, 'active')""",
            (session_id, order["id"], req.order_amount),
        )
        conn.commit()

    return CreateSessionResponse(
        session_id=session_id,
        razorpay_order_id=order["id"],
        order_amount=req.order_amount,
        status="active",
    )


def _get_session_context(conn, session_id: str):
    """Load full event history and prior interventions (with their outcome,
    if any) for a session — the exact inputs rules_engine.decide() needs."""
    raw_events = conn.execute(
        "SELECT * FROM events WHERE session_id = ? ORDER BY created_at", (session_id,)
    ).fetchall()
    events = []
    for e in raw_events:
        d = row_to_dict(e)
        d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
        events.append(d)

    raw_interventions = conn.execute(
        """SELECT i.*, o.response AS outcome_response
           FROM interventions i
           LEFT JOIN outcomes o ON o.intervention_id = i.id
           WHERE i.session_id = ?
           ORDER BY i.created_at""",
        (session_id,),
    ).fetchall()
    interventions = [row_to_dict(i) for i in raw_interventions]

    return events, interventions


@app.post("/api/checkout/event")
def log_event(req: EventRequest):
    """
    Ingest a hesitation signal from the frontend, run it through the rules
    engine, and — if an intervention is warranted — generate the phrased
    message and persist everything for the audit trail.
    """
    with get_connection() as conn:
        session = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (req.session_id,)
        ).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        cursor = conn.execute(
            """INSERT INTO events (session_id, event_type, metadata)
               VALUES (?, ?, ?)""",
            (req.session_id, req.event_type, json.dumps(req.metadata or {})),
        )
        event_id = cursor.lastrowid

        events, prior_interventions = _get_session_context(conn, req.session_id)

        available_payment_methods = razorpay_client.get_available_payment_methods(
            session["order_amount"]
        )

        decision = rules_engine.decide(
            events=events,
            prior_interventions=prior_interventions,
            order_amount=session["order_amount"],
            available_payment_methods=available_payment_methods,
        )

        message = ""
        intervention_id = None
        if decision["action"] != "no_action":
            message = agent_messaging.generate_message(decision)
            cursor = conn.execute(
                """INSERT INTO interventions
                   (session_id, triggering_event_id, action_type, action_value, reason, message_shown)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    req.session_id,
                    event_id,
                    decision["action"],
                    decision["value"],
                    decision["reason"],
                    message,
                ),
            )
            intervention_id = cursor.lastrowid

        conn.commit()

    return {
        "event_id": event_id,
        "decision": decision,
        "message": message,
        "intervention_id": intervention_id,
    }


@app.post("/api/agent/intervene")
def log_outcome(req: InterventionOutcomeRequest):
    """Record the user's response to an intervention and whether the session converted."""
    with get_connection() as conn:
        intervention = conn.execute(
            "SELECT * FROM interventions WHERE id = ?", (req.intervention_id,)
        ).fetchone()
        if not intervention:
            raise HTTPException(status_code=404, detail="Intervention not found")

        conn.execute(
            """INSERT INTO outcomes (intervention_id, response, session_converted, revenue_amount)
               VALUES (?, ?, ?, ?)""",
            (req.intervention_id, req.response, req.session_converted, req.revenue_amount),
        )

        if req.session_converted:
            conn.execute(
                "UPDATE sessions SET status = 'converted', updated_at = ? WHERE id = ?",
                (datetime.utcnow(), intervention["session_id"]),
            )
        conn.commit()

    return {"status": "recorded"}


@app.post("/api/checkout/session/{session_id}/payment-link")
def create_recovery_payment_link(session_id: str):
    """
    Generate a Razorpay Payment Link for the recovered checkout — call
    this once the user accepts an intervention (e.g. switches payment
    method), so they have a fresh, completable payment flow to use.
    """
    with get_connection() as conn:
        session = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

    link = razorpay_client.create_payment_link(
        order_amount_paise=session["order_amount"],
        description="Complete your order — Agentic Checkout Concierge",
    )
    return link


@app.get("/api/metrics/summary")
def metrics_summary():
    """
    Aggregate recovered-revenue metrics across all sessions.

    TODO (Phase 5): expand this into the full baseline-vs-treated
    comparison described in the metrics definition doc.
    """
    with get_connection() as conn:
        total_sessions = conn.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
        converted_sessions = conn.execute(
            "SELECT COUNT(*) AS c FROM sessions WHERE status = 'converted'"
        ).fetchone()["c"]
        recovered_revenue = conn.execute(
            """SELECT COALESCE(SUM(o.revenue_amount), 0) AS total
               FROM outcomes o
               JOIN interventions i ON o.intervention_id = i.id
               WHERE o.session_converted = 1 AND i.action_type != 'no_action'"""
        ).fetchone()["total"]

    return {
        "total_sessions": total_sessions,
        "converted_sessions": converted_sessions,
        "recovered_revenue_paise": recovered_revenue,
    }


class BatchSimulationRequest(BaseModel):
    num_sessions: int = 100


@app.post("/api/simulate/batch")
def simulate_batch(req: BatchSimulationRequest):
    """
    Run a control-vs-treatment batch simulation using the real rules
    engine. Does not touch the database — see simulate.py for why.
    """
    if req.num_sessions < 1 or req.num_sessions > 5000:
        raise HTTPException(status_code=400, detail="num_sessions must be between 1 and 5000")
    return simulate.run_batch(req.num_sessions)


@app.get("/api/checkout/session/{session_id}")
def get_session(session_id: str):
    """Fetch a session's current state — useful for debugging during Phase 1-2."""
    with get_connection() as conn:
        session = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        events = conn.execute(
            "SELECT * FROM events WHERE session_id = ? ORDER BY created_at", (session_id,)
        ).fetchall()

    return {
        "session": row_to_dict(session),
        "events": [row_to_dict(e) for e in events],
    }