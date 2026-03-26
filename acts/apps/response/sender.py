import logging

logger = logging.getLogger(__name__)


def send_reply(report) -> None:
    """
    Graph API reply removed for demo mode.
    The resolve action shows a simulated-response toast in the dashboard instead.
    """
    logger.info(
        "Mock mode: Graph API reply skipped for report %s (category=%s)",
        report.id,
        report.category,
    )
