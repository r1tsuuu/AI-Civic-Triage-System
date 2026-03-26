import uuid
from django.db import models


class AutoReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey('triage.Report', on_delete=models.CASCADE, related_name='auto_replies')
    reply_text = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    graph_api_success = models.BooleanField(default=False)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"AutoReply(report={self.report_id}, success={self.graph_api_success})"
