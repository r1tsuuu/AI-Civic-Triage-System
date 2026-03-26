import uuid
import logging

from django.shortcuts import render, redirect
from django.views import View
from django.utils import timezone

from apps.webhook.models import RawPost

logger = logging.getLogger(__name__)


class MockFBFeedView(View):
    """
    Simulates an LGU Facebook page feed for the hackathon demo.

    GET  /fb/  — Render feed with recent posts and the compose form.
    POST /fb/  — Accept a new civic report, create a RawPost, run the
                 NLP pipeline synchronously, then redirect back.
    """
    template_name = "mock_fb/feed.html"

    def get(self, request):
        posts = (
            RawPost.objects
            .prefetch_related("report_set")
            .order_by("-received_at")[:20]
        )
        return render(request, self.template_name, {
            "posts": posts,
            "just_posted": request.GET.get("posted") == "1",
        })

    def post(self, request):
        text = request.POST.get("post_text", "").strip()
        if not text:
            return redirect("/fb/")

        raw_post = RawPost.objects.create(
            facebook_post_id=f"mock_{uuid.uuid4().hex[:16]}",
            post_text=text,
        )

        # Run pipeline synchronously — no background thread for demo
        try:
            from apps.triage.pipeline import process_post
            process_post(raw_post)
        except Exception:
            logger.exception("Pipeline failed for mock post %s", raw_post.id)

        return redirect("/fb/?posted=1")
