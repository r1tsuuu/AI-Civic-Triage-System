"""Dashboard report views: list, detail, map, and status-action endpoints."""

from __future__ import annotations

from typing import ClassVar

from django.views.generic import ListView, DetailView, TemplateView, View
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count
from datetime import timedelta

from apps.triage.models import Report, StatusChange, CorrectionLog
from apps.triage.exceptions import InvalidTransitionError
from apps.triage.constants import ALL_CATEGORIES, ALL_STATUSES

_STALE_HOURS = 4
_UNASSIGNED_STATUSES = {'for_review', 'reported'}


def _format_elapsed(total_seconds: int) -> str:
    """Return a human-readable elapsed time string (e.g. '2h 15m ago')."""
    if total_seconds < 60:
        return f"{total_seconds}s ago"
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    rem = minutes % 60
    if hours < 24:
        return f"{hours}h {rem}m ago" if rem else f"{hours}h ago"
    return f"{hours // 24}d ago"


def _deduplicate_and_annotate(qs) -> list:
    """
    Pull the queryset into Python, cluster by (category, ~1 km grid),
    keep the highest-urgency report per cluster, and attach display
    attributes to every primary report:
      .duplicate_count  — how many additional reports share the cluster
      .time_elapsed     — "2h 15m ago" string
      .is_stale         — True when unassigned > STALE_HOURS
      .confidence       — alias for classifier_confidence (template convenience)
    """
    now = timezone.now()
    seen: dict = {}
    primaries: list = []

    for report in qs:
        # ── display helpers ──────────────────────────────────────────────
        report.confidence = report.classifier_confidence
        delta = now - report.created_at
        total_sec = int(delta.total_seconds())
        report.time_elapsed = _format_elapsed(total_sec)
        report.is_stale = (
            report.status in _UNASSIGNED_STATUSES
            and total_sec > _STALE_HOURS * 3600
        )

        # ── deduplication cluster ────────────────────────────────────────
        if report.latitude and report.longitude:
            cluster = (
                report.category,
                round(report.latitude, 2),
                round(report.longitude, 2),
            )
        else:
            cluster = None

        if cluster and cluster in seen:
            seen[cluster].duplicate_count += 1
        else:
            report.duplicate_count = 0
            if cluster:
                seen[cluster] = report
            primaries.append(report)

    return primaries


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

        # Return a plain list so ListView's Paginator (which accepts any
        # sequence) can page over the deduplicated, annotated result.
        return _deduplicate_and_annotate(qs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category_filter'] = self.request.GET.get('category', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['barangay_filter'] = self.request.GET.get('barangay', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['category_options'] = ALL_CATEGORIES
        context['status_options'] = ALL_STATUSES
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

        # Template compatibility aliases (confidence_pct is already a model property)
        report.confidence = report.classifier_confidence
        report.confidence_threshold = Report.CONFIDENCE_THRESHOLD
        report.confidence_threshold_pct = int(Report.CONFIDENCE_THRESHOLD * 100)
        report.barangay = report.location_text or ''
        report.current_status = report.status

        context['status_changes'] = list(
            StatusChange.objects.filter(report=report).order_by('changed_at')
        )

        from apps.response.templates_config import get_reply_text
        reply_text = get_reply_text(report.category)
        context['simulated_reply_preview'] = reply_text
        context['auto_reply'] = reply_text

        # Fetch the most recent AutoReply record (created when moderator resolves)
        context['auto_reply_record'] = report.auto_replies.first()

        context['available_next_statuses'] = Report.VALID_TRANSITIONS.get(report.status, [])
        all_statuses = ['reported', 'acknowledged', 'in_progress', 'resolved']
        context['all_statuses'] = all_statuses
        context['current_status_index'] = (
            all_statuses.index(report.status)
            if report.status in all_statuses else -1
        )
        context['category_options'] = ALL_CATEGORIES
        context['corrections'] = report.corrections.all().order_by('-corrected_at')
        from apps.triage.scorer import compute_score_with_breakdown
        _, breakdown = compute_score_with_breakdown(
            report.raw_post.post_text if report.raw_post else ''
        )
        context['signal_breakdown'] = breakdown
        return context


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
                        'confidence_pct': round(r.classifier_confidence * 100),
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
            # Create MockComment for the public portal feed (use same Taglish text as AutoReply)
            if report.raw_post_id:
                try:
                    from apps.mock_fb.models import MockComment
                    from apps.response.templates_config import get_reply_text
                    MockComment.objects.create(
                        raw_post_id=report.raw_post_id,
                        author="Lipa City LGU Official",
                        text=get_reply_text(report.category),
                    )
                except Exception:
                    pass  # portal feed is non-critical

            # Fire automated reply (creates AutoReply record) in background thread
            from apps.response.sender import send_reply_async
            send_reply_async(report)

            messages.success(
                request,
                "Report resolved. Automated response sent to citizen.",
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
    Handles the Edit Report modal form.
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
                f"Report updated: {label} corrected and marked as ground-truth.",
                extra_tags='mock-resolve',
            )
        else:
            messages.warning(request, "No fields were changed.")

        return redirect('dashboard:report_detail', pk=pk)


class SaveRoutingNotesView(View):
    """
    POST /dashboard/reports/<pk>/notes/
    Saves the moderator's internal routing notes for a report via AJAX.
    Returns JSON {ok: true} on success.
    """
    http_method_names = ['post']

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        notes = request.POST.get('routing_notes', '').strip()
        report.routing_notes = notes
        report.save(update_fields=['routing_notes', 'updated_at'])
        return JsonResponse({'ok': True})


class FlagReportView(View):
    """
    POST /dashboard/reports/<pk>/flag/
    Prepends a flag reason to the report's routing_notes and forces
    status back to 'for_review' so the report re-enters the review queue.
    Returns JSON {ok: true} on success.
    """
    http_method_names = ['post']

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        reason = request.POST.get('reason', '').strip()
        if not reason:
            return JsonResponse({'ok': False, 'error': 'Reason is required.'}, status=400)

        flag_line = f"[FLAGGED] {reason}"
        existing = report.routing_notes.strip() if report.routing_notes else ''
        report.routing_notes = f"{flag_line}\n{existing}" if existing else flag_line
        update_fields = ['routing_notes', 'updated_at']

        # Push the report back to for_review if it's still in an active status
        from apps.triage.constants import ACTIVE_STATUSES
        if report.status in ACTIVE_STATUSES and report.status != 'for_review':
            old_status = report.status
            report.status = 'for_review'
            update_fields.append('status')
            StatusChange.objects.create(
                report=report,
                from_status=old_status,
                to_status='for_review',
                changed_by='demo',
                note=f'Flagged for senior review: {reason}',
            )

        report.save(update_fields=update_fields)
        return JsonResponse({'ok': True})
