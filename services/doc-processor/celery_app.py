"""Celery application configuration for the doc-processor worker."""

from celery import Celery
from celery.schedules import crontab

from common.config import get_settings

settings = get_settings()

app = Celery(
    "doc-processor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Results
    result_expires=3600,  # 1 hour

    # Routing
    task_routes={
        "process_documentation": {"queue": "doc-processing"},
        "scheduled_sync": {"queue": "doc-processing"},
    },

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Reliability
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# ---------------------------------------------------------------------------
# Beat schedule -- periodic documentation updates
# ---------------------------------------------------------------------------
app.conf.beat_schedule = {
    "daily-documentation-sync": {
        "task": "scheduled_sync",
        "schedule": crontab(hour=2, minute=0),  # Every day at 02:00 UTC
        "options": {"queue": "doc-processing"},
    },
}
