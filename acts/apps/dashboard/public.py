"""Public citizen transparency portal views."""

from __future__ import annotations

from datetime import timedelta

from django.views.generic import TemplateView, View
from django.utils import timezone
from django.http import JsonResponse

from apps.triage.models import Report, StatusChange
from apps.triage.constants import CATEGORY_LABELS, ACTIVE_STATUSES


PUBLIC_STATUS_LABELS = {
    "for_review": "Received",
    "reported": "Received",
    "acknowledged": "Reviewed by LGU",
    "in_progress": "Being addressed",
    "resolved": "Resolved",
}


class LandingView(TemplateView):
    template_name = "portal/index.html"


class PublicGeoJSONView(View):
    """
    GET /api/public/geojson/
    Anonymised GeoJSON for the citizen transparency map.
    Exposes: category, status, barangay, urgency_tier, created_at_iso.
    No raw text, no user IDs, no personal names.

    Public visibility rules:
    - Dismissed reports are never shown.
    - Resolved reports remain visible for 30 days in muted styling.
    """

    def get(self, request):
        features = []
        now = timezone.now()
        resolved_cutoff = now - timedelta(days=30)

        qs = (
            Report.objects
            .exclude(status="dismissed")
            .exclude(status="resolved", updated_at__lt=resolved_cutoff)
            .filter(latitude__isnull=False, longitude__isnull=False)
            .values(
            "category", "status", "location_text",
            "latitude", "longitude", "urgency_score", "created_at", "updated_at",
            )
            .order_by("-created_at")
        )

        for r in qs:
            score = r["urgency_score"] or 0
            if score >= 7:
                tier = "high"
            elif score >= 4:
                tier = "medium"
            else:
                tier = "low"

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [r["longitude"], r["latitude"]],
                },
                "properties": {
                    "category":       r["category"],
                    "category_label": CATEGORY_LABELS.get(r["category"], r["category"]),
                    "status":         r["status"],
                    "status_label":   PUBLIC_STATUS_LABELS.get(r["status"], r["status"]),
                    "barangay":       r["location_text"] or "Unknown",
                    "urgency_tier":   tier,
                    "created_at_iso": r["created_at"].isoformat() if r["created_at"] else None,
                    "resolved_at_iso": r["updated_at"].isoformat() if r["status"] == "resolved" and r["updated_at"] else None,
                },
            })

        return JsonResponse({"type": "FeatureCollection", "features": features})


class PublicRecentView(View):
    """
    GET /api/public/recent/
    Returns the 10 most recent visible reports for the citizen feed.
    Anonymised — no raw post text, no user identifiers.
    """

    def get(self, request):
        reports = []
        now = timezone.now()
        resolved_cutoff = now - timedelta(days=30)
        qs = (
            Report.objects
            .exclude(status="dismissed")
            .exclude(status="resolved", updated_at__lt=resolved_cutoff)
            .order_by("-created_at")
            .values("category", "status", "location_text", "urgency_score", "created_at")
        )[:10]

        for r in qs:
            score = r["urgency_score"] or 0
            if score >= 7:
                tier, tier_label = "high", "High Priority"
            elif score >= 4:
                tier, tier_label = "medium", "Medium Priority"
            else:
                tier, tier_label = "low", "Routine"

            reports.append({
                "category":       r["category"],
                "category_label": CATEGORY_LABELS.get(r["category"], r["category"]),
                "status":         r["status"],
                "status_label":   PUBLIC_STATUS_LABELS.get(r["status"], r["status"]),
                "barangay":       r["location_text"] or "Location not identified",
                "urgency_tier":   tier,
                "urgency_label":  tier_label,
                "created_at_iso": r["created_at"].isoformat() if r["created_at"] else None,
            })

        return JsonResponse({"reports": reports})


class PublicStatsView(View):
    """
    GET /api/public/stats/
    Returns lightweight public counters for the live ticker.
    """

    def get(self, request):
        today = timezone.localdate()
        now = timezone.now()
        resolved_cutoff = now - timedelta(days=30)
        resolved_today = StatusChange.objects.filter(
            to_status="resolved",
            changed_at__date=today,
        ).count()
        active = Report.objects.filter(status__in=ACTIVE_STATUSES).exclude(status="dismissed").count()
        total = (
            Report.objects
            .exclude(status="dismissed")
            .exclude(status="resolved", updated_at__lt=resolved_cutoff)
            .count()
        )
        resolved_total = Report.objects.filter(status="resolved").count()
        resolution_rate = round(resolved_total / total * 100) if total else 0

        return JsonResponse({
            "resolved_today":    resolved_today,
            "active_reports":    active,
            "total_reports":     total,
            "resolved_total":    resolved_total,
            "resolution_rate":   resolution_rate,
        })
