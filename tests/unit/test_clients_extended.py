import aiohttp
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.clients.deribit import DeribitClient
from app.clients.exceptions import DeribitAPIError, DeribitConnectionError


class TestDeribitClientExtended:
    """Расширенные тесты клиента Deribit"""

    @pytest.mark.asyncio
    async def test_get_index_price_with_different_currencies(self):
        """Тест получения цены для поддерживаемых валютных пар"""

        test_cases = [
            ("btc_usd", "btc_usd"),
            ("eth_usd", "eth_usd"),
        ]

        client = DeribitClient()
        mock_response = AsyncMock()

        mock_response.status = 200
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"index_price": 50000.50}
        }

        mock_post_context = AsyncMock()
        mock_post_context.__aenter__.return_value = mock_response

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_context
        mock_session.close = AsyncMock()

        with patch.object(client, '_create_session', return_value=mock_session):
            async with client:
                for currency, expected_param in test_cases:
                    result = await client.get_index_price(currency)

                    assert result["index_price"] == 50000.50
                    mock_session.post.assert_called()

                    call_args = mock_session.post.call_args
                    request_body = call_args.kwargs['json']
                    assert request_body['params']['index_name'] == expected_param

    @pytest.mark.asyncio
    async def test_get_index_price_rate_limit(self):
        """Тест обработки rate limiting (429)"""

        client = DeribitClient(max_retries=3)

        def mock_post_logic(*args, **kwargs):
            mock_context = AsyncMock()
            call_idx = mock_session.post.call_count

            if call_idx == 1:
                # Первый вызов - 429
                resp = AsyncMock()
                resp.status = 429
                resp.headers = {"Retry-After": "1"}
                mock_context.__aenter__.return_value = resp
            else:
                resp = AsyncMock()
                resp.status = 200
                resp.json.return_value = {"jsonrpc": "2.0", "result": {"index_price": 50000.50}}
                mock_context.__aenter__.return_value = resp
            return mock_context

        mock_session = MagicMock()
        mock_session.post.side_effect = mock_post_logic
        mock_session.close = AsyncMock()

        with patch.object(client, '_create_session', return_value=mock_session):
            with patch('asyncio.sleep', AsyncMock()) as mock_sleep:
                async with client:
                    result = await client.get_index_price("btc_usd")

                    assert mock_session.post.call_count == 2
                    mock_sleep.assert_any_call(1)
                    assert result["index_price"] == 50000.50

    @pytest.mark.asyncio
    async def test_get_index_price_timeout(self):
        """Тест таймаута запроса с повторными попытками"""
        client = DeribitClient(max_retries=2)

        mock_session = MagicMock()

        mock_post_context = AsyncMock()
        mock_post_context.__aenter__.side_effect = asyncio.TimeoutError("Request timeout")

        mock_session.post.return_value = mock_post_context
        mock_session.close = AsyncMock()

        with patch.object(client, '_create_session', return_value=mock_session):
            with patch('asyncio.sleep', AsyncMock()) as mock_sleep:
                async with client:
                    with pytest.raises(DeribitConnectionError) as exc_info:
                        await client.get_index_price("btc_usd")

                    assert "время ожидания" in str(exc_info.value).lower() or "timeout" in str(exc_info.value).lower()
                    assert mock_session.post.call_count == 3
                    assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_get_index_price_network_errors(self):
        """Тест различных сетевых ошибок с логикой повторов"""

        network_errors = [
            aiohttp.ClientError("Connection refused"),
            ConnectionResetError("Connection reset by peer"),
            OSError("Network is unreachable"),
        ]

        for error in network_errors:
            mock_session = MagicMock()
            mock_post_context = AsyncMock()
            mock_post_context.__aenter__.side_effect = error

            mock_session.post.return_value = mock_post_context
            mock_session.close = AsyncMock()

            client = DeribitClient(max_retries=1)

            with patch.object(client, '_create_session', return_value=mock_session):
                with patch('asyncio.sleep', AsyncMock()):
                    async with client:
                        with pytest.raises(DeribitConnectionError):
                            await client.get_index_price("btc_usd")
            assert mock_session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_get_index_price_invalid_json_response(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_post_context = AsyncMock()
        mock_post_context.__aenter__.return_value = mock_response

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_context
        mock_session.close = AsyncMock()

        client = DeribitClient(max_retries=0)

        with patch.object(client, '_create_session', return_value=mock_session):
            async with client:
                with pytest.raises(Exception) as exc_info:
                    await client.get_index_price("btc_usd")

                assert "json" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_index_price_missing_fields(self):
        """Тест ответа с отсутствующими полями"""

        test_cases = [
            {"jsonrpc": "2.0", "id": 1},
            {"jsonrpc": "2.0", "id": 1, "result": {}},
            {"jsonrpc": "2.0", "id": 1, "result": {"wrong_field": 50000.50}},
        ]

        for response_data in test_cases:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = response_data

            mock_post_context = AsyncMock()
            mock_post_context.__aenter__.return_value = mock_response

            mock_session = MagicMock()
            mock_session.post.return_value = mock_post_context
            mock_session.close = AsyncMock()

            client = DeribitClient(max_retries=0)

            with patch.object(client, '_create_session', return_value=mock_session):
                async with client:
                    result = await client.get_index_price("btc_usd")
                    assert "index_price" not in result

    @pytest.mark.asyncio
    async def test_health_check_detailed(self):
        """Тест детальной проверки здоровья"""

        test_cases = [
            {
                "name": "success",
                "response": {"jsonrpc": "2.0", "id": 1, "result": {"version": "1.0.0"}},
                "expected": True, "error": None
            },
            {
                "name": "api_error",
                "response": {"jsonrpc": "2.0", "id": 1, "error": {"message": "Maint"}},
                "expected": False, "error": None
            },
            {
                "name": "timeout",
                "response": None, "expected": False, "error": asyncio.TimeoutError()
            }
        ]

        for case in test_cases:
            mock_session = MagicMock()
            mock_session.close = AsyncMock()

            mock_post_context = AsyncMock()

            if case["error"]:
                mock_post_context.__aenter__.side_effect = case["error"]
            else:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = case["response"]
                mock_post_context.__aenter__.return_value = mock_response

            mock_session.post.return_value = mock_post_context

            client = DeribitClient(max_retries=0)

            with patch.object(client, '_create_session', return_value=mock_session):
                client.session = mock_session

                result = await client.health_check()
                assert result == case["expected"], f"Failed on case: {case['name']}"

    @pytest.mark.asyncio
    async def test_backoff_with_exponential_delay(self):
        """Тест экспоненциальной задержки при повторных попытках"""

        call_count = {"count": 0}

        def mock_post_logic(*args, **kwargs):
            call_count["count"] += 1
            mock_context = AsyncMock()
            if call_count["count"] < 4:
                mock_context.__aenter__.side_effect = aiohttp.ClientError(f"Fail {call_count['count']}")
            else:
                resp = AsyncMock()
                resp.status = 200
                resp.json.return_value = {"jsonrpc": "2.0", "result": {"index_price": 50000.5}}
                mock_context.__aenter__.return_value = resp
            return mock_context

        mock_session = MagicMock()
        mock_session.post.side_effect = mock_post_logic
        mock_session.close = AsyncMock()

        client = DeribitClient(max_retries=5)

        with patch.object(client, '_create_session', return_value=mock_session):
            with patch('asyncio.sleep', AsyncMock()) as mock_sleep:
                async with client:
                    await client.get_index_price("btc_usd")

                    assert mock_sleep.call_count == 3
                    # Извлекаем задержки из вызовов sleep
                    delays = [call.args[0] for call in mock_sleep.call_args_list]
                    for i in range(1, len(delays)):
                        assert delays[i] > delays[i - 1]

    def test_client_configuration(self):
        """Тест конфигурации клиента"""

        with patch('app.clients.deribit.settings') as mock_settings:
            mock_settings.DERIBIT_BASE_URL = "https://custom.deribit.com/api/v2"
            mock_settings.DERIBIT_API_TIMEOUT = 60

            client = DeribitClient()

            assert "custom.deribit.com" in client.base_url
            assert client.timeout == 60
