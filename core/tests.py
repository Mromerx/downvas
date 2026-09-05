from unittest import mock

from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import translation

from core import views


class I18nSettingsTest(SimpleTestCase):
    def test_default_language_is_english(self):
        response = self.client.get(reverse("settings"))
        self.assertContains(response, '<html lang="en">')
        self.assertContains(response, "Settings")
        self.assertContains(response, "Language")

    def test_saved_language_becomes_active(self):
        response = self.client.post(reverse("settings"), {
            "canvas_url": "https://canvas.example.com",
            "api_token": "secret-token",
            "locale": "es",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["locale"], "es")

        settings_page = self.client.get(reverse("settings"))
        self.assertContains(settings_page, '<html lang="es">')
        self.assertContains(settings_page, "Ajustes")
        self.assertContains(settings_page, "Idioma")

        index_page = self.client.get(reverse("index"))
        self.assertContains(index_page, '<html lang="es">')
        self.assertContains(index_page, "Cargar curso")

    def test_invalid_locale_falls_back_to_english(self):
        session = self.client.session
        session["locale"] = "xx"
        session.save()

        response = self.client.get(reverse("settings"))
        self.assertContains(response, '<html lang="en">')
        self.assertContains(response, "Settings")

    def test_english_still_active_after_switch_back(self):
        self.client.post(reverse("settings"), {
            "canvas_url": "https://canvas.example.com",
            "locale": "es",
        })
        self.client.post(reverse("settings"), {
            "canvas_url": "https://canvas.example.com",
            "locale": "en",
        })

        response = self.client.get(reverse("index"))
        self.assertContains(response, '<html lang="en">')
        self.assertContains(response, "Load Course")

    def test_stream_activates_selected_locale_in_background_thread(self):
        captured = []

        def fake_download(base_url, token, jobs, emit=None):
            captured.append(translation.get_language())
            emit({"type": "phase", "phase": "download", "total_files": 0})
            return [], None

        with mock.patch("core.views.download_files_to_temp", fake_download):
            list(views._stream_progress("https://x", "tk", [], "es"))

        self.assertEqual(captured, ["es"])