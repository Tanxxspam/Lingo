"""
Rules engine for Agentic Checkout Concierge.

Deterministic decision logic. No LLM calls happen here — this module
decides WHETHER to intervene and WHAT to offer. Message phrasing is a
separate concern (see agent_messaging.py) so that every money-affecting
decision stays inspectable and testable in isolation.

See AGENTS.md for the full design rationale.
"""

from datetime import datetime
from typing import Optional

# --- Stopping rules / thresholds (hardcoded, not LLM-configurable) ---
MAX_INTERVENTIONS_PER_SESSION = 2
COOLDOWN_SECONDS = 15
IDLE_THRESHOLD_SECONDS = 20
DISCOUNT_CAP_PERCENT = 10
EMI_THRESHOLD_PAISE = 500_000  # ₹5,000 — orders at/above this may get EMI offers

SQLITE_TS_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_ts(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts
    return datetime.strptime(ts.split(".")[0], SQLITE_TS_FORMAT)


def no_action(reason: str) -> dict:
    return {"action": "no_action", "value": None, "reason": reason}


def _pick_alternate_method(available_methods: list, exclude: list) -> Optional[str]:
    for method in available_methods:
        if method not in exclude:
            return method
    return None


def decide(
    events: list[dict],
    prior_interventions: list[dict],
    order_amount: int,
    available_payment_methods: list[str],
    now: Optional[datetime] = None,
) -> dict:
    """
    Decide whether to intervene and what to offer, based on the full
    event history and prior interventions for a session.

    Args:
        events: list of event dicts, ordered oldest -> newest, each with
                at least {event_type, metadata, created_at}
        prior_interventions: list of intervention dicts already made this
                session, each with {action_type, reason, created_at,
                outcome_response} (outcome_response may be None if the
                user hasn't responded yet)
        order_amount: order amount in paise
        available_payment_methods: methods actually available on the
                Razorpay order, e.g. ["card", "upi", "netbanking", "emi"]
        now: injectable clock for testing; defaults to current UTC time

    Returns:
        A decision dict: {"action": ..., "value": ..., "reason": ...}
    """
    now = now or datetime.utcnow()  # naive UTC, matching SQLite's CURRENT_TIMESTAMP

    if not events:
        return no_action("no_events_yet")

    # --- Stopping rule: max interventions per session ---
    if len(prior_interventions) >= MAX_INTERVENTIONS_PER_SESSION:
        return no_action(
            f"stopping_rule: max_interventions_reached ({MAX_INTERVENTIONS_PER_SESSION})"
        )

    # --- Stopping rule: cooldown between interventions ---
    if prior_interventions:
        last_time = _parse_ts(prior_interventions[-1]["created_at"])
        elapsed = (now - last_time).total_seconds()
        if elapsed < COOLDOWN_SECONDS:
            return no_action(
                f"stopping_rule: cooldown_active ({elapsed:.0f}s < {COOLDOWN_SECONDS}s)"
            )

    rejected_types = {
        i["action_type"] for i in prior_interventions if i.get("outcome_response") == "rejected"
    }

    latest_event = events[-1]
    event_type = latest_event["event_type"]
    metadata = latest_event.get("metadata") or {}

    # --- Idle time ---
    if event_type == "idle":
        idle_seconds = metadata.get("idle_seconds", 0)
        if idle_seconds < IDLE_THRESHOLD_SECONDS:
            return no_action(f"idle_time_below_threshold ({idle_seconds}s < {IDLE_THRESHOLD_SECONDS}s)")

        if "offer_discount" in rejected_types:
            # Discount already rejected once this session — don't repeat it.
            # Escalate to a payment-method suggestion instead, if one hasn't
            # already been tried, otherwise stand down.
            if "suggest_payment_method" not in {i["action_type"] for i in prior_interventions}:
                method = _pick_alternate_method(available_payment_methods, exclude=["card"])
                if method:
                    return {
                        "action": "suggest_payment_method",
                        "value": method,
                        "reason": "idle_time_exceeded AND discount_already_rejected, escalating",
                    }
            return no_action("idle_time_exceeded but discount_already_rejected and no_alternate_left")

        return {
            "action": "offer_discount",
            "value": f"{DISCOUNT_CAP_PERCENT}%",
            "reason": f"idle_time_exceeded_{IDLE_THRESHOLD_SECONDS}s AND no_prior_intervention",
        }

    # --- OTP failure ---
    if event_type == "otp_fail":
        otp_fail_count = sum(1 for e in events if e["event_type"] == "otp_fail")

        if otp_fail_count == 1:
            method = _pick_alternate_method(available_payment_methods, exclude=["card"])
            if not method:
                return no_action("otp_failed_once but no_alternate_payment_method_available")
            return {
                "action": "suggest_payment_method",
                "value": method,
                "reason": "otp_failed_once",
            }

        # Two or more OTP failures — steer away from OTP-based methods entirely.
        method = _pick_alternate_method(available_payment_methods, exclude=["card"])
        if not method:
            return no_action("otp_failed_repeatedly but no_alternate_payment_method_available")
        return {
            "action": "suggest_payment_method",
            "value": method,
            "reason": "otp_failed_repeatedly, steering away from OTP-based methods",
        }

    # --- Back button ---
    if event_type == "back_button":
        if order_amount >= EMI_THRESHOLD_PAISE and "emi" in available_payment_methods:
            return {
                "action": "offer_emi",
                "value": "emi",
                "reason": f"back_button_pressed AND order_amount>={EMI_THRESHOLD_PAISE}_paise",
            }

        if "offer_discount" in rejected_types:
            return no_action("back_button_pressed but discount_already_rejected and order_below_emi_threshold")

        return {
            "action": "offer_discount",
            "value": f"{DISCOUNT_CAP_PERCENT}%",
            "reason": "back_button_pressed AND order_amount_below_emi_threshold",
        }

    return no_action(f"unhandled_event_type: {event_type}")