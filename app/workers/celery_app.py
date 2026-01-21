from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


def create_celery_app() -> Celery:
    """
    Создание и настройка экземпляра Celery
    """
    app = Celery(
        "deribit_tracker",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=["app.workers.tasks"],
    )

    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        # Настройки Redis
        broker_connection_retry_on_startup=True,
        broker_transport_options={
            "visibility_timeout": 3600,
            "socket_keepalive": True,
            "retry_on_timeout": True,
        },
        # Настройки задач
        task_acks_late=True,  # Подтверждение после выполнения
        task_reject_on_worker_lost=True,
        task_track_started=True,
        worker_prefetch_multiplier=1,  # По одной задаче на воркер
        worker_max_tasks_per_child=1000,  # Перезапуск после 1000 задач
        # Расписание (Beat)
        beat_schedule={
            # Задача получения цен каждую минуту
            "fetch-prices-every-minute": {
                "task": "fetch_prices_task",
                "schedule": crontab(minute="*"),
                "options": {"queue": "prices"},
            },
            # Проверка здоровья API каждые 5 минут
            "health-check-every-5-minutes": {
                "task": "health_check_task",
                "schedule": crontab(minute="*/5"),
                "options": {"queue": "monitoring"},
            },
        },
        # Очереди
        task_routes={
            "app.workers.tasks.fetch_prices_task": {"queue": "prices"},
            "app.workers.tasks.health_check_task": {"queue": "monitoring"},
        },
        # Обработка ошибок
        task_annotations={
            "*": {
                "rate_limit": "10/m",  # Ограничение 10 задач в минуту
                "max_retries": 3,
                "retry_backoff": True,
                "retry_backoff_max": 600,  # Максимум 10 минут
                "retry_jitter": True,  # Случайная задержка для предотвращения stampede
            }
        },
    )

    return app


celery_app = create_celery_app()
