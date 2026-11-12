import re
import unittest
from pathlib import Path
from unittest.mock import patch
import os

import app as app_module
from app import app


class InstagramOAuthSecurityTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY="test-only-secret")
        self.client = app.test_client()

    def test_home_has_no_password_capture_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotRegex(
            html,
            re.compile(r"<input[^>]+(?:type=['\"]password|name=['\"]password)", re.I),
        )
        self.assertIn("Continue with Instagram", html) if "Continue with Instagram" in html else self.assertIn(
            "Instagram sign-in is not configured yet", html
        )

    def test_legacy_password_post_route_is_removed(self):
        response = self.client.post(
            "/login",
            data={"username": "not-a-real-user", "password": "must-not-be-collected"},
        )
        self.assertEqual(response.status_code, 404)

    def test_callback_rejects_oauth_state_mismatch(self):
        with self.client.session_transaction() as browser_session:
            browser_session["oauth_state"] = "expected-state"
        response = self.client.get(
            "/auth/instagram/callback?code=fake-code&state=attacker-state"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Security check failed", response.get_data(as_text=True))

    def test_oauth_start_redirects_to_instagram_when_configured(self):
        with patch.dict(os.environ, {"FLASK_SECRET_KEY": "test-secret"}):
            with patch.object(app_module, "INSTAGRAM_CLIENT_ID", "test-client-id"), patch.object(
                app_module, "INSTAGRAM_CLIENT_SECRET", "test-client-secret"
            ), patch.object(
                app_module,
                "INSTAGRAM_REDIRECT_URI",
                "https://example.test/auth/instagram/callback",
            ):
                response = self.client.get("/auth/instagram")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("https://www.instagram.com/oauth/authorize?"))

    def test_health_endpoint(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_fake_metrics_and_credential_printing_are_absent(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "app.py").read_text(encoding="utf-8")
        legacy = (root / "instagram.py").read_text(encoding="utf-8")
        self.assertNotIn("random.randint", source + legacy)
        self.assertNotRegex(source + legacy, re.compile(r"print\s*\([^)]*password", re.I))
        self.assertNotIn('name="password"', source + legacy)
        self.assertNotIn('type="password"', source + legacy)


if __name__ == "__main__":
    unittest.main()
