import uuid
from django.db import models
from apps.triage.exceptions import InvalidTransitionError


class RawPost(models.Model):
    STATUS_REPORTED = "reported"
    STATUS_ACKNOWLEDGED = "acknowledged"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_RESOLVED = "resolved"
    STATUS_DISMISSED = "dismissed"

    STATUS_CHOICES = [
        (STATUS_REPORTED, "Reported"),
        (STATUS_ACKNOWLEDGED, "Acknowledged"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_DISMISSED, "Dismissed"),
    ]

    # Allowed one-directional transitions: {from_status: [to_status, ...]}
    VALID_TRANSITIONS = {
        STATUS_REPORTED: [STATUS_ACKNOWLEDGED, STATUS_DISMISSED],
        STATUS_ACKNOWLEDGED: [STATUS_IN_PROGRESS, STATUS_DISMISSED],
        STATUS_IN_PROGRESS: [STATUS_RESOLVED, STATUS_DISMISSED],
        STATUS_RESOLVED: [],
        STATUS_DISMISSED: [],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    facebook_post_id = models.CharField(max_length=255, unique=True)
    post_text = models.TextField()
    received_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_REPORTED,
    )

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"RawPost({self.facebook_post_id})"

    def transition_to(self, new_status, moderator_name="demo"):
        """
        Transition this report to *new_status*.

        Raises InvalidTransitionError if the transition is not permitted by
        VALID_TRANSITIONS.  On success the instance is saved in-place.

        Args:
            new_status (str): One of the STATUS_* constants.
            moderator_name (str): Name of the acting moderator (for audit logs).
        """
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition from '{self.status}' to '{new_status}'. "
                f"Allowed transitions: {allowed or 'none (terminal state)'}."
            )
        self.status = new_status
        self.save(update_fields=["status"])


class CorrectionLog(models.Model):
    """
    TASK-041: Audit log for report field corrections/overrides
    
    Tracks all manual overrides made by moderators, including:
    - Which report was corrected
    - Which field was changed
    - Old and new values
    - Who made the change
    - When the change was made
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(RawPost, on_delete=models.CASCADE, related_name='corrections')
    field_name = models.CharField(max_length=50)  # e.g., 'category', 'location_text'
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    corrected_by = models.CharField(max_length=255, default='demo')
    corrected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-corrected_at"]

    def __str__(self):
        return f"CorrectionLog({self.report.id}, {self.field_name}: {self.old_value} → {self.new_value})"