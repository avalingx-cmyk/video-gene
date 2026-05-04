from celery import Celery
from celery.schedules import crontab

from app.tasks.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "cleanup-expired-segments": {
        "task": "app.tasks.retention_tasks.cleanup_expired_segments_task",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "maintenance"},
    },
}

celery_app.conf.timezone = "UTC"