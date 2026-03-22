"""
WSGI config for ACTS.
Gunicorn command: gunicorn config.wsgi --log-file -
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_wsgi_application()
