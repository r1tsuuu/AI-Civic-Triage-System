from django.test import TestCase
from django.db import IntegrityError
from apps.webhook.models import RawPost


class RawPostModelTest(TestCase):

    def test_str(self):
        post = RawPost(facebook_post_id="abc123", post_text="Baha sa Brgy. San Jose")
        self.assertEqual(str(post), "RawPost(abc123)")

    def test_default_processed_is_false(self):
        post = RawPost.objects.create(
            facebook_post_id="post_001",
            post_text="May butas sa daan sa Padre Garcia.",
        )
        self.assertFalse(post.processed)

    def test_uuid_primary_key_is_auto_generated(self):
        post = RawPost.objects.create(
            facebook_post_id="post_002",
            post_text="Walang tubig sa Brgy. Marawoy.",
        )
        self.assertIsNotNone(post.id)

    def test_duplicate_facebook_post_id_raises_integrity_error(self):
        RawPost.objects.create(
            facebook_post_id="duplicate_id",
            post_text="First post.",
        )
        with self.assertRaises(IntegrityError):
            RawPost.objects.create(
                facebook_post_id="duplicate_id",
                post_text="Second post with same ID.",
            )

    def test_received_at_is_auto_set(self):
        post = RawPost.objects.create(
            facebook_post_id="post_003",
            post_text="Sunog sa Brgy. Balintawak!",
        )
        self.assertIsNotNone(post.received_at)