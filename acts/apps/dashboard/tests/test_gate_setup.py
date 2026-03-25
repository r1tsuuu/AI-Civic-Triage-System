from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse

from apps.dashboard.gate_views import gate_logout, gate_view
from apps.dashboard.middleware import DashboardPasswordGate
from apps.webhook.views import webhook_receive, webhook_verify


class ProjectSetupTests(TestCase):
    def test_required_apps_are_installed(self):
        for app in [
            "apps.webhook",
            "apps.triage",
            "apps.dashboard",
            "apps.response",
            "apps.accounts",
        ]:
            self.assertIn(app, settings.INSTALLED_APPS)

    def test_dashboard_gate_middleware_is_enabled_after_session_middleware(self):
        session_index = settings.MIDDLEWARE.index(
            "django.contrib.sessions.middleware.SessionMiddleware"
        )
        gate_index = settings.MIDDLEWARE.index(
            "apps.dashboard.middleware.DashboardPasswordGate"
        )
        self.assertGreater(gate_index, session_index)

    def test_gate_url_is_wired(self):
        match = resolve("/gate/")
        self.assertEqual(match.func, gate_view)

    def test_dashboard_stats_url_is_wired(self):
        match = resolve("/dashboard/")
        self.assertEqual(match.view_name, "dashboard:stats")

    def test_webhook_verify_url_is_wired(self):
        match = resolve("/webhook/facebook/")
        self.assertEqual(match.func, webhook_verify)

    def test_webhook_receive_url_is_wired(self):
        match = resolve("/webhook/facebook/receive/")
        self.assertEqual(match.func, webhook_receive)

    def test_logout_url_is_wired(self):
        match = resolve("/dashboard/logout/")
        self.assertEqual(match.func, gate_logout)


@override_settings(DEMO_PASSWORD="demo-pass")
class GateViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_gate_get_renders_page(self):
        response = self.client.get(reverse("gate"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "gate.html")

    def test_gate_post_with_correct_password_sets_session_and_redirects(self):
        response = self.client.post(reverse("gate"), {"password": "demo-pass"})
        self.assertRedirects(response, reverse("dashboard:stats"), fetch_redirect_response=False)
        self.assertTrue(self.client.session.get("demo_authed"))

    def test_gate_post_with_wrong_password_shows_error(self):
        response = self.client.post(reverse("gate"), {"password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.session.get("demo_authed", False))
        self.assertContains(response, "Incorrect password. Please try again.")

    def test_logout_flushes_session_and_redirects_to_gate(self):
        session = self.client.session
        session["demo_authed"] = True
        session["some_other_key"] = "value"
        session.save()

        response = self.client.get(reverse("dashboard:logout"))

        self.assertRedirects(response, reverse("gate"), fetch_redirect_response=False)
        self.assertFalse(self.client.session.get("demo_authed", False))
        self.assertNotIn("some_other_key", self.client.session)


class DashboardPasswordGateMiddlewareTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_route_redirects_to_gate_when_unauthenticated(self):
        response = self.client.get(reverse("dashboard:stats"))
        self.assertRedirects(response, reverse("gate"), fetch_redirect_response=False)

    def test_dashboard_route_allows_authenticated_session(self):
        session = self.client.session
        session["demo_authed"] = True
        session.save()

        response = self.client.get(reverse("dashboard:stats"))
        self.assertEqual(response.status_code, 200)

    def test_non_dashboard_route_is_not_blocked_by_gate(self):
        middleware = DashboardPasswordGate(lambda request: None)

        class DummyRequest:
            path = "/webhook/facebook/"
            session = {}

        response = middleware(DummyRequest())
        self.assertIsNone(response)
