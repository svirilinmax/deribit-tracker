from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp import ClientError

from app.clients.deribit import DeribitClient
from app.clients.exceptions import DeribitAPIError, DeribitConnectionError


class TestDeribitClientFixed:
    """Исправленные тесты клиента Deribit"""

    def test_client_initialization(self):
        """Тест инициализации клиента"""

        client = DeribitClient()
        assert hasattr(client, "base_url")
        assert hasattr(client, "timeout")
        assert client.timeout == 30

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Тест контекстного менеджера"""

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.close = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session

            async with DeribitClient() as client:
                assert hasattr(client, "base_url")

    @pytest.mark.asyncio
    async def test_get_index_price_success(self):
        client = DeribitClient()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"index_price": 50000.50},
        }

        mock_post_context = AsyncMock()
        mock_post_context.__aenter__.return_value = mock_response

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_context
        mock_session.close = AsyncMock()

        with patch.object(client, "_create_session", return_value=mock_session):
            async with client:
                result = await client.get_index_price("btc_usd")

                assert result["index_price"] == 50000.50
                mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_index_price_api_error(self):
        """Тест обработки ошибки API (код 200, но в теле ответа 'error')"""

        client = DeribitClient()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"message": "Invalid request", "code": -32600},
            }
        )

        mock_post_context = AsyncMock()
        mock_post_context.__aenter__.return_value = mock_response

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_context
        mock_session.close = AsyncMock()

        with patch.object(client, "_create_session", return_value=mock_session):
            async with client:
                with pytest.raises(DeribitAPIError) as exc_info:
                    await client.get_index_price("btc_usd")

                # 5. Проверяем детали ошибки
                assert "Invalid request" in str(exc_info.value)
                assert exc_info.value.code == -32600

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_index_price_http_error(self):
        """Тест обработки HTTP ошибки (например, 500 Server Error)"""

        client = DeribitClient(max_retries=0)

        mock_response = AsyncMock()
        mock_response.status = 500

        mock_post_context = AsyncMock()
        mock_post_context.__aenter__.return_value = mock_response

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_context
        mock_session.close = AsyncMock()

        with patch.object(client, "_create_session", return_value=mock_session):
            async with client:
                with pytest.raises(DeribitAPIError) as exc_info:
                    await client.get_index_price("btc_usd")

                assert "500" in str(exc_info.value)
                assert exc_info.value.code == 500

        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_index_price_connection_error(self):
        """Тест ошибки соединения"""

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(side_effect=ClientError("Connection failed"))

        client = DeribitClient()

        with patch.object(client, "_create_session") as mock_create:
            mock_create.return_value.__aenter__.return_value = mock_session
            with pytest.raises(DeribitConnectionError):
                await client.get_index_price("btc_usd")

    @pytest.mark.asyncio
    async def test_get_multiple_index_prices(self):
        """Тест получения нескольких цен"""

        with patch.object(DeribitClient, "get_index_price") as mock_get:
            mock_get.side_effect = [{"index_price": 50000.50}, {"index_price": 3500.75}]

            client = DeribitClient()
            results = await client.get_multiple_index_prices(["btc_usd", "eth_usd"])

            assert "btc_usd" in results
            assert "eth_usd" in results
            assert results["btc_usd"]["index_price"] == 50000.50
            assert results["eth_usd"]["index_price"] == 3500.75

    @pytest.mark.asyncio
    async def test_get_multiple_index_prices_with_error(self):
        """Тест получения нескольких цен с ошибкой"""

        with patch.object(DeribitClient, "get_index_price") as mock_get:
            mock_get.side_effect = [
                {"index_price": 50000.50},
                DeribitAPIError("API Error", code=-1),
            ]

            client = DeribitClient()
            results = await client.get_multiple_index_prices(["btc_usd", "eth_usd"])

            assert "btc_usd" in results
            assert "error" in results["eth_usd"]
            assert results["btc_usd"]["index_price"] == 50000.50

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Тест проверки здоровья - успех"""

        client = DeribitClient()

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"version": "1.0.0"},
        }

        mock_post_context = AsyncMock()
        mock_post_context.__aenter__.return_value = mock_response

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_context
        mock_session.close = AsyncMock()

        with patch.object(client, "_create_session", return_value=mock_session):
            async with client:
                is_healthy = await client.health_check()
                assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Тест проверки здоровья - неудача"""

        mock_session = AsyncMock()
        mock_session.post = AsyncMock(side_effect=ClientError("Connection failed"))

        client = DeribitClient()

        with patch.object(client, "_create_session") as mock_create:
            mock_create.return_value.__aenter__.return_value = mock_session
            is_healthy = await client.health_check()
            assert is_healthy is False

    @pytest.mark.asyncio
    async def test_backoff_retry_logic(self):
        """Тест логики повторных попыток"""

        call_count = {"count": 0}

        def mock_post_logic(*args, **kwargs):
            call_count["count"] += 1

            mock_context = AsyncMock()

            if call_count["count"] < 3:
                mock_context.__aenter__.side_effect = aiohttp.ClientError(
                    f"Connection failed {call_count['count']}"
                )
            else:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(
                    return_value={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "result": {"index_price": 50000.50},
                    }
                )
                mock_context.__aenter__.return_value = mock_response
            return mock_context

        mock_session = MagicMock()
        mock_session.post.side_effect = mock_post_logic
        mock_session.close = AsyncMock()

        client = DeribitClient(max_retries=3)

        with patch.object(client, "_create_session", return_value=mock_session):
            with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
                async with client:
                    result = await client.get_index_price("btc_usd")

                    assert call_count["count"] == 3
                    assert result["index_price"] == 50000.50
                    assert mock_sleep.call_count == 2
