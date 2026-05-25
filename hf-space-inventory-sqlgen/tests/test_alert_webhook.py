"""
test_alert_webhook.py
=====================
Unit tests for sync_watcher._alert() covering:
  1. Webhook not configured — no HTTP call is made.
  2. Webhook configured + HTTP 200 — POST is made with correct payload.
  3. Webhook configured + URLError — logs to stderr, does NOT raise.

All tests monkeypatch urllib.request.urlopen so no real network calls occur.
"""
import importlib
import io
import json
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Locate sync_watcher without executing its __main__ block
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_HF_DIR = os.path.dirname(_HERE)

if _HF_DIR not in sys.path:
    sys.path.insert(0, _HF_DIR)

import sync_watcher  # noqa: E402  (module-level import after path setup)


class TestAlertNoWebhook(unittest.TestCase):
    """_alert() must not make any HTTP call when GRAPH_SYNC_ALERT_WEBHOOK is unset."""

    def test_no_http_call_when_webhook_unset(self):
        env = {k: v for k, v in os.environ.items() if k != "GRAPH_SYNC_ALERT_WEBHOOK"}
        env.pop("GRAPH_SYNC_ALERT_EMAIL", None)

        with patch.dict(os.environ, env, clear=True):
            with patch("urllib.request.urlopen") as mock_urlopen:
                sync_watcher._alert("TEST TITLE", "test body")
                mock_urlopen.assert_not_called()

    def test_no_http_call_when_webhook_empty_string(self):
        env = {"GRAPH_SYNC_ALERT_WEBHOOK": ""}
        env.pop("GRAPH_SYNC_ALERT_EMAIL", None)

        with patch.dict(os.environ, env, clear=False):
            # Temporarily remove email var to avoid SMTP path
            with patch.dict(os.environ, {"GRAPH_SYNC_ALERT_EMAIL": ""}, clear=False):
                with patch("urllib.request.urlopen") as mock_urlopen:
                    sync_watcher._alert("TEST TITLE", "test body")
                    mock_urlopen.assert_not_called()


class TestAlertWebhookSuccess(unittest.TestCase):
    """_alert() must POST a JSON payload to the webhook URL on HTTP 200."""

    def _make_fake_response(self, status=200):
        resp = MagicMock()
        resp.status = status
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_posts_to_webhook_on_http_200(self):
        fake_url = "https://hooks.slack.com/services/fake/webhook"
        env_patch = {
            "GRAPH_SYNC_ALERT_WEBHOOK": fake_url,
            "GRAPH_SYNC_ALERT_EMAIL": "",
        }

        with patch.dict(os.environ, env_patch, clear=False):
            with patch("urllib.request.urlopen", return_value=self._make_fake_response(200)) as mock_urlopen:
                sync_watcher._alert("SYNC FAILED", "some error detail", pending=3)
                mock_urlopen.assert_called_once()

    def test_payload_contains_title_and_body(self):
        fake_url = "https://hooks.slack.com/services/fake/webhook"
        captured_request = []

        def fake_urlopen(req, timeout=None):
            captured_request.append(req)
            return self._make_fake_response(200)

        env_patch = {
            "GRAPH_SYNC_ALERT_WEBHOOK": fake_url,
            "GRAPH_SYNC_ALERT_EMAIL": "",
        }

        with patch.dict(os.environ, env_patch, clear=False):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                sync_watcher._alert("MY TITLE", "my error body", pending=5)

        self.assertEqual(len(captured_request), 1)
        req = captured_request[0]
        # Verify the request URL
        self.assertEqual(req.full_url, fake_url)
        # Decode and parse the posted JSON
        payload = json.loads(req.data.decode("utf-8"))
        self.assertIn("text", payload)
        text = payload["text"]
        self.assertIn("MY TITLE", text)
        self.assertIn("my error body", text)
        self.assertIn("5 pending queue row(s)", text)

    def test_content_type_header_is_json(self):
        fake_url = "https://hooks.slack.com/services/fake/webhook"
        captured_request = []

        def fake_urlopen(req, timeout=None):
            captured_request.append(req)
            return self._make_fake_response(200)

        env_patch = {
            "GRAPH_SYNC_ALERT_WEBHOOK": fake_url,
            "GRAPH_SYNC_ALERT_EMAIL": "",
        }

        with patch.dict(os.environ, env_patch, clear=False):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                sync_watcher._alert("TITLE", "body")

        req = captured_request[0]
        self.assertEqual(req.get_header("Content-type"), "application/json")

    def test_pending_none_shows_unavailable(self):
        fake_url = "https://hooks.slack.com/services/fake/webhook"
        captured_request = []

        def fake_urlopen(req, timeout=None):
            captured_request.append(req)
            return self._make_fake_response(200)

        env_patch = {
            "GRAPH_SYNC_ALERT_WEBHOOK": fake_url,
            "GRAPH_SYNC_ALERT_EMAIL": "",
        }

        with patch.dict(os.environ, env_patch, clear=False):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                sync_watcher._alert("TITLE", "body", pending=None)

        payload = json.loads(captured_request[0].data.decode("utf-8"))
        self.assertIn("pending count unavailable", payload["text"])


class TestAlertWebhookHttpError(unittest.TestCase):
    """_alert() must log to stderr and NOT raise when the webhook POST fails."""

    def test_url_error_logs_to_stderr_and_does_not_raise(self):
        import urllib.error

        fake_url = "https://hooks.slack.com/services/fake/webhook"
        env_patch = {
            "GRAPH_SYNC_ALERT_WEBHOOK": fake_url,
            "GRAPH_SYNC_ALERT_EMAIL": "",
        }

        def raise_url_error(req, timeout=None):
            raise urllib.error.URLError("connection refused")

        stderr_capture = io.StringIO()

        with patch.dict(os.environ, env_patch, clear=False):
            with patch("urllib.request.urlopen", side_effect=raise_url_error):
                with patch("sys.stderr", stderr_capture):
                    # Must not raise
                    sync_watcher._alert("FAILED", "boom")

        output = stderr_capture.getvalue()
        self.assertIn("Webhook POST failed", output)
        self.assertIn("connection refused", output)

    def test_non_200_status_logs_to_stderr_and_does_not_raise(self):
        fake_url = "https://hooks.slack.com/services/fake/webhook"

        bad_resp = MagicMock()
        bad_resp.status = 500
        bad_resp.__enter__ = lambda s: s
        bad_resp.__exit__ = MagicMock(return_value=False)

        env_patch = {
            "GRAPH_SYNC_ALERT_WEBHOOK": fake_url,
            "GRAPH_SYNC_ALERT_EMAIL": "",
        }

        stderr_capture = io.StringIO()

        with patch.dict(os.environ, env_patch, clear=False):
            with patch("urllib.request.urlopen", return_value=bad_resp):
                with patch("sys.stderr", stderr_capture):
                    sync_watcher._alert("FAILED", "server error")

        output = stderr_capture.getvalue()
        self.assertIn("HTTP 500", output)

    def test_alert_always_writes_to_stderr(self):
        """stderr line must appear regardless of webhook configuration."""
        env_patch = {
            "GRAPH_SYNC_ALERT_WEBHOOK": "",
            "GRAPH_SYNC_ALERT_EMAIL": "",
        }

        stderr_capture = io.StringIO()

        with patch.dict(os.environ, env_patch, clear=False):
            with patch("sys.stderr", stderr_capture):
                sync_watcher._alert("ANY TITLE", "any body", pending=7)

        output = stderr_capture.getvalue()
        self.assertIn("[GRAPH_SYNC_ALERT]", output)
        self.assertIn("ANY TITLE", output)
        self.assertIn("7 pending queue row(s)", output)


if __name__ == "__main__":
    unittest.main()
