from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.workers.tasks import (
    _fetch_prices_async,
    _save_prices_to_db,
    cleanup_old_prices_task,
    fetch_prices_task,
    health_check_task,
)


class TestCeleryTasks:
    """Тесты Celery задач"""

    @patch("app.workers.tasks.run_async")
    @patch("app.workers.tasks._save_prices_to_db")
    def test_fetch_prices_task_success(self, mock_save, mock_run_async):
        """Тест успешного выполнения задачи получения цен"""

        mock_run_async.return_value = {
            "btc_usd": {"index_price": 95194.62, "timestamp": 1705593600000},
            "eth_usd": {"index_price": 3342.62, "timestamp": 1705593600000},
        }
        mock_save.return_value = 2

        result = fetch_prices_task()

        assert result["status"] == "success"
        assert result["prices_fetched"] == 2
        assert result["prices_saved"] == 2
        assert "btc_usd" in result["details"]
        assert "eth_usd" in result["details"]

        mock_run_async.assert_called_once()
        mock_save.assert_called_once_with(mock_run_async.return_value)

    @patch("app.workers.tasks.run_async")
    def test_fetch_prices_task_no_data(self, mock_run_async):
        """Тест задачи получения цен без данных"""

        mock_run_async.return_value = {}

        result = fetch_prices_task()

        assert result["status"] == "no_data"
        assert result["prices_fetched"] == 0
        assert result["prices_saved"] == 0

    @patch("app.workers.tasks.run_async")
    def test_fetch_prices_task_api_error(self, mock_run_async):
        """Тест задачи получения цен с ошибкой API"""

        from app.clients.exceptions import DeribitAPIError

        mock_run_async.side_effect = DeribitAPIError("API Error", code=-1)

        result = fetch_prices_task()

        assert result["status"] == "api_error"
        assert len(result["errors"]) > 0
        assert "API ошибка" in result["errors"][0]

    @patch("app.workers.tasks.run_async")
    def test_fetch_prices_task_connection_error(self, mock_run_async):
        """Тест задачи получения цен с ошибкой соединения"""

        from app.clients.exceptions import DeribitConnectionError

        mock_run_async.side_effect = DeribitConnectionError("Connection failed")

        result = fetch_prices_task()

        assert result["status"] == "connection_error"
        assert len(result["errors"]) > 0
        assert "Ошибка соединения" in result["errors"][0]

    @patch("app.workers.tasks._check_database_health")
    @patch("app.workers.tasks._check_redis_health")
    @patch("app.workers.tasks.run_async")
    def test_health_check_task_success(
        self, mock_run_async, mock_redis_health, mock_db_health
    ):
        """Тест задачи проверки здоровья - успех"""

        mock_run_async.return_value = True
        mock_db_health.return_value = True
        mock_redis_health.return_value = True

        result = health_check_task()

        assert result["status"] == "healthy"
        assert result["checks"]["deribit_api"]["available"] is True
        assert result["checks"]["database"]["available"] is True
        assert result["checks"]["redis"]["available"] is True

    @patch("app.workers.tasks._check_database_health")
    @patch("app.workers.tasks._check_redis_health")
    @patch("app.workers.tasks.run_async")
    def test_health_check_task_partial_failure(
        self, mock_run_async, mock_redis_health, mock_db_health
    ):
        """Тест задачи проверки здоровья - частичный сбой"""

        mock_run_async.return_value = False
        mock_db_health.return_value = True
        mock_redis_health.return_value = True

        result = health_check_task()

        assert result["status"] == "unhealthy"
        assert result["checks"]["deribit_api"]["available"] is False
        assert result["checks"]["database"]["available"] is True

    @patch("app.workers.tasks.run_async")
    @patch("app.workers.tasks._save_prices_to_db")
    def test_cleanup_old_prices_task(self, mock_save, mock_run_async):
        """Тест задачи очистки старых цен"""

        mock_session = Mock()

        mock_db = Mock()
        mock_db.__enter__ = Mock(return_value=mock_session)
        mock_db.__exit__ = Mock(return_value=None)

        with patch("app.workers.tasks.get_db_context", return_value=mock_db):
            mock_result = Mock()
            mock_result.rowcount = 5
            mock_session.execute.return_value = mock_result

            result = cleanup_old_prices_task(days_to_keep=30)

            assert result["task"] == "cleanup_old_prices"
            assert result["days_to_keep"] == 30
            assert result["deleted_count"] == 5

    @pytest.mark.asyncio
    @patch("app.workers.tasks.DeribitClient")
    async def test_fetch_prices_async_success(self, mock_client_class):
        """Тест асинхронного получения цен"""

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        mock_client.get_multiple_index_prices.return_value = {
            "btc_usd": {"index_price": 95194.62},
            "eth_usd": {"index_price": 3342.62},
        }

        mock_client_class.return_value = mock_client

        result = await _fetch_prices_async()

        assert "btc_usd" in result
        assert "eth_usd" in result
        assert "index_price" in result["btc_usd"]
        assert "timestamp" in result["btc_usd"]
        assert "source_data" in result["btc_usd"]

        mock_client.get_multiple_index_prices.assert_called_once_with(
            ["btc_usd", "eth_usd"]
        )

    @patch("app.workers.tasks.PriceService")
    @patch("app.workers.tasks.get_db_context")
    def test_save_prices_to_db(self, mock_db_context, mock_price_service):
        """Тест сохранения цен в базу данных"""

        mock_session = Mock()
        mock_db = Mock()
        mock_db.__enter__ = Mock(return_value=mock_session)
        mock_db.__exit__ = Mock(return_value=None)
        mock_db_context.return_value = mock_db

        mock_created_price = Mock()
        mock_created_price.id = 1
        mock_price_service.create_price.return_value = mock_created_price

        prices_data = {
            "btc_usd": {
                "index_price": 95194.62,
                "timestamp": 1705593600000,
                "source_data": {},
            },
            "eth_usd": {
                "index_price": 3342.62,
                "timestamp": 1705593600000,
                "source_data": {},
            },
        }

        saved_count = _save_prices_to_db(prices_data)

        assert saved_count == 2
        assert mock_price_service.create_price.call_count == 2

        first_call = mock_price_service.create_price.call_args_list[0]
        price_create = first_call[0][1]  # второй аргумент

        assert price_create.ticker in ["btc_usd", "eth_usd"]
        assert price_create.price in [95194.62, 3342.62]
