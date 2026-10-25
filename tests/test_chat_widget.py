import unittest
import re
from sqlalchemy import select
from tests import create_test_app
from app.extensions import db
from app.models.user import User


class ChatWidgetTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_test_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = True

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.rollback()
        self.ctx.pop()

    def get_csrf_token(self, url="/"):
        res = self.client.get(url)
        html = res.get_data(as_text=True)
        match = re.search(r'name="csrf_token"[^>]*?value="([^"]+)"', html)
        if not match:
            match = re.search(r'content="([^"]+)"[^>]*?name="csrf-token"', html)
        if not match:
            match = re.search(r'name="csrf-token"[^>]*?content="([^"]+)"', html)
        self.assertTrue(match, f"CSRF token not found in {url}")
        return match.group(1)

    def test_widget_renders_on_homepage(self):
        """Widget launcher and panel must be rendered on the homepage."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('id="sw-chat-widget"', html)
        self.assertIn('id="sw-widget-launcher"', html)
        self.assertIn("Tanya SehatWarga", html)
        self.assertIn('id="sw-widget-panel"', html)
        self.assertIn("Asisten SehatWarga", html)
        self.assertIn("Bantuan informasi layanan kesehatan", html)
        self.assertIn('id="sw-widget-minimize"', html)
        self.assertIn('id="sw-widget-close"', html)
        self.assertIn('id="sw-widget-messages"', html)
        self.assertIn('id="sw-widget-input"', html)
        self.assertIn('id="sw-widget-submit"', html)
        self.assertIn("assistant-widget.js", html)

    def test_widget_not_rendered_on_full_assistant_page(self):
        """Full /assistant page must NOT contain the floating widget or duplicate launcher."""
        res = self.client.get("/assistant")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertNotIn('id="sw-chat-widget"', html)
        self.assertNotIn('id="sw-widget-launcher"', html)
        self.assertNotIn("assistant-widget.js", html)
        # Dedicated assistant interface remains intact
        self.assertIn('id="chat-form"', html)
        self.assertIn('id="chat-messages"', html)
        self.assertIn("assistant.js", html)

    def test_widget_renders_on_facilities_page(self):
        """Widget must be accessible on facilities list."""
        res = self.client.get("/facilities")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn('id="sw-chat-widget"', html)
        self.assertIn("Tanya SehatWarga", html)
        self.assertIn("assistant-widget.js", html)

    def test_widget_renders_on_citizen_dashboard(self):
        """Widget must be accessible on citizen dashboard when authenticated."""
        citizen = db.session.execute(
            select(User).filter_by(email="warga.demo@sehatwarga.test")
        ).scalar_one_or_none()

        if citizen:
            with self.client.session_transaction() as session:
                session["_user_id"] = str(citizen.id)
                session["_fresh"] = True

            res = self.client.get("/citizen/dashboard")
            self.assertEqual(res.status_code, 200)
            html = res.get_data(as_text=True)

            self.assertIn('id="sw-chat-widget"', html)
            self.assertIn("Tanya SehatWarga", html)
            self.assertIn("assistant-widget.js", html)

    def test_widget_accessibility_attributes(self):
        """Verify semantic HTML and accessible roles and labels."""
        res = self.client.get("/")
        html = res.get_data(as_text=True)

        # Dialog attributes
        self.assertIn('role="dialog"', html)
        self.assertIn('aria-labelledby="sw-widget-title"', html)
        self.assertIn('aria-describedby="sw-widget-desc"', html)

        # Launcher attributes
        self.assertIn('aria-expanded="false"', html)
        self.assertIn('aria-controls="sw-widget-panel"', html)

        # Messages log
        self.assertIn('role="log"', html)
        self.assertIn('aria-live="polite"', html)

        # Action accessible names
        self.assertIn('aria-label="Minimalkan percakapan"', html)
        self.assertIn('aria-label="Tutup percakapan"', html)
        self.assertIn('aria-label="Buka asisten penuh"', html)
        self.assertIn('aria-label="Kirim pesan"', html)

    def test_widget_welcome_message_and_chips(self):
        """Verify initial welcome message and suggested quick chips."""
        res = self.client.get("/")
        html = res.get_data(as_text=True)

        self.assertIn(
            "Halo! Saya Asisten SehatWarga. Ada yang bisa saya bantu terkait layanan atau fasilitas kesehatan?",
            html,
        )
        self.assertIn("Fasilitas terdekat", html)
        self.assertIn("Ajukan layanan", html)
        self.assertIn("Cek iuran", html)

    def test_widget_form_urls_and_csrf(self):
        """Verify widget form endpoints and CSRF token."""
        res = self.client.get("/")
        html = res.get_data(as_text=True)

        self.assertIn('data-chat-url="/assistant/chat"', html)
        self.assertIn('data-location-url="/assistant/location"', html)
        self.assertIn('name="csrf_token" id="sw-widget-csrf"', html)

    def test_chat_api_call_with_conversation_history(self):
        """Verify backend /assistant/chat handles messages with conversation history."""
        csrf_token = self.get_csrf_token("/")
        payload = {
            "message": "Halo, saya ingin bertanya tentang layanan kesehatan.",
            "conversation_history": [
                {"role": "user", "content": "Halo"},
                {"role": "assistant", "content": "Halo! Ada yang bisa saya bantu?"},
            ],
        }

        res = self.client.post(
            "/assistant/chat",
            json=payload,
            headers={"X-CSRFToken": csrf_token},
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("message", data)
        self.assertTrue(len(data["message"]) > 0)


if __name__ == "__main__":
    unittest.main()
