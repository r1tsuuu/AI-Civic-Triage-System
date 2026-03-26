"""Dashboard history views: audit log and CSV export."""

from __future__ import annotations

import csv
from datetime import datetime

from django.views.generic import ListView, View
from django.utils import timezone
from django.http import HttpResponse

from apps.triage.models import StatusChange


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
