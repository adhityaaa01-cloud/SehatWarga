import unittest
import threading
import time
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright

from tests import create_test_app
from app.extensions import db


class ServerThread(threading.Thread):
    def __init__(self, app, port=5055):
        super().__init__()
        self.server = make_server("127.0.0.1", port, app)
        self.port = port

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class WidgetE2ETestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_test_app()
        cls.app.config["TESTING"] = True
        cls.port = 5055
        cls.server_thread = ServerThread(cls.app, cls.port)
        cls.server_thread.start()
        time.sleep(1)

        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server_thread.shutdown()
        cls.server_thread.join()

    def setUp(self):
        self.page = self.browser.new_page()

    def tearDown(self):
        self.page.close()

    def test_widget_desktop_interaction(self):
        """Test open, send message, receive backend response, minimize, reopen, and message retention."""
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.goto(f"http://127.0.0.1:{self.port}/")

        # 1. Launcher is visible, panel is hidden
        launcher = self.page.locator("#sw-widget-launcher")
        panel = self.page.locator("#sw-widget-panel")

        self.assertTrue(launcher.is_visible())
        self.assertFalse(panel.is_visible())
        self.assertEqual(launcher.inner_text().strip(), "Tanya SehatWarga")

        # 2. Click launcher -> panel opens, input is focused
        launcher.click()
        self.assertTrue(panel.is_visible())
        self.assertFalse(launcher.is_visible())

        input_field = self.page.locator("#sw-widget-input")
        self.assertTrue(input_field.is_visible())

        # Check welcome message
        welcome = self.page.locator("#sw-widget-messages .message-row")
        self.assertGreaterEqual(welcome.count(), 1)
        self.assertIn("Asisten SehatWarga", welcome.first.inner_text())

        # 3. Type message and send via Enter key
        input_field.fill("Halo")
        input_field.press("Enter")

        # Wait for user row to appear
        user_row = self.page.locator("#sw-widget-messages .user-row")
        user_row.wait_for(timeout=5000)
        self.assertIn("Halo", user_row.inner_text())

        # Wait for assistant response row to arrive from real backend
        # Note: there is 1 initial welcome assistant row, so count should become at least 2
        self.page.wait_for_function(
            "document.querySelectorAll('#sw-widget-messages .assistant-row').length >= 2",
            timeout=15000
        )
        assistant_rows = self.page.locator("#sw-widget-messages .assistant-row")
        self.assertGreaterEqual(assistant_rows.count(), 2)

        # 4. Minimize panel
        minimize_btn = self.page.locator("#sw-widget-minimize")
        minimize_btn.click()

        self.assertFalse(panel.is_visible())
        self.assertTrue(launcher.is_visible())

        # 5. Reopen panel and verify conversation history is intact!
        launcher.click()
        self.assertTrue(panel.is_visible())

        assistant_rows_after = self.page.locator("#sw-widget-messages .assistant-row")
        self.assertGreaterEqual(assistant_rows_after.count(), 2)
        user_rows_after = self.page.locator("#sw-widget-messages .user-row")
        self.assertEqual(user_rows_after.count(), 1)
        self.assertIn("Halo", user_rows_after.first.inner_text())

        # 6. Test suggested chip click
        chip = self.page.locator(".sw-widget-chip").first
        chip_text = chip.inner_text()
        chip.click()

        # Should send another question
        self.page.wait_for_function(
            "document.querySelectorAll('#sw-widget-messages .user-row').length >= 2",
            timeout=5000
        )
        self.page.wait_for_function(
            "document.querySelectorAll('#sw-widget-messages .assistant-row').length >= 3",
            timeout=15000
        )

        # 7. Close button closes panel
        close_btn = self.page.locator("#sw-widget-close")
        close_btn.click()
        self.assertFalse(panel.is_visible())
        self.assertTrue(launcher.is_visible())

    def test_widget_mobile_responsiveness(self):
        """Test widget behavior and layout on mobile viewport (375x667)."""
        self.page.set_viewport_size({"width": 375, "height": 667})
        self.page.goto(f"http://127.0.0.1:{self.port}/")

        launcher = self.page.locator("#sw-widget-launcher")
        panel = self.page.locator("#sw-widget-panel")

        self.assertTrue(launcher.is_visible())
        launcher.click()

        self.assertTrue(panel.is_visible())
        # Check panel bounding box fits within viewport
        box = panel.bounding_box()
        self.assertIsNotNone(box)
        self.assertLessEqual(box["width"], 375)
        self.assertLessEqual(box["height"], 667)

        # Close on mobile
        close_btn = self.page.locator("#sw-widget-close")
        close_btn.click()
        self.assertFalse(panel.is_visible())
        self.assertTrue(launcher.is_visible())

    def test_widget_keyboard_escape(self):
        """Test Escape key closes the panel and returns focus to launcher."""
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.goto(f"http://127.0.0.1:{self.port}/")

        launcher = self.page.locator("#sw-widget-launcher")
        panel = self.page.locator("#sw-widget-panel")

        launcher.click()
        self.assertTrue(panel.is_visible())

        input_field = self.page.locator("#sw-widget-input")
        input_field.press("Escape")

        self.assertFalse(panel.is_visible())
        self.assertTrue(launcher.is_visible())

    def test_quick_reply_chips_intact_and_not_clipped(self):
        """Test quick-reply chips are all fully visible and not clipped by panel container."""
        # Test on desktop
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.goto(f"http://127.0.0.1:{self.port}/")
        self.page.locator("#sw-widget-launcher").click()

        panel = self.page.locator("#sw-widget-panel")
        panel_box = panel.bounding_box()
        self.assertIsNotNone(panel_box)

        chips = self.page.locator(".sw-widget-chip")
        self.assertEqual(chips.count(), 4)

        for i in range(chips.count()):
            chip = chips.nth(i)
            self.assertTrue(chip.is_visible())
            c_box = chip.bounding_box()
            self.assertIsNotNone(c_box)
            # Chip must not overflow right edge of panel
            self.assertLessEqual(
                c_box["x"] + c_box["width"],
                panel_box["x"] + panel_box["width"] + 1,
                f"Desktop: Chip {i} overflows panel right boundary"
            )
            # Chip must not overflow left edge of panel
            self.assertGreaterEqual(
                c_box["x"],
                panel_box["x"] - 1,
                f"Desktop: Chip {i} overflows panel left boundary"
            )

        # Test on mobile (375x667)
        self.page.set_viewport_size({"width": 375, "height": 667})
        m_panel_box = panel.bounding_box()
        self.assertIsNotNone(m_panel_box)

        for i in range(chips.count()):
            chip = chips.nth(i)
            self.assertTrue(chip.is_visible())
            c_box = chip.bounding_box()
            self.assertIsNotNone(c_box)
            self.assertLessEqual(
                c_box["x"] + c_box["width"],
                m_panel_box["x"] + m_panel_box["width"] + 1,
                f"Mobile: Chip {i} overflows panel right boundary"
            )
            self.assertGreaterEqual(
                c_box["x"],
                m_panel_box["x"] - 1,
                f"Mobile: Chip {i} overflows panel left boundary"
            )

    def test_conversation_persists_across_session_page_navigation(self):
        """Test that conversation state persists across page navigation during the session."""
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.goto(f"http://127.0.0.1:{self.port}/")

        # Open widget and send message
        self.page.locator("#sw-widget-launcher").click()
        input_field = self.page.locator("#sw-widget-input")
        input_field.fill("Pertanyaan demo sesi")
        input_field.press("Enter")

        # Wait for user row and assistant response
        self.page.locator("#sw-widget-messages .user-row").wait_for(timeout=5000)
        self.page.wait_for_function(
            "document.querySelectorAll('#sw-widget-messages .assistant-row').length >= 2",
            timeout=15000
        )

        # Minimize panel
        self.page.locator("#sw-widget-minimize").click()
        self.assertFalse(self.page.locator("#sw-widget-panel").is_visible())

        # Navigate to another page in the same session
        self.page.goto(f"http://127.0.0.1:{self.port}/facilities")

        # Open widget on new page
        launcher = self.page.locator("#sw-widget-launcher")
        self.assertTrue(launcher.is_visible())
        launcher.click()

        panel = self.page.locator("#sw-widget-panel")
        self.assertTrue(panel.is_visible())

        # Verify previous conversation is restored intact!
        user_rows = self.page.locator("#sw-widget-messages .user-row")
        self.assertGreaterEqual(user_rows.count(), 1)
        self.assertIn("Pertanyaan demo sesi", user_rows.first.inner_text())

        assistant_rows = self.page.locator("#sw-widget-messages .assistant-row")
        self.assertGreaterEqual(assistant_rows.count(), 2)

    def test_panel_viewport_containment_across_screen_sizes(self):
        """Test panel remains completely inside viewport across varied desktop & mobile screens."""
        resolutions = [
            (1920, 1080),
            (1366, 768),
            (800, 600),
            (375, 667),
            (320, 568),
            (667, 375),
        ]

        for w, h in resolutions:
            self.page.set_viewport_size({"width": w, "height": h})
            self.page.goto(f"http://127.0.0.1:{self.port}/")
            self.page.locator("#sw-widget-launcher").click()

            panel = self.page.locator("#sw-widget-panel")
            box = panel.bounding_box()
            self.assertIsNotNone(box, f"Panel missing bounding box at {w}x{h}")

            self.assertGreaterEqual(box["x"], 0, f"Panel x < 0 at {w}x{h}")
            self.assertGreaterEqual(box["y"], 0, f"Panel y < 0 at {w}x{h}")
            self.assertLessEqual(box["x"] + box["width"], w + 1, f"Panel overflows right at {w}x{h}")
            self.assertLessEqual(box["y"] + box["height"], h + 1, f"Panel overflows bottom at {w}x{h}")

    def test_no_widget_on_assistant_page(self):
        """Test that /assistant has no floating widget launcher."""
        self.page.goto(f"http://127.0.0.1:{self.port}/assistant")

        launcher = self.page.locator("#sw-widget-launcher")
        self.assertEqual(launcher.count(), 0)

        # Dedicated assistant card exists
        dedicated_form = self.page.locator("#chat-form")
        self.assertTrue(dedicated_form.is_visible())


if __name__ == "__main__":
    unittest.main()
