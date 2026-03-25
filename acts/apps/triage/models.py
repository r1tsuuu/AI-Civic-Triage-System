import uuid
from django.db import models
from .exceptions import InvalidTransitionError

class Report(models.Model):
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
        valid_next = []
        if self.status == 'reported':
            valid_next = ['acknowledged']
        elif self.status == 'acknowledged':
            valid_next = ['in_progress']
        elif self.status == 'in_progress':
            valid_next = ['resolved']
            
        if new_status == 'dismissed' or new_status in valid_next:
            StatusChange.objects.create(
                report=self,
                from_status=self.status,
                to_status=new_status,
                changed_by=moderator_name
            )
            self.status = new_status
            self.save()
        else:
            raise InvalidTransitionError(f"Cannot transition from {self.status} to {new_status}")

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
    created_at = models.DateTimeField(auto_now_add=True)
