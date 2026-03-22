from django.conf import settings
from django.shortcuts import render, redirect


def gate_view(request):
    error = None

    if request.method == "POST":
        password = request.POST.get("password", "")
        if password == settings.DEMO_PASSWORD:
            request.session["demo_authed"] = True
            return redirect("/dashboard/")
        else:
            error = "Incorrect password. Please try again."

    return render(request, "gate.html", {"error": error})


def gate_logout(request):
    request.session.flush()
    return redirect("/gate/")