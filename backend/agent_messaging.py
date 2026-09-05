"""
Message generation layer for Agentic Checkout Concierge.

CRITICAL DESIGN CONSTRAINT: this module only phrases a decision that the
rules engine has already made. It never decides the action_type or the
value — those come in as fixed inputs. This keeps every money-affecting
choice traceable to rules_engine.py, not to LLM output.

Provider chain: Groq (free tier, fast) -> Anthropic (if configured) ->
static templates. Groq is tried first since it's free and has no card
requirement, which matters for a hackathon budget. Anthropic is kept as
a fallback in case Groq's free-tier rate limit is hit mid-demo. If both
fail, static templates keep the concierge widget working regardless.

See AGENTS.md, Section 3.
"""

import os

GROQ_MODEL = "llama-3.3-70b-versatile"
ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

_groq_client = None
_anthropic_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        from groq import Groq

        _groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return _groq_client


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic

        _anthropic_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _anthropic_client


# Fallback templates used if every provider fails — keeps the demo
# working even without network/API access.
_FALLBACK_TEMPLATES = {
    "offer_discount": "Still deciding? Here's {value} off if you complete your order now.",
    "suggest_payment_method": "Having trouble? Try paying with {value} instead — it might be smoother.",
    "offer_emi": "You can also split this into easy EMI payments if that works better for you.",
}


def _build_prompt(action: str, value) -> str:
    return (
        "You are a checkout assistant. Phrase this offer in one short, "
        "friendly sentence for a customer who seems to be hesitating at checkout. "
        "Do not change the offer type or the value given below — only phrase it naturally.\n\n"
        f"Offer type: {action}\n"
        f"Offer value: {value}\n\n"
        "Respond with only the sentence, no preamble."
    )


def _try_groq(prompt: str) -> str:
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def _try_anthropic(prompt: str) -> str:
    client = _get_anthropic_client()
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()


def generate_message(decision: dict) -> str:
    """
    Turn a rules-engine decision into a short, friendly customer-facing
    message. The decision's action_type and value are treated as fixed —
    every provider is instructed not to alter them.

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

    prompt = _build_prompt(action, value)

    for provider_fn, provider_name in [(_try_groq, "groq"), (_try_anthropic, "anthropic")]:
        try:
            text = provider_fn(prompt)
            if text:
                return text
        except Exception:
            # Missing key, rate limit, network issue, etc. — try the next
            # provider in the chain rather than failing the checkout flow.
            continue

    return _fallback(action, value)


def _fallback(action: str, value) -> str:
    template = _FALLBACK_TEMPLATES.get(action, "We've got an offer for you — check it out!")
    return template.format(value=value)