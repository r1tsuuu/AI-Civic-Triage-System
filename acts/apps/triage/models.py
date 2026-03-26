import uuid
from django.db import models
from .exceptions import InvalidTransitionError

class Report(models.Model):
    VALID_TRANSITIONS = {
        'reported':     ['acknowledged', 'dismissed'],
        'acknowledged': ['in_progress', 'dismissed'],
        'in_progress':  ['resolved', 'dismissed'],
        'resolved':     [],
        'dismissed':    [],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    raw_post = models.ForeignKey('webhook.RawPost', on_delete=models.CASCADE)
    category = models.CharField(max_length=50)
    classifier_confidence = models.FloatField(default=0.0)
    urgency_score = models.FloatField(default=0.0)
    location_text = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_confidence = models.CharField(max_length=50, default="unresolved")

    STATUS_CHOICES = [
        ('reported', 'Reported'),
        ('acknowledged', 'Acknowledged'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='reported')
    routing_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def transition_to(self, new_status, moderator_name="demo"):
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition from '{self.status}' to '{new_status}'. "
                f"Allowed: {allowed or 'none (terminal state)'}."
            )
        StatusChange.objects.create(
            report=self,
            from_status=self.status,
            to_status=new_status,
            changed_by=moderator_name,
        )
        self.status = new_status
        self.save()

class StatusChange(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='status_changes')
    from_status = models.CharField(max_length=50)
    to_status = models.CharField(max_length=50)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True, null=True)
    changed_by = models.CharField(max_length=255)

class CorrectionLog(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='corrections')
    old_category = models.CharField(max_length=50, null=True, blank=True)
    new_category = models.CharField(max_length=50, null=True, blank=True)
    old_location = models.CharField(max_length=255, null=True, blank=True)
    new_location = models.CharField(max_length=255, null=True, blank=True)
    corrected_at = models.DateTimeField(auto_now_add=True)  # renamed from created_at
