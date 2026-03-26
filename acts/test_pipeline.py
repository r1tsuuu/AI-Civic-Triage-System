"""
Quick smoke-test script for the NLP pipeline.
Run directly (not via Django test runner):
    .venv/bin/python test_pipeline.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.triage.pipeline import process_post
from apps.webhook.models import RawPost
import uuid

rp = RawPost(
    facebook_post_id=f"test_smoke_{uuid.uuid4().hex[:8]}",
    post_text="Tulong! Lampas tao na baha dito sa Mataas na Lupa. May mga naiipit na matanda!",
)
rp.save()

report = process_post(rp)
if report:
    print(f"Category      : {report.category} (conf: {report.classifier_confidence:.2f})")
    print(f"Urgency Score : {report.urgency_score} / 10.0")
    print(f"Location      : {report.location_text}")
    print(f"Coordinates   : {report.latitude}, {report.longitude} ({report.location_confidence})")
    print(f"Status        : {report.status}")
    report.delete()
else:
    print("ERROR: process_post returned None")

rp.delete()
