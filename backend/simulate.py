"""
Batch simulation engine for Agentic Checkout Concierge.

Runs a control-vs-treatment simulation entirely in memory —
no DB writes, no Razorpay API calls. The rules engine is exercised
directly so the results are deterministic and fast.

Control group:   sessions that receive NO intervention (baseline).
Treatment group: sessions that go through the full rules engine.

The output is what the Metrics Dashboard and the /api/simulate/batch
endpoint expose to the frontend.
"""

import random
from datetime import datetime, timedelta

import rules_engine

# ---------------------------------------------------------------------------
# Simulation parameters
# ---------------------------------------------------------------------------

# Probability that a session emits each hesitation signal
P_IDLE = 0.5
P_BACK_BUTTON = 0.3
P_OTP_FAIL = 0.2

# Idle duration distribution (seconds) — roughly log-normal
IDLE_MEAN = 25
IDLE_STD = 10

# Order amount range in paise  (₹500 – ₹10,000)
ORDER_MIN = 50_000
ORDER_MAX = 1_000_000

# Baseline conversion rate with no intervention
BASELINE_CONVERSION_RATE = 0.55

# How much each intervention type lifts conversion probability
INTERVENTION_LIFT = {
    "offer_discount": 0.20,
    "suggest_payment_method": 0.15,
    "offer_emi": 0.18,
}

AVAILABLE_METHODS = ["card", "upi", "netbanking", "emi"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _random_order_amount() -> int:
    return random.randint(ORDER_MIN, ORDER_MAX)


def _make_event(event_type: str, ts: datetime, metadata: dict = None) -> dict:
    return {
        "event_type": event_type,
        "metadata": metadata or {},
        "created_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _make_intervention(action_type: str, ts: datetime) -> dict:
    return {
        "action_type": action_type,
        "created_at": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "outcome_response": None,
    }


def _simulate_events(order_amount: int) -> list[dict]:
    """Generate a random hesitation-signal sequence for one session."""
    events = []
    ts = datetime(2026, 9, 1, 10, 0, 0)

    if random.random() < P_IDLE:
        idle_secs = max(1, int(random.gauss(IDLE_MEAN, IDLE_STD)))
        ts += timedelta(seconds=idle_secs)
        events.append(_make_event("idle", ts, {"idle_seconds": idle_secs}))

    if random.random() < P_BACK_BUTTON:
        ts += timedelta(seconds=random.randint(5, 20))
        events.append(_make_event("back_button", ts))

    if random.random() < P_OTP_FAIL:
        ts += timedelta(seconds=random.randint(5, 30))
        events.append(_make_event("otp_fail", ts))
        if random.random() < 0.4:  # chance of a second OTP fail
            ts += timedelta(seconds=random.randint(10, 30))
            events.append(_make_event("otp_fail", ts))

    return events


def _run_single_session_treated(order_amount: int) -> dict:
    """
    Simulate one treatment session end-to-end:
    emit events one at a time, run the rules engine after each,
    stop when an intervention is triggered or events are exhausted.
    Returns a summary dict.
    """
    events = _simulate_events(order_amount)
    if not events:
        # No hesitation signals — session converts at baseline rate
        converted = random.random() < BASELINE_CONVERSION_RATE
        return {
            "intervened": False,
            "action": None,
            "converted": converted,
            "revenue": order_amount if converted else 0,
        }

    prior_interventions = []
    decision = {"action": "no_action"}
    ts = datetime(2026, 9, 1, 10, 0, 0)

    for i, _ in enumerate(events):
        decision = rules_engine.decide(
            events=events[: i + 1],
            prior_interventions=prior_interventions,
            order_amount=order_amount,
            available_payment_methods=AVAILABLE_METHODS,
            now=ts + timedelta(seconds=(i + 1) * 20),
        )
        if decision["action"] != "no_action":
            prior_interventions.append(
                _make_intervention(
                    decision["action"],
                    ts + timedelta(seconds=(i + 1) * 20),
                )
            )

    # Determine conversion
    if decision["action"] != "no_action":
        lift = INTERVENTION_LIFT.get(decision["action"], 0.10)
        converted = random.random() < (BASELINE_CONVERSION_RATE + lift)
        return {
            "intervened": True,
            "action": decision["action"],
            "converted": converted,
            "revenue": order_amount if converted else 0,
        }
    else:
        converted = random.random() < BASELINE_CONVERSION_RATE
        return {
            "intervened": False,
            "action": None,
            "converted": converted,
            "revenue": order_amount if converted else 0,
        }


def _run_single_session_control(order_amount: int) -> dict:
    """Control session: no intervention, just baseline conversion probability."""
    converted = random.random() < BASELINE_CONVERSION_RATE
    return {
        "intervened": False,
        "action": None,
        "converted": converted,
        "revenue": order_amount if converted else 0,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_batch(num_sessions: int) -> dict:
    """
    Run num_sessions split 50/50 control vs treatment.
    Returns a summary dict suitable for direct JSON serialisation.
    """
    random.seed(42)  # reproducible results for demos

    half = num_sessions // 2
    control_n = half
    treatment_n = num_sessions - half  # handles odd numbers

    control_results = [
        _run_single_session_control(_random_order_amount()) for _ in range(control_n)
    ]
    treatment_results = [
        _run_single_session_treated(_random_order_amount()) for _ in range(treatment_n)
    ]

    # --- Control metrics ---
    ctrl_converted = sum(1 for r in control_results if r["converted"])
    ctrl_revenue = sum(r["revenue"] for r in control_results)
    ctrl_conversion_rate = ctrl_converted / control_n if control_n else 0

    # --- Treatment metrics ---
    trt_converted = sum(1 for r in treatment_results if r["converted"])
    trt_revenue = sum(r["revenue"] for r in treatment_results)
    trt_conversion_rate = trt_converted / treatment_n if treatment_n else 0
    trt_intervened = sum(1 for r in treatment_results if r["intervened"])

    # --- Breakdown by intervention type ---
    breakdown: dict[str, dict] = {}
    for r in treatment_results:
        if not r["intervened"]:
            continue
        action = r["action"]
        if action not in breakdown:
            breakdown[action] = {"shown": 0, "converted": 0, "revenue_paise": 0}
        breakdown[action]["shown"] += 1
        if r["converted"]:
            breakdown[action]["converted"] += 1
            breakdown[action]["revenue_paise"] += r["revenue"]

    recovered_revenue = trt_revenue - ctrl_revenue

    return {
        "num_sessions": num_sessions,
        "control": {
            "sessions": control_n,
            "converted": ctrl_converted,
            "conversion_rate": round(ctrl_conversion_rate, 4),
            "total_revenue_paise": ctrl_revenue,
        },
        "treatment": {
            "sessions": treatment_n,
            "converted": trt_converted,
            "conversion_rate": round(trt_conversion_rate, 4),
            "total_revenue_paise": trt_revenue,
            "sessions_intervened": trt_intervened,
        },
        "recovered_revenue_paise": max(0, recovered_revenue),
        "recovered_revenue_inr": round(max(0, recovered_revenue) / 100, 2),
        "conversion_lift_pp": round((trt_conversion_rate - ctrl_conversion_rate) * 100, 2),
        "breakdown_by_intervention": breakdown,
    }
