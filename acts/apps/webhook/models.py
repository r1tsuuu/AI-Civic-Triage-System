import uuid
from django.db import models


class RawPost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    facebook_post_id = models.CharField(max_length=255, unique=True)
    post_text = models.TextField()
    received_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"RawPost({self.facebook_post_id})"