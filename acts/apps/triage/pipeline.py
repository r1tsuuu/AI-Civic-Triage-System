import logging
from apps.triage.models import Report
from apps.triage.classifier import classify
from apps.triage.ner import extract_locations, geocode
from apps.triage.scorer import compute_score

logger = logging.getLogger(__name__)

def process_post(raw_post):
    """
    Orchestrate the flow: classify -> extract locations -> geocode -> score ->
    save Report -> mark raw_post.processed = True.

    Confidence threshold: if the classifier's confidence is below
    Report.CONFIDENCE_THRESHOLD (65 %), the report is created with
    status='for_review' and category='uncertain' so a human moderator
    must verify it before it enters the normal workflow.
    """
    try:
        text = raw_post.post_text

        category, clf_conf = classify(text)
        locations = extract_locations(text)

        lat, lon, loc_conf = None, None, "unresolved"
        location_text = None
        if locations:
            location_text = ", ".join(locations)
            lat, lon, loc_conf = geocode(locations[0])

        has_image = getattr(raw_post, 'has_image', False)
        reaction_count = getattr(raw_post, 'reaction_count', 0)

        score = compute_score(text, has_image=has_image, reaction_count=reaction_count)

        # ── Confidence gate ──────────────────────────────────────────────────
        if clf_conf < Report.CONFIDENCE_THRESHOLD:
            initial_status = "for_review"
            initial_category = "uncertain"
            routing_notes = (
                f"Low confidence: {clf_conf * 100:.1f}% "
                f"(threshold {Report.CONFIDENCE_THRESHOLD * 100:.0f}%). "
                f"Original prediction: {category}. Awaiting human review."
            )
            logger.info(
                "Low-confidence classification for post %s: %s (%.1f%%) → for_review",
                raw_post.id, category, clf_conf * 100,
            )
        else:
            initial_status = "reported"
            initial_category = category
            routing_notes = ""

        report = Report.objects.create(
            raw_post=raw_post,
            category=initial_category,
            classifier_confidence=clf_conf,
            urgency_score=score,
            location_text=location_text,
            latitude=lat,
            longitude=lon,
            location_confidence=loc_conf,
            status=initial_status,
            routing_notes=routing_notes,
        )
        
        raw_post.processed = True
        raw_post.save()
        return report
        
    except Exception as e:
        logger.error(f"Catastrophic failure in process_post: {e}", exc_info=True)
        try:
            report = Report.objects.create(
                raw_post=raw_post,
                category="other",
                classifier_confidence=0.0,
                urgency_score=0.0,
                location_text=None,
                latitude=None,
                longitude=None,
                location_confidence="unresolved",
                status="reported"
            )
            raw_post.processed = True
            raw_post.save()
            return report
        except Exception as inner_e:
            logger.error(f"Failed to create fallback report: {inner_e}", exc_info=True)
            return None