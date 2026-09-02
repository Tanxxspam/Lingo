"""
Unit tests for the rules engine, using scripted event sequences.
Run with: python3 -m unittest test_rules_engine.py -v

No server or DB needed — rules_engine.decide() is a pure function.
"""

import unittest
from datetime import datetime, timedelta

import rules_engine as re


def event(event_type, metadata=None, ts="2026-09-01 10:00:00"):
    return {"event_type": event_type, "metadata": metadata or {}, "created_at": ts}


def intervention(action_type, ts="2026-09-01 10:00:05", outcome_response=None):
    return {"action_type": action_type, "created_at": ts, "outcome_response": outcome_response}


class TestIdleSignal(unittest.TestCase):
    def test_idle_below_threshold_no_action(self):
        events = [event("idle", {"idle_seconds": 10})]
        decision = re.decide(events, [], order_amount=100000, available_payment_methods=["card", "upi"])
        self.assertEqual(decision["action"], "no_action")
        self.assertIn("idle_time_below_threshold", decision["reason"])

    def test_idle_above_threshold_offers_discount(self):
        events = [event("idle", {"idle_seconds": 25})]
        decision = re.decide(events, [], order_amount=100000, available_payment_methods=["card", "upi"])
        self.assertEqual(decision["action"], "offer_discount")
        self.assertEqual(decision["value"], "10%")

    def test_idle_after_discount_rejected_escalates_to_payment_method(self):
        events = [event("idle", {"idle_seconds": 25}, ts="2026-09-01 10:01:00")]
        priors = [intervention("offer_discount", ts="2026-09-01 10:00:00", outcome_response="rejected")]
        decision = re.decide(events, priors, order_amount=100000, available_payment_methods=["card", "upi"])
        self.assertEqual(decision["action"], "suggest_payment_method")
        self.assertEqual(decision["value"], "upi")


class TestOtpFailure(unittest.TestCase):
    def test_first_otp_failure_suggests_alternate_method(self):
        events = [event("otp_fail")]
        decision = re.decide(events, [], order_amount=100000, available_payment_methods=["card", "netbanking"])
        self.assertEqual(decision["action"], "suggest_payment_method")
        self.assertEqual(decision["value"], "netbanking")
        self.assertEqual(decision["reason"], "otp_failed_once")

    def test_second_otp_failure_still_suggests_non_card_method(self):
        events = [event("otp_fail"), event("otp_fail")]
        decision = re.decide(events, [], order_amount=100000, available_payment_methods=["card", "upi"])
        self.assertEqual(decision["action"], "suggest_payment_method")
        self.assertIn("otp_failed_repeatedly", decision["reason"])

    def test_no_alternate_method_available_no_action(self):
        events = [event("otp_fail")]
        decision = re.decide(events, [], order_amount=100000, available_payment_methods=["card"])
        self.assertEqual(decision["action"], "no_action")


class TestBackButton(unittest.TestCase):
    def test_high_value_order_offers_emi(self):
        events = [event("back_button")]
        decision = re.decide(events, [], order_amount=600_000, available_payment_methods=["card", "emi"])
        self.assertEqual(decision["action"], "offer_emi")

    def test_low_value_order_offers_discount(self):
        events = [event("back_button")]
        decision = re.decide(events, [], order_amount=100_000, available_payment_methods=["card", "emi"])
        self.assertEqual(decision["action"], "offer_discount")

    def test_low_value_order_discount_already_rejected_no_action(self):
        events = [event("back_button", ts="2026-09-01 10:01:00")]
        priors = [intervention("offer_discount", ts="2026-09-01 10:00:00", outcome_response="rejected")]
        decision = re.decide(events, priors, order_amount=100_000, available_payment_methods=["card", "emi"])
        self.assertEqual(decision["action"], "no_action")


class TestStoppingRules(unittest.TestCase):
    def test_max_interventions_reached_no_action(self):
        events = [event("idle", {"idle_seconds": 25}, ts="2026-09-01 10:02:00")]
        priors = [
            intervention("offer_discount", ts="2026-09-01 10:00:00"),
            intervention("suggest_payment_method", ts="2026-09-01 10:01:00"),
        ]
        decision = re.decide(events, priors, order_amount=100000, available_payment_methods=["card", "upi"])
        self.assertEqual(decision["action"], "no_action")
        self.assertIn("max_interventions_reached", decision["reason"])

    def test_cooldown_blocks_rapid_second_intervention(self):
        now = datetime(2026, 9, 1, 10, 0, 10)  # 10s after the prior intervention
        events = [event("idle", {"idle_seconds": 25}, ts="2026-09-01 10:00:10")]
        priors = [intervention("offer_discount", ts="2026-09-01 10:00:00")]
        decision = re.decide(events, priors, order_amount=100000, available_payment_methods=["card"], now=now)
        self.assertEqual(decision["action"], "no_action")
        self.assertIn("cooldown_active", decision["reason"])

    def test_cooldown_elapsed_allows_second_intervention(self):
        now = datetime(2026, 9, 1, 10, 0, 20)  # 20s after the prior intervention
        events = [event("idle", {"idle_seconds": 25}, ts="2026-09-01 10:00:20")]
        priors = [intervention("suggest_payment_method", ts="2026-09-01 10:00:00")]
        decision = re.decide(events, priors, order_amount=100000, available_payment_methods=["card", "upi"], now=now)
        self.assertEqual(decision["action"], "offer_discount")


if __name__ == "__main__":
    unittest.main()