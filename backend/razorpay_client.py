"""
Razorpay integration for Agentic Checkout Concierge — test mode only.

Two real API calls are made here: Orders API (client.order.create) and
Payment Links API (client.payment_link.create). Payment-method
availability is NOT a live Razorpay API call — Razorpay doesn't expose a
"which methods apply to this specific order" endpoint. Instead it's a
config-driven function that mirrors how a merchant's enabled methods and
an order's EMI eligibility actually work, kept in sync with
rules_engine.EMI_THRESHOLD_PAISE so the rules engine never offers a
method that wouldn't really be available.
"""

import os

import rules_engine

# Methods this (fictional) merchant has enabled in their Razorpay dashboard.
# In production this would be read from your account's payment method
# configuration rather than hardcoded.
ENABLED_METHODS = ["card", "upi", "netbanking", "emi"]

_client = None


def _get_client():
    """Lazily import and construct the Razorpay client, so this module
    (and its pure functions) still work even without the package
    installed — same pattern as agent_messaging.py."""
    global _client
    if _client is None:
        import razorpay

        key_id = os.environ.get("RAZORPAY_KEY_ID")
        key_secret = os.environ.get("RAZORPAY_KEY_SECRET")
        _client = razorpay.Client(auth=(key_id, key_secret))
    return _client


def create_order(order_amount_paise: int, receipt: str = None, notes: dict = None) -> dict:
    """
    Create a test-mode Razorpay order.

    Returns a dict with at least {"id": ..., "amount": ..., "currency": ...}.
    Falls back to a fake local order id if the API call fails (missing
    keys, no network, etc.) so the demo never breaks on this call alone —
    same resilience pattern as agent_messaging's fallback.
    """
    try:
        client = _get_client()
        order = client.order.create(
            {
                "amount": order_amount_paise,
                "currency": "INR",
                "receipt": receipt or "concierge_demo",
                "notes": notes or {},
            }
        )
        return order
    except Exception as e:
        import uuid

        return {
            "id": f"order_fallback_{uuid.uuid4().hex[:14]}",
            "amount": order_amount_paise,
            "currency": "INR",
            "_fallback_reason": str(e),
        }


def create_payment_link(order_amount_paise: int, description: str, customer: dict = None) -> dict:
    """
    Generate a Payment Link for the "recovered" checkout — used once the
    agent's intervention is accepted, to hand the user a completable
    payment flow (e.g. after switching payment method).

    Returns a dict with at least {"id": ..., "short_url": ...}.
    """
    try:
        client = _get_client()
        payload = {
            "amount": order_amount_paise,
            "currency": "INR",
            "description": description,
            "notify": {"sms": False, "email": False},
        }
        if customer:
            payload["customer"] = customer
        return client.payment_link.create(payload)
    except Exception as e:
        return {
            "id": None,
            "short_url": None,
            "_fallback_reason": str(e),
        }


def get_available_payment_methods(order_amount_paise: int) -> list[str]:
    """
    Return the payment methods that should actually be offered for an
    order of this amount. EMI is filtered out below the same threshold
    the rules engine uses, so the two modules can never disagree about
    what EMI eligibility means.
    """
    methods = list(ENABLED_METHODS)
    if order_amount_paise < rules_engine.EMI_THRESHOLD_PAISE and "emi" in methods:
        methods.remove("emi")
    return methods


def verify_payment_signature(params: dict) -> bool:
    """
    Verify a payment signature from a Razorpay callback (e.g. after a
    Payment Link is completed). params must include order_id, payment_id,
    and signature. Returns False (not an exception) on any failure, since
    a verification check should never crash the caller.
    """
    try:
        client = _get_client()
        client.utility.verify_payment_signature(params)
        return True
    except Exception:
        return False