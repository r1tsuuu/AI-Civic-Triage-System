"""
Dashboard Views — connected to triage.Report pipeline (Phase 2).
"""

from __future__ import annotations

import csv
from typing import ClassVar

from django.views.generic import TemplateView, ListView, DetailView, View
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.db.models import Count
from datetime import timedelta, datetime
from django.core.paginator import Paginator

from apps.triage.models import Report, StatusChange, CorrectionLog
from apps.triage.exceptions import InvalidTransitionError


class StatsView(TemplateView):
    template_name = 'dashboard/stats.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)

        total = Report.objects.count()
        reports_24h = Report.objects.filter(created_at__gte=twenty_four_hours_ago).count()
        resolved = Report.objects.filter(status='resolved').count()
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


class ReportListView(ListView):
    model = Report
    template_name = 'dashboard/list_view.html'
    context_object_name = 'reports'
    paginate_by = 20

    def get_queryset(self):
        qs = Report.objects.select_related('raw_post').order_by('-urgency_score')
        category_filter = self.request.GET.get('category')
        status_filter = self.request.GET.get('status')
        barangay_filter = self.request.GET.get('barangay')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')

        if category_filter:
            qs = qs.filter(category=category_filter)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if barangay_filter:
            qs = qs.filter(location_text__icontains=barangay_filter)
        if date_from:
            try:
                from_date = timezone.datetime.fromisoformat(date_from)
                qs = qs.filter(created_at__gte=from_date)
            except (ValueError, AttributeError):
                pass
        if date_to:
            try:
                to_date = timezone.datetime.fromisoformat(date_to) + timedelta(days=1)
                qs = qs.filter(created_at__lt=to_date)
            except (ValueError, AttributeError):
                pass
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for report in context['reports']:
            # confidence_tier and confidence_pct drive the UI colour coding
            report.confidence_pct  = round(report.classifier_confidence * 100, 1)
            report.confidence_tier = report.confidence_tier  # model property

        context['category_filter'] = self.request.GET.get('category', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['barangay_filter'] = self.request.GET.get('barangay', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['category_options'] = [
            'disaster_flooding', 'transportation_traffic', 'public_infrastructure',
            'public_safety', 'other', 'uncertain',
        ]
        context['status_options'] = [
            'for_review', 'reported', 'acknowledged', 'in_progress', 'resolved', 'dismissed',
        ]
        context['barangay_options'] = list(
            Report.objects
            .exclude(location_text__isnull=True)
            .exclude(location_text='')
            .values_list('location_text', flat=True)
            .distinct()[:50]
        )
        return context


class ReportDetailView(DetailView):
    model = Report
    template_name = 'dashboard/report_detail.html'
    context_object_name = 'report'

    def get_queryset(self):
        return Report.objects.select_related('raw_post')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = context['report']
        threshold = getattr(settings, 'NLP_CONFIDENCE_THRESHOLD', 0.65)

        # Template compatibility aliases
        report.confidence = report.classifier_confidence
        report.confidence_pct = round(report.classifier_confidence * 100, 1)
        report.confidence_threshold_pct = int(Report.CONFIDENCE_THRESHOLD * 100)
        report.barangay = report.location_text or ''
        report.current_status = report.status

        context['status_changes'] = list(
            StatusChange.objects.filter(report=report).order_by('changed_at')
        )

        from apps.response.templates_config import get_reply_text
        context['simulated_reply_preview'] = get_reply_text(report.category)

        context['available_next_statuses'] = Report.VALID_TRANSITIONS.get(report.status, [])
        context['all_statuses'] = ['reported', 'acknowledged', 'in_progress', 'resolved']
        context['category_options'] = [
            'disaster_flooding', 'transportation_traffic', 'public_infrastructure',
            'public_safety', 'other', 'uncertain',
        ]
        context['corrections'] = report.corrections.all().order_by('-corrected_at')
        from apps.triage.scorer import compute_score_with_breakdown
        _, breakdown = compute_score_with_breakdown(
            report.raw_post.post_text if report.raw_post else ''
        )
        context['signal_breakdown'] = breakdown
        return context


class HistoryView(ListView):
    model = StatusChange
    template_name = 'dashboard/history.html'
    context_object_name = 'status_changes'
    paginate_by = 50

    def get_queryset(self):
        qs = StatusChange.objects.select_related('report').order_by('-changed_at')
        date_from_str = self.request.GET.get('date_from', '')
        date_to_str = self.request.GET.get('date_to', '')
        report_id_search = self.request.GET.get('report_id', '')

        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d').replace(
                    tzinfo=timezone.utc)
                qs = qs.filter(changed_at__gte=date_from)
            except ValueError:
                pass
        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d').replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc)
                qs = qs.filter(changed_at__lte=date_to)
            except ValueError:
                pass
        if report_id_search:
            qs = qs.filter(report__id__icontains=report_id_search)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['report_id'] = self.request.GET.get('report_id', '')
        context['total_changes'] = self.get_queryset().count()
        return context


class HistoryExportView(View):
    def get(self, request):
        qs = StatusChange.objects.select_related('report').order_by('-changed_at')
        date_from_str = request.GET.get('date_from', '')
        date_to_str = request.GET.get('date_to', '')
        report_id_search = request.GET.get('report_id', '')

        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d').replace(
                    tzinfo=timezone.utc)
                qs = qs.filter(changed_at__gte=date_from)
            except ValueError:
                pass
        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d').replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc)
                qs = qs.filter(changed_at__lte=date_to)
            except ValueError:
                pass
        if report_id_search:
            qs = qs.filter(report__id__icontains=report_id_search)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="acts_history_export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Report ID', 'From Status', 'To Status', 'Note', 'Changed By'])
        for sc in qs:
            writer.writerow([
                sc.changed_at.strftime('%Y-%m-%d %H:%M:%S'),
                str(sc.report_id),
                sc.from_status,
                sc.to_status,
                sc.note or '',
                sc.changed_by,
            ])
        return response


class MapView(TemplateView):
    template_name = 'dashboard/map.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Lipa City Hall per CONSTITUTION.md §14
        context['map_center'] = {'lat': 13.9420, 'lng': 121.1628}
        context['map_zoom'] = 14
        return context


class ReportsGeoJSONView(View):
    def get(self, request):
        features = []
        unresolved = []
        for r in Report.objects.select_related('raw_post'):
            preview = r.raw_post.post_text[:120] if r.raw_post else ''
            if r.latitude is not None and r.longitude is not None:
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [r.longitude, r.latitude],
                    },
                    'properties': {
                        'id': str(r.id),
                        'lat': r.latitude,
                        'lng': r.longitude,
                        'category': r.category,
                        'urgency_score': r.urgency_score,
                        'status': r.status,
                        'message_preview': preview,
                    },
                })
            else:
                unresolved.append({
                    'id': str(r.id),
                    'category': r.category,
                    'urgency_score': r.urgency_score,
                    'status': r.status,
                    'message_preview': preview,
                })
        return JsonResponse({
            'type': 'FeatureCollection',
            'features': features,
            'unresolved': unresolved,
        })


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


class _BaseStatusActionView(View):
    target_status: ClassVar[str]
    http_method_names = ['post']

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        try:
            report.transition_to(self.target_status, moderator_name="demo")
        except InvalidTransitionError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                f"Report marked as {self.target_status.replace('_', ' ')}.",
            )
        return redirect('dashboard:report_detail', pk=pk)


class AcknowledgeReportView(_BaseStatusActionView):
    target_status = 'acknowledged'


class InProgressReportView(_BaseStatusActionView):
    target_status = 'in_progress'


class ResolveReportView(_BaseStatusActionView):
    target_status = 'resolved'

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        try:
            report.transition_to(self.target_status, moderator_name="demo")
        except InvalidTransitionError as exc:
            messages.error(request, str(exc))
        else:
            if report.raw_post_id:
                from apps.mock_fb.models import MockComment
                MockComment.objects.create(
                    raw_post_id=report.raw_post_id,
                    author="Lipa City LGU Official",
                    text=(
                        "Hello! This is the LGU Automated System. "
                        "Our team has addressed this issue. "
                        "Thank you for reporting!"
                    ),
                )
            messages.success(
                request,
                "Success! A simulated response has been sent to the citizen's Facebook thread.",
                extra_tags="mock-resolve",
            )
        return redirect('dashboard:report_detail', pk=pk)


class DismissReportView(_BaseStatusActionView):
    target_status = 'dismissed'

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        try:
            report.transition_to(self.target_status, moderator_name="demo")
        except InvalidTransitionError as exc:
            messages.error(request, str(exc))
        else:
            if report.raw_post_id:
                from apps.mock_fb.models import MockComment
                MockComment.objects.create(
                    raw_post_id=report.raw_post_id,
                    author="Lipa City LGU Official",
                    text=(
                        "Hello. We have reviewed your post, but it does not fall under "
                        "civic concerns or is a duplicate. No further action will be taken."
                    ),
                )
            messages.success(request, "Report dismissed.")
        return redirect('dashboard:report_detail', pk=pk)


class OverrideReportView(View):
    """
    POST /dashboard/reports/<pk>/override/
    Handles the Edit Report modal form.  Persists any changed fields,
    logs category/location changes to CorrectionLog, and marks the
    report as manually corrected (ground-truth for future training).
    """
    http_method_names = ['post']

    def post(self, request, pk):
        from apps.dashboard.forms import ReportEditForm

        report = get_object_or_404(Report, pk=pk)
        form = ReportEditForm(request.POST)

        if not form.is_valid():
            error_str = '; '.join(
                f"{f}: {', '.join(errs)}" for f, errs in form.errors.items()
            )
            messages.error(request, f"Could not save: {error_str}")
            return redirect('dashboard:report_detail', pk=pk)

        cd = form.cleaned_data
        changes_made = []
        update_fields = ['updated_at']

        # ── Category ─────────────────────────────────────────────────────────
        new_category = cd.get('category') or ''
        if new_category and new_category != report.category:
            CorrectionLog.objects.create(
                report=report,
                old_category=report.category,
                new_category=new_category,
            )
            report.category = new_category
            update_fields.append('category')
            changes_made.append('category')

        # ── Urgency score ─────────────────────────────────────────────────────
        new_urgency = cd.get('urgency_score')
        if new_urgency is not None and new_urgency != report.urgency_score:
            report.urgency_score = new_urgency
            update_fields.append('urgency_score')
            changes_made.append('urgency score')

        # ── Location name ─────────────────────────────────────────────────────
        new_location_text = cd.get('location_text') or ''
        if new_location_text and new_location_text != report.location_text:
            CorrectionLog.objects.create(
                report=report,
                old_location=report.location_text,
                new_location=new_location_text,
            )
            report.location_text = new_location_text
            update_fields.append('location_text')
            changes_made.append('location name')

        # ── Coordinates (lat + lng must arrive together) ──────────────────────
        new_lat = cd.get('latitude')
        new_lng = cd.get('longitude')
        if new_lat is not None and new_lng is not None:
            if new_lat != report.latitude or new_lng != report.longitude:
                report.latitude = new_lat
                report.longitude = new_lng
                report.location_confidence = 'manual'
                update_fields.extend(['latitude', 'longitude', 'location_confidence'])
                changes_made.append('coordinates')

        if changes_made:
            report.is_manually_corrected = True
            update_fields.append('is_manually_corrected')
            report.save(update_fields=update_fields)
            label = ', '.join(changes_made)
            messages.success(
                request,
                f"✓ Report corrected ({label}). Marked as ground-truth.",
                extra_tags='mock-resolve',
            )
        else:
            messages.warning(request, "No fields were changed.")

        return redirect('dashboard:report_detail', pk=pk)


# ── Public Citizen Transparency Portal ──────────────────────────────────────


class LandingView(TemplateView):
    template_name = "portal/index.html"


class PublicGeoJSONView(View):
    """
    GET /api/public/geojson/
    Anonymised GeoJSON for the citizen transparency map.
    Only exposes: category, display_status, barangay. No raw text, no IDs, no names.
    """

    CATEGORY_LABELS: ClassVar[dict] = {
        "disaster_flooding":      "Flooding / Disaster",
        "transportation_traffic": "Traffic / Roads",
        "public_infrastructure":  "Infrastructure",
        "public_safety":          "Public Safety",
        "other":                  "Other",
    }

    STATUS_LABELS: ClassVar[dict] = {
        "reported":     "Pending",
        "acknowledged": "Acknowledged",
        "in_progress":  "In Progress",
        "resolved":     "Resolved",
        "dismissed":    "Closed",
    }

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
                    "category_label": self.CATEGORY_LABELS.get(r["category"], r["category"]),
                    "status":         r["status"],
                    "status_label":   self.STATUS_LABELS.get(r["status"], r["status"]),
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
        active = Report.objects.filter(
            status__in=["reported", "acknowledged", "in_progress"]
        ).count()
        total = Report.objects.count()

        return JsonResponse({
            "resolved_today": resolved_today,
            "active_reports":  active,
            "total_reports":   total,
        })
