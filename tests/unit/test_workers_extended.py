import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.clients.exceptions import DeribitConnectionError
from app.workers.tasks import (
    _check_database_health,
    _check_redis_health,
    _fetch_prices_async,
    _save_prices_to_db,
    cleanup_old_prices_task,
    fetch_prices_task,
    health_check_task,
)


class TestCeleryTasksExtended:
    """Расширенные тесты Celery задач"""

    @patch("app.workers.tasks.run_async")
    @patch("app.workers.tasks._fetch_prices_async")
    @patch("app.workers.tasks._save_prices_to_db")
    def test_fetch_prices_task_partial_success(self, mock_save, mock_fetch, mock_run):
        """Тест частично успешного получения цен"""

        mock_run.return_value = {
            "btc_usd": {"index_price": 95194.62, "timestamp": 1705593600000},
            "eth_usd": {"index_price": None, "timestamp": 1705593600000},
            "invalid": "wrong_format",
        }

        mock_fetch.return_value = None

        mock_save.return_value = 1

        result = fetch_prices_task()

        assert result["status"] == "partial_success"
        assert result["prices_fetched"] == 3
        assert result["prices_saved"] == 1
        assert "details" in result
        assert "errors" in result

    @patch("app.workers.tasks.run_async")
    @patch("app.workers.tasks._save_prices_to_db")
    def test_fetch_prices_task_with_validation_errors(self, mock_save, mock_run_async):
        """Тест с ошибками валидации при сохранении"""

        mock_run_async.return_value = {
            "btc_usd": {"index_price": 95194.62, "timestamp": 1705593600000},
            "eth_usd": {"index_price": -100.0, "timestamp": 1705593600000},
        }
        mock_save.side_effect = Exception("Validation error")

        result = fetch_prices_task()

        assert result["status"] == "error"
        assert "validation error" in result["errors"][0].lower()

    @patch("app.workers.tasks._check_database_health")
    @patch("app.workers.tasks._check_redis_health")
    @patch("app.workers.tasks.run_async")
    def test_health_check_task_with_detailed_info(
        self, mock_run_async, mock_redis_health, mock_db_health
    ):
        """Тест детальной проверки здоровья"""

        mock_run_async.return_value = True
        mock_db_health.return_value = {
            "connected": True,
            "tables": 5,
            "can_write": True,
        }
        mock_redis_health.return_value = {
            "connected": True,
            "memory_used": "1.2MB",
            "clients": 3,
        }

        result = health_check_task()

        assert result["status"] == "healthy"
        assert result["checks"]["deribit_api"]["available"] is True
        assert result["checks"]["database"]["connected"] is True
        assert result["checks"]["redis"]["connected"] is True

    @patch("app.workers.tasks._check_database_health")
    @patch("app.workers.tasks._check_redis_health")
    @patch("app.workers.tasks.run_async")
    @patch("app.workers.tasks._check_deribit_health_async")
    def test_health_check_task_timeout(
        self, mock_deri_async, mock_run_async, mock_redis_health, mock_db_health
    ):
        """Тест проверки здоровья с таймаутом"""

        mock_deri_async.return_value = None
        mock_run_async.side_effect = asyncio.TimeoutError("API timeout")
        mock_db_health.return_value = False
        mock_redis_health.return_value = True

        result = health_check_task()

        assert result["status"] == "unhealthy"
        assert "timeout" in result["checks"]["deribit_api"].get("error", "").lower()

    @patch("app.workers.tasks.get_db_context")
    def test_cleanup_old_prices_with_different_periods(self, mock_db_context):
        """Тест очистки с разными периодами"""

        mock_session = Mock()
        mock_db = Mock()
        mock_db.__enter__ = Mock(return_value=mock_session)
        mock_db.__exit__ = Mock(return_value=None)
        mock_db_context.return_value = mock_db

        test_periods = [1, 7, 30, 90, 365]

        for days in test_periods:
            mock_result = Mock()
            mock_result.rowcount = days * 10

            with patch("app.workers.tasks.delete") as mock_delete:
                mock_session.execute.return_value = mock_result

                result = cleanup_old_prices_task(days_to_keep=days)

                assert result["task"] == "cleanup_old_prices"
                assert result["days_to_keep"] == days
                assert result["deleted_count"] == days * 10
                mock_delete.assert_called_once()

    @patch("app.workers.tasks.get_db_context")
    def test_cleanup_old_prices_error(self, mock_db_context):
        """Тест ошибки при очистке"""

        mock_session = Mock()
        mock_db = Mock()
        mock_db.__enter__ = Mock(return_value=mock_session)
        mock_db.__exit__ = Mock(side_effect=Exception("Database error"))
        mock_db_context.return_value = mock_db

        with patch("app.workers.tasks.text"):
            mock_session.execute.side_effect = Exception("SQL error")

            result = cleanup_old_prices_task(days_to_keep=30)

            assert result["task"] == "cleanup_old_prices"
            assert result["status"] == "error"
            assert "database error" in result.get("error", "").lower()

    @pytest.mark.asyncio
    @patch("app.workers.tasks.DeribitClient")
    async def test_fetch_prices_async_empty_response(self, mock_client_class):
        """Тест пустого ответа от API"""

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get_multiple_index_prices.return_value = {}

        mock_client_class.return_value = mock_client

        result = await _fetch_prices_async()

        assert result == {}
        mock_client.get_multiple_index_prices.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.workers.tasks.DeribitClient")
    async def test_fetch_prices_async_with_retry_logic(self, mock_client_class):
        """Тест логики повторных попыток"""

        call_count = 0

        async def mock_get_prices(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise DeribitConnectionError(f"Attempt {call_count}")

            return {
                "btc_usd": {"index_price": 95194.62},
                "eth_usd": {"index_price": 3342.62},
            }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get_multiple_index_prices = AsyncMock(side_effect=mock_get_prices)

        mock_client_class.return_value = mock_client

        result = await _fetch_prices_async()

        assert call_count == 3
        assert "btc_usd" in result
        assert "eth_usd" in result

    @patch("app.workers.tasks.PriceService")
    @patch("app.workers.tasks.get_db_context")
    def test_save_prices_to_db_with_duplicates(
        self, mock_db_context, mock_price_service
    ):
        """Тест сохранения дублирующихся цен"""

        mock_session = Mock()
        mock_db = Mock()
        mock_db.__enter__ = Mock(return_value=mock_session)
        mock_db.__exit__ = Mock(return_value=None)
        mock_db_context.return_value = mock_db

        mock_price_service.create_price.side_effect = [
            Mock(id=1),
            Exception("UNIQUE constraint failed"),
        ]

        prices_data = {
            "btc_usd": {
                "index_price": 95194.62,
                "timestamp": 1705593600000,
                "source_data": {},
            },
            "eth_usd": {
                "index_price": 95194.62,
                "timestamp": 1705593600000,
                "source_data": {},
            },
        }

        saved_count = _save_prices_to_db(prices_data)

        assert saved_count == 1
        assert mock_price_service.create_price.call_count == 2

    @patch("app.workers.tasks.get_db_context")
    def test_check_database_health_detailed(self, mock_db_context):
        """Тест детальной проверки базы данных"""

        mock_session = Mock()
        mock_db_context.return_value.__enter__.return_value = mock_session

        mock_session.execute.return_value = None

        result = _check_database_health()
        assert result is True
        mock_session.execute.assert_called_once()

        mock_session.execute.side_effect = Exception("DB Error")
        result_error = _check_database_health()
        assert result_error is False

    @patch("app.workers.tasks.redis.Redis")
    @patch("app.workers.tasks.settings")
    def test_check_redis_health_detailed(self, mock_settings, mock_redis_class):
        """Тест детальной проверки Redis"""

        mock_settings.redis_url = "redis://localhost:6379"

        mock_redis = Mock()
        mock_redis_class.from_url.return_value = mock_redis
        mock_redis.ping.return_value = True

        result = _check_redis_health()

        assert result is True
        mock_redis_class.from_url.assert_called_once()

    @patch("app.workers.tasks.run_async")
    def test_fetch_prices_task_custom_tickers(self, mock_run_async):
        """Тест получения цен для кастомного списка тикеров"""

        mock_run_async.return_value = {
            "btc_usd": {"index_price": 95194.62, "timestamp": 1705593600000},
            "eth_usd": {"index_price": 3342.62, "timestamp": 1705593600000},
        }

        with patch("app.workers.tasks._fetch_prices_async") as mock_fetch:
            with patch("app.workers.tasks._save_prices_to_db", return_value=2):
                result = fetch_prices_task()

                assert result["prices_fetched"] == 2

                mock_run_async.assert_called_once()

                mock_fetch.assert_called_once()

    def test_task_error_handling_comprehensive(self):
        """Тест всесторонней обработки ошибок"""

        assert hasattr(fetch_prices_task, "__wrapped__")
        assert hasattr(health_check_task, "__wrapped__")
        assert hasattr(cleanup_old_prices_task, "__wrapped__")
