from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse


class DashboardPasswordGate:
    """
    Simple demo password gate for all /dashboard/* routes.
    Not a security system but just a demo gate for the hackathon sake.
    Anyone who knows DEMO_PASSWORD can access the dashboard.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/dashboard/"):
            if not request.session.get("demo_authed"):
                return redirect("/gate/")

        return self.get_response(request)