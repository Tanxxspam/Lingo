"""
Message generation layer for Agentic Checkout Concierge.

CRITICAL DESIGN CONSTRAINT: this module only phrases a decision that the
rules engine has already made. It never decides the action_type or the
value — those come in as fixed inputs. This keeps every money-affecting
choice traceable to rules_engine.py, not to LLM output.

See AGENTS.md, Section 3.
"""

import os

MODEL = "claude-haiku-4-5-20251001"  # fast + cheap, sufficient for one-sentence phrasing

_client = None


def _get_client():
    """Lazily import and construct the Anthropic client. Importing lazily
    means this module (and its fallback templates) still work even in an
    environment where the anthropic package isn't installed yet."""
    global _client
    if _client is None:
        from anthropic import Anthropic

        _client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


# Fallback templates used if the API call fails or no key is configured —
# keeps the demo working even without network/API access.
_FALLBACK_TEMPLATES = {
    "offer_discount": "Still deciding? Here's {value} off if you complete your order now.",
    "suggest_payment_method": "Having trouble? Try paying with {value} instead — it might be smoother.",
    "offer_emi": "You can also split this into easy EMI payments if that works better for you.",
}


def generate_message(decision: dict) -> str:
    """
    Turn a rules-engine decision into a short, friendly customer-facing
    message. The decision's action_type and value are treated as fixed —
    the model is instructed not to alter them.

    Args:
        decision: {"action": ..., "value": ..., "reason": ...} as produced
                  by rules_engine.decide()

    Returns:
        A single sentence to show in the concierge widget.
    """
    action = decision["action"]
    value = decision.get("value")

    if action == "no_action":
        return ""

    prompt = (
        "You are a checkout assistant. Phrase this offer in one short, "
        "friendly sentence for a customer who seems to be hesitating at checkout. "
        "Do not change the offer type or the value given below — only phrase it naturally.\n\n"
        f"Offer type: {action}\n"
        f"Offer value: {value}\n\n"
        "Respond with only the sentence, no preamble."
    )

    try:
        client = _get_client()
        response = client.messages.create(
            model=MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        return text or _fallback(action, value)
    except Exception:
        # Network issues, missing API key, rate limits, etc. — never let
        # message phrasing failures block the checkout flow.
        return _fallback(action, value)


def _fallback(action: str, value) -> str:
    template = _FALLBACK_TEMPLATES.get(action, "We've got an offer for you — check it out!")
    return template.format(value=value)