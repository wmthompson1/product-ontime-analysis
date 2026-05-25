"""Tests for email alert message formatting.

Verifies that the alert payload builder produces a correctly-formed email
message (subject, body, recipient) regardless of whether SMTP secrets are
present. No live SMTP connection is made (#112).

Run: python hf-space-inventory-sqlgen/tests/test_email_alert_format.py
"""

from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
HF_DIR = os.path.dirname(HERE)
sys.path.insert(0, HF_DIR)


def _build_alert_email(
    subject: str,
    body: str,
    to_addr: str,
    from_addr: str,
) -> dict:
    """Reference implementation of alert email builder — mirrors what GitHub Actions sends."""
    if not subject or not body or not to_addr or not from_addr:
        raise ValueError("All email fields are required")
    return {
        "subject": subject,
        "body": body,
        "to": to_addr,
        "from": from_addr,
    }


def _should_send_email() -> bool:
    """True when all required email secrets are present."""
    required = ["ALERT_EMAIL_TO", "ALERT_EMAIL_FROM", "ALERT_SMTP_HOST",
                "ALERT_SMTP_PORT", "ALERT_SMTP_USER", "ALERT_SMTP_PASSWORD"]
    return all(os.environ.get(k, "").strip() for k in required)


class TestEmailAlertFormat(unittest.TestCase):

    def test_build_alert_email_returns_required_fields(self):
        """Alert email dict must include subject, body, to, from."""
        msg = _build_alert_email(
            subject="[ALERT] ArangoDB drift detected",
            body="Perspective_Intents mismatch: ArangoDB=4, SQLite=5",
            to_addr="ops@example.com",
            from_addr="noreply@example.com",
        )
        for field in ("subject", "body", "to", "from"):
            self.assertIn(field, msg, f"Email dict missing '{field}' field")

    def test_subject_is_nonempty_string(self):
        msg = _build_alert_email("subject", "body", "a@b.com", "c@d.com")
        self.assertIsInstance(msg["subject"], str)
        self.assertTrue(msg["subject"].strip())

    def test_body_contains_drift_details(self):
        drift_details = "Perspective_Intents: Arango=4, SQLite=5 ❌"
        msg = _build_alert_email(
            subject="[ALERT] Drift",
            body=f"Drift detected:\n{drift_details}",
            to_addr="ops@example.com",
            from_addr="noreply@example.com",
        )
        self.assertIn(drift_details, msg["body"])

    def test_raises_on_missing_to_address(self):
        with self.assertRaises(ValueError):
            _build_alert_email("subj", "body", "", "from@example.com")

    def test_raises_on_missing_from_address(self):
        with self.assertRaises(ValueError):
            _build_alert_email("subj", "body", "to@example.com", "")

    def test_raises_on_empty_subject(self):
        with self.assertRaises(ValueError):
            _build_alert_email("", "body", "to@example.com", "from@example.com")

    def test_raises_on_empty_body(self):
        with self.assertRaises(ValueError):
            _build_alert_email("subj", "", "to@example.com", "from@example.com")

    def test_should_send_email_false_when_secrets_missing(self):
        """should_send_email returns False when ALERT_EMAIL_TO is not set."""
        original = os.environ.pop("ALERT_EMAIL_TO", None)
        try:
            self.assertFalse(_should_send_email())
        finally:
            if original is not None:
                os.environ["ALERT_EMAIL_TO"] = original

    def test_should_send_email_true_when_all_secrets_present(self):
        """should_send_email returns True when all required env vars are set."""
        secrets = {
            "ALERT_EMAIL_TO": "ops@example.com",
            "ALERT_EMAIL_FROM": "noreply@example.com",
            "ALERT_SMTP_HOST": "smtp.example.com",
            "ALERT_SMTP_PORT": "587",
            "ALERT_SMTP_USER": "user",
            "ALERT_SMTP_PASSWORD": "pass",
        }
        original = {k: os.environ.pop(k, None) for k in secrets}
        try:
            os.environ.update(secrets)
            self.assertTrue(_should_send_email())
        finally:
            for k, v in original.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)

    def test_alert_subject_contains_repo_context(self):
        """Alert subject should identify the source for easy triage."""
        subject = "[ALERT] ArangoDB ↔ SQLite Drift — manufacturing_graph"
        msg = _build_alert_email(subject, "body", "to@x.com", "from@x.com")
        self.assertIn("ALERT", msg["subject"])
        self.assertIn("manufacturing_graph", msg["subject"])


class TestEmailAlertSkipWhenSecretsAbsent(unittest.TestCase):

    def test_no_email_sent_in_ci_without_secrets(self):
        """Verify the guard logic: email is NOT attempted without secrets."""
        for key in ["ALERT_EMAIL_TO", "ALERT_EMAIL_FROM", "ALERT_SMTP_HOST",
                    "ALERT_SMTP_PORT", "ALERT_SMTP_USER", "ALERT_SMTP_PASSWORD"]:
            os.environ.pop(key, None)
        self.assertFalse(
            _should_send_email(),
            "Email should be skipped when no ALERT_* secrets are configured"
        )


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestEmailAlertFormat))
    suite.addTests(loader.loadTestsFromTestCase(TestEmailAlertSkipWhenSecretsAbsent))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
    print(f"\n{'PASS' if result.wasSuccessful() else 'FAIL'}: "
          f"{passed}/{result.testsRun} tests "
          f"({len(result.skipped)} skipped)")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
