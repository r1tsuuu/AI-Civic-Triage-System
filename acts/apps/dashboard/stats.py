"""Dashboard stats views."""

from __future__ import annotations

from django.views.generic import TemplateView, View
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Count, Avg
from datetime import timedelta

from apps.triage.models import Report, StatusChange
from apps.triage.constants import ACTIVE_STATUSES


class StatsView(TemplateView):
    template_name = 'dashboard/stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)

        total    = Report.objects.count()
        resolved = Report.objects.filter(status='resolved').count()
        reports_24h    = Report.objects.filter(created_at__gte=twenty_four_hours_ago).count()
        resolution_rate = round(resolved / total * 100) if total else 0

        most_affected = (
            Report.objects
            .exclude(location_text__isnull=True)
            .exclude(location_text='')
            .values('location_text')
            .annotate(count=Count('id'))
            .order_by('-count')
            .first()
        )
        most_reported = (
            Report.objects
            .values('category')
            .annotate(count=Count('id'))
            .order_by('-count')
            .first()
        )

        # ── Impact metric 1: Average Response Time ────────────────────────
        resolved_changes = (
            StatusChange.objects
            .filter(to_status='resolved')
            .select_related('report')
        )
        durations = [
            (sc.changed_at - sc.report.created_at).total_seconds() / 3600
            for sc in resolved_changes
            if sc.report and sc.report.created_at
        ]
        avg_hours = round(sum(durations) / len(durations), 1) if durations else None
        if avg_hours is None:
            avg_response_display = "N/A"
            avg_response_sub = "No resolved reports yet"
        elif avg_hours < 1:
            avg_response_display = f"{int(avg_hours * 60)} min"
            avg_response_sub = f"Across {len(durations)} resolved report{'s' if len(durations) != 1 else ''}"
        else:
            avg_response_display = f"{avg_hours} hrs"
            avg_response_sub = f"Across {len(durations)} resolved report{'s' if len(durations) != 1 else ''}"

        # ── Impact metric 2: Top Emergency Zone ───────────────────────────
        top_zone = (
            Report.objects
            .exclude(location_text__isnull=True)
            .exclude(location_text='')
            .values('location_text')
            .annotate(avg_urgency=Avg('urgency_score'), report_count=Count('id'))
            .filter(report_count__gte=1)
            .order_by('-avg_urgency')
            .first()
        )
        if top_zone:
            top_zone_name  = top_zone['location_text']
            top_zone_score = round(top_zone['avg_urgency'], 1)
            top_zone_count = top_zone['report_count']
        else:
            top_zone_name  = "N/A"
            top_zone_score = 0
            top_zone_count = 0

        active = Report.objects.filter(status__in=ACTIVE_STATUSES).count()

        context['impact'] = {
            'avg_response_display': avg_response_display,
            'avg_response_sub':     avg_response_sub,
            'top_zone_name':        top_zone_name,
            'top_zone_score':       top_zone_score,
            'top_zone_count':       top_zone_count,
            'resolution_rate':      resolution_rate,
            'resolved_count':       resolved,
            'total_count':          total,
            'active_count':         active,
        }

        context['stats'] = {
            'reports_24h': reports_24h,
            'reports_24h_change': 0,
            'resolution_rate': resolution_rate,
            'resolution_rate_change': 0,
            'most_affected_barangay': most_affected['location_text'] if most_affected else 'N/A',
            'most_affected_count': most_affected['count'] if most_affected else 0,
            'most_reported_category': most_reported['category'] if most_reported else 'N/A',
            'most_reported_count': most_reported['count'] if most_reported else 0,
        }
        return context


class StatsDataView(View):
    def get(self, request):
        try:
            now = timezone.now()
            seven_days_ago = now - timedelta(days=7)

            cat_qs = (
                Report.objects
                .filter(created_at__gte=seven_days_ago)
                .values('category')
                .annotate(count=Count('id'))
                .order_by('-count')[:5]
            )
            top_categories = [
                {'category': row['category'], 'count': row['count']} for row in cat_qs
            ]

            loc_qs = (
                Report.objects
                .filter(created_at__gte=seven_days_ago)
                .exclude(location_text__isnull=True)
                .exclude(location_text='')
                .values('location_text')
                .annotate(count=Count('id'))
                .order_by('-count')[:5]
            )
            top_barangays = [
                {'barangay': row['location_text'], 'count': row['count']} for row in loc_qs
            ]

            avg_hours = None
            resolved_changes = StatusChange.objects.filter(
                to_status='resolved'
            ).select_related('report')
            durations = []
            for sc in resolved_changes:
                if sc.report.created_at:
                    durations.append(
                        (sc.changed_at - sc.report.created_at).total_seconds() / 3600
                    )
            if durations:
                avg_hours = round(sum(durations) / len(durations), 1)

            return JsonResponse({
                'top_categories': top_categories,
                'top_barangays': top_barangays,
                'avg_resolution_hours': avg_hours,
            })
        except Exception as exc:
            return JsonResponse({
                'error': str(exc),
                'top_categories': [],
                'top_barangays': [],
                'avg_resolution_hours': None,
            })
