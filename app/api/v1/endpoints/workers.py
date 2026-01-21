import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel

from app.db.session import get_db

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()


class TaskStatusResponse(BaseModel):
    """Ответ со статусом задачи"""
    task_id: str
    status: str
    ready: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TriggerTaskResponse(BaseModel):
    """Ответ на запуск задачи"""
    task_id: str
    status: str
    check_status: str


class HealthCheckResponse(BaseModel):
    """Ответ проверки здоровья"""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None


class QueueInfoResponse(BaseModel):
    """Информация об очередях"""
    queues: Dict[str, Dict[str, Any]]
    workers: Dict[str, Any]
    redis: Dict[str, Any]


@router.post("/trigger-fetch-prices", response_model=TriggerTaskResponse)
async def trigger_fetch_prices(background_tasks: BackgroundTasks):
    """Ручной запуск задачи получения цен"""

    logger.info("Ручной запуск задачи получения цен")

    try:
        task = celery_app.tasks["fetch_prices_task"].apply_async()

        return TriggerTaskResponse(
            task_id=task.id,
            status="PENDING",
            check_status=f"/v1/workers/tasks/{task.id}"
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске задачи: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при запуске задачи: {str(e)}")


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Получение статуса задачи"""

    try:
        task = celery_app.AsyncResult(task_id)

        result = None
        if task.ready():
            try:
                result = task.get(timeout=1)
            except Exception as e:
                result = {"error": str(e)}

        return TaskStatusResponse(
            task_id=task_id,
            status=task.status,
            ready=task.ready(),
            result=result
        )
    except Exception as e:
        logger.error(f"Ошибка при получении статуса задачи task_id = {task_id}: {e}")
        return TaskStatusResponse(
            task_id=task_id,
            status="PENDING",
            ready=False,
            error=str(e)
        )


@router.get("/health", response_model=HealthCheckResponse)
async def check_celery_health():
    """Проверка здоровья Celery"""

    logger.info("Запрос проверки здоровья Celery")

    try:
        task = celery_app.tasks["health_check_task"].apply_async()

        result = task.get(timeout=10)

        return HealthCheckResponse(
            task_id=task.id,
            status=task.status,
            result=result
        )
    except Exception as e:
        logger.error(f"Ошибка при проверке здоровья Celery: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при проверке здоровья: {str(e)}")


@router.get("/queues", response_model=QueueInfoResponse)
async def get_queue_info():
    """Получение информации об очередях и воркерах"""

    try:
        try:
            from redis import Redis
            redis_client = Redis.from_url(celery_app.conf.broker_url)
            redis_connected = redis_client.ping()
        except ImportError:
            redis_connected = False
        except Exception:
            redis_connected = False

        inspector = celery_app.control.inspect()

        active_workers = {}
        registered_tasks = {}

        if inspector:
            active_workers = inspector.active() or {}
            registered_tasks = inspector.registered() or {}

        queues_info = {
            "celery": {"length": 0},
            "prices": {"length": 2},
            "monitoring": {"length": 1}
        }

        return QueueInfoResponse(
            queues=queues_info,
            workers={
                "count": len(active_workers),
                "active": list(active_workers.keys()),
                "registered": registered_tasks
            },
            redis={
                "connected": redis_connected,
                "broker_url": celery_app.conf.broker_url
            }
        )
    except Exception as e:
        logger.error(f"Ошибка при получении информации об очередях: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении информации: {str(e)}")
