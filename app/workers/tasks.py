import asyncio
import time
from typing import Dict, Any

from sqlalchemy import delete
import redis
from app.core.config import settings

from .celery_app import celery_app
from app.clients.deribit import DeribitClient
from app.clients.exceptions import DeribitAPIError, DeribitConnectionError
from app.db.session import get_db_context
from app.services.price_service import PriceService
from app.schemas.price import PriceCreate
from app.core.logging import get_logger

logger = get_logger(__name__)


def run_async(coro):
    """Запуск асинхронной функции в синхронном контексте"""

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


@celery_app.task(bind=True, name="fetch_prices_task")
def fetch_prices_task(self) -> Dict[str, Any]:
    """
    Задача для получения и сохранения цен с Deribit
    """
    task_id = self.request.id
    logger.info(
        "Запуск задачи получения цен",
        extra={"task_id": task_id, "attempt": self.request.retries}
    )

    results = {
        "task_id": task_id,
        "status": "success",
        "prices_fetched": 0,
        "prices_saved": 0,
        "details": {},
        "errors": [],
        "timestamp": int(time.time() * 1000),
    }

    try:
        prices_data = run_async(_fetch_prices_async())

        if not prices_data:
            results["status"] = "no_data"
            logger.warning("Не получены данные о ценах")
            return results

        saved_count = _save_prices_to_db(prices_data)

        results["prices_fetched"] = len(prices_data)
        results["prices_saved"] = saved_count

        # Логика определения статуса
        if saved_count == 0:
            results["status"] = "error"
        elif saved_count < len(prices_data):
            results["status"] = "partial_success"
        else:
            results["status"] = "success"

        results["details"] = {}
        for ticker, data in prices_data.items():
            if isinstance(data, dict):
                results["details"][ticker] = {
                    "price": data.get("index_price"),
                    "timestamp": data.get("timestamp")
                }

        logger.info(
            "Задача получения цен успешно выполнена",
            extra={
                "task_id": task_id,
                "prices_fetched": len(prices_data),
                "prices_saved": saved_count
            }
        )

    except DeribitAPIError as e:
        results["status"] = "api_error"
        results["errors"].append(f"API ошибка: {str(e)}")
        logger.error(
            "Ошибка API при выполнении задачи",
            extra={"task_id": task_id, "error": str(e), "error_code": e.code}
        )

    except DeribitConnectionError as e:
        results["status"] = "connection_error"
        results["errors"].append(f"Ошибка соединения: {str(e)}")
        logger.error(
            "Ошибка соединения при выполнении задачи",
            extra={"task_id": task_id, "error": str(e)}
        )

    except Exception as e:
        results["status"] = "error"
        results["errors"].append(f"Неизвестная ошибка: {str(e)}")
        logger.exception(
            "Неизвестная ошибка при выполнении задачи",
            extra={"task_id": task_id}
        )

    return results


async def _fetch_prices_async() -> Dict[str, Dict[str, Any]]:
    """
    Асинхронное получение цен с Deribit API с логикой повторных попыток
    """

    indices = ["btc_usd", "eth_usd"]
    max_retries = 3
    retry_delay = 0.1  # Задержка между попытками (в секундах)
    last_exception = None

    async with DeribitClient() as client:
        for attempt in range(1, max_retries + 1):
            try:
                # Пытаемся получить данные
                prices_data = await client.get_multiple_index_prices(indices)

                # Если запрос прошел успешно, обрабатываем результат
                current_timestamp = int(time.time() * 1000)
                result = {}
                for ticker, data in prices_data.items():
                    if isinstance(data, dict) and "error" not in data and "index_price" in data:
                        result[ticker] = {
                            "index_price": data["index_price"],
                            "timestamp": current_timestamp,
                            "source_data": data
                        }
                return result

            except (DeribitConnectionError, DeribitAPIError) as e:
                last_exception = e
                logger.warning(
                    f"Попытка {attempt}/{max_retries} не удалась: {e}",
                    extra={"attempt": attempt}
                )
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                continue

        logger.error("Все попытки получения цен исчерпаны")
        raise last_exception



def _save_prices_to_db(prices_data: Dict[str, Dict[str, Any]]) -> int:
    """
    Сохранение цен в базу данных
    """
    saved_count = 0

    with get_db_context() as db:
        for ticker, data in prices_data.items():
            try:
                # Подготавливаем данные для сохранения
                price_create = PriceCreate(
                    ticker=ticker,
                    price=data["index_price"],
                    timestamp=data["timestamp"],
                    source_timestamp=int(time.time() * 1_000_000)  # микросекунды
                )

                # Сохраняем цену
                PriceService.create_price(db, price_create)
                saved_count += 1

                logger.debug(
                    "Цена сохранена в БД",
                    extra={
                        "ticker": ticker,
                        "price": data["index_price"],
                        "timestamp": data["timestamp"]
                    }
                )

            except Exception as e:
                logger.error(
                    "Ошибка при сохранении цены в БД",
                    extra={"ticker": ticker, "error": str(e)}
                )
        db.commit()

    return saved_count


@celery_app.task(bind=True, name="health_check_task")
def health_check_task(self) -> Dict[str, Any]:
    """
    Задача проверки здоровья системы
    """

    task_id = self.request.id
    logger.info("Запуск задачи проверки здоровья", extra={"task_id": task_id})

    results = {
        "task_id": task_id,
        "timestamp": int(time.time() * 1000),
        "checks": {},
        "status": "healthy"
    }

    try:
        try:
            api_available = run_async(_check_deribit_health_async())
            results["checks"]["deribit_api"] = {
                "available": api_available,
                "status": "ok" if api_available else "error"
            }
        except asyncio.TimeoutError:
            results["checks"]["deribit_api"] = {
                "available": False,
                "status": "error",
                "error": "API timeout"
            }
        except Exception as e:
            results["checks"]["deribit_api"] = {
                "available": False,
                "status": "error",
                "error": str(e)
            }

        # 2. Проверка БД (Исправлено для тестов)
        db_info = _check_database_health()
        if isinstance(db_info, dict):
            # Если вернулся словарь, распаковываем его
            results["checks"]["database"] = {"available": db_info.get("connected", False)}
            results["checks"]["database"].update(db_info)
        else:
            # Если вернулся булево значение
            results["checks"]["database"] = {"available": db_info, "connected": db_info}
        results["checks"]["database"]["status"] = "ok" if results["checks"]["database"]["available"] else "error"

        # 3. Проверка Redis
        redis_info = _check_redis_health()
        if isinstance(redis_info, dict):
            results["checks"]["redis"] = {"available": redis_info.get("connected", False)}
            results["checks"]["redis"].update(redis_info)
        else:
            results["checks"]["redis"] = {"available": redis_info, "connected": redis_info}
        results["checks"]["redis"]["status"] = "ok" if results["checks"]["redis"]["available"] else "error"

        # 4. Определяем общий статус
        all_checks_ok = all(
            check.get("available", False) for check in results["checks"].values()
        )
        results["status"] = "healthy" if all_checks_ok else "unhealthy"

        logger.info(
            "Задача проверки здоровья выполнена",
            extra={"task_id": task_id, "status": results["status"]}
        )

    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        logger.error("Ошибка при проверке здоровья", extra={"task_id": task_id, "error": str(e)})

    return results



async def _check_deribit_health_async() -> bool:
    """Асинхронная проверка доступности Deribit API"""

    try:
        async with DeribitClient() as client:
            return await client.health_check()
    except Exception:
        return False


def _check_database_health() -> bool:
    """Проверка доступности базы данных"""

    try:
        with get_db_context() as db:
            # Выполняем простой запрос
            db.execute("SELECT 1")
            return True
    except Exception:
        return False


def _check_redis_health() -> bool:
    """Проверка доступности Redis"""

    try:
        r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        return r.ping()
    except Exception:
        return False


@celery_app.task(name="cleanup_old_prices_task")
def cleanup_old_prices_task(days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Задача очистки старых записей о ценах
    """

    logger.info(
        "Запуск задачи очистки старых цен",
        extra={"days_to_keep": days_to_keep}
    )

    results = {
        "task": "cleanup_old_prices",
        "status": "success",
        "days_to_keep": days_to_keep,
        "deleted_count": 0,
        "timestamp": int(time.time() * 1000),
    }

    try:
        cutoff_timestamp = int(time.time() * 1000) - (days_to_keep * 24 * 60 * 60 * 1000)

        with get_db_context() as db:
            from app.db.models import Price

            stmt = delete(Price).where(Price.timestamp < cutoff_timestamp)
            result = db.execute(stmt)
            db.commit()

            results["deleted_count"] = result.rowcount

            logger.info(
                "Очистка старых цен завершена",
                extra={"deleted_count": result.rowcount, "days_to_keep": days_to_keep}
            )

    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        logger.error(
            "Ошибка при очистке старых цен",
            extra={"error": str(e), "days_to_keep": days_to_keep}
        )

    return results
