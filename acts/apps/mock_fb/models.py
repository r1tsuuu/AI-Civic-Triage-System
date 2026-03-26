import uuid
from django.db import models


class MockComment(models.Model):
    """
    Simulates an LGU reply comment on a citizen's Facebook post.
    Created automatically when a Report transitions to 'resolved' or 'dismissed'.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    raw_post = models.ForeignKey(
        'webhook.RawPost',
        on_delete=models.CASCADE,
        related_name='mock_comments',
    )
    author = models.CharField(max_length=100, default="Lipa City LGU Official")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"MockComment({self.raw_post_id}, {self.author})"
