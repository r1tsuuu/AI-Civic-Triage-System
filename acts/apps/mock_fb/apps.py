from django.apps import AppConfig


class MockFbConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.mock_fb"
    label = "mock_fb"
    verbose_name = "Mock Facebook Feed"
