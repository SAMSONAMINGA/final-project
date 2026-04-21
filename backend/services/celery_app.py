"""
Celery app configuration for async task handling.
Tasks: IMERG fetching, OpenWeather fetching, GATv2 inference, alert dispatch, model retraining.

Design decisions:
- Redis broker for task queue and result backend
- 5-minute beat schedule for periodic tasks (IMERG/OpenWeather/inference every 30 min)
- Task routing based on priority
- Automatic retries with exponential backoff
"""

from celery import Celery
from celery.schedules import schedule
from core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    "floodguard_ke",
    broker=settings.redis_broker_url,
    backend=settings.redis_broker_url,
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Nairobi",
    enable_utc=True,
    
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_max_retries=3,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        # IMERG fetch every 30 minutes
        "fetch-imerg": {
            "task": "services.tasks.imerg_task.fetch_imerg",
            "schedule": 30.0 * 60.0,  # 30 minutes in seconds
        },
        # OpenWeather fetch every 30 minutes
        "fetch-openweather": {
            "task": "services.tasks.openweather_task.fetch_openweather",
            "schedule": 30.0 * 60.0,
        },
        # GATv2 inference every 30 minutes
        "run-inference": {
            "task": "services.tasks.inference_task.run_inference",
            "schedule": 30.0 * 60.0,
        },
    },
)

# Task routing
celery_app.conf.task_routes = {
    "services.tasks.imerg_task.*": {"queue": "data_fetch"},
    "services.tasks.openweather_task.*": {"queue": "data_fetch"},
    "services.tasks.inference_task.*": {"queue": "inference"},
    "services.tasks.alert_task.*": {"queue": "alerts"},
}

# Task timeout
celery_app.conf.task_soft_time_limit = 300  # 5 minutes soft timeout
celery_app.conf.task_time_limit = 600  # 10 minutes hard timeout

logger.info("Celery app configured")
