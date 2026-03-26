"""Public citizen transparency portal views."""

from __future__ import annotations

from django.views.generic import TemplateView, View
from django.utils import timezone
from django.http import JsonResponse

from apps.triage.models import Report, StatusChange
from apps.triage.constants import CATEGORY_LABELS, STATUS_LABELS, ACTIVE_STATUSES


class LandingView(TemplateView):
    template_name = "portal/index.html"


class PublicGeoJSONView(View):
    """
    GET /api/public/geojson/
    Anonymised GeoJSON for the citizen transparency map.
    Only exposes: category, display_status, barangay. No raw text, no IDs, no names.
    """

    def get(self, request):
        features = []
        qs = Report.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
        ).values("category", "status", "location_text", "latitude", "longitude")

        for r in qs:
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
                    "status_label":   STATUS_LABELS.get(r["status"], r["status"]),
                    "barangay":       r["location_text"] or "Unknown",
                },
            })

        return JsonResponse({"type": "FeatureCollection", "features": features})


class PublicStatsView(View):
    """
    GET /api/public/stats/
    Returns lightweight public counters for the live ticker.
    """

    def get(self, request):
        today = timezone.localdate()
        resolved_today = StatusChange.objects.filter(
            to_status="resolved",
            changed_at__date=today,
        ).count()
        active = Report.objects.filter(status__in=ACTIVE_STATUSES).count()
        total = Report.objects.count()

        return JsonResponse({
            "resolved_today": resolved_today,
            "active_reports":  active,
            "total_reports":   total,
        })
