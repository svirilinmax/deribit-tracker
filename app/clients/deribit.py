import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from app.core.config import settings

from .exceptions import DeribitAPIError, DeribitConnectionError

logger = logging.getLogger(__name__)


class DeribitClient:
    """Асинхронный клиент для Deribit API"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.base_url = base_url or settings.DERIBIT_BASE_URL
        self.timeout = timeout or settings.DERIBIT_API_TIMEOUT
        self.max_retries = max_retries or settings.API_MAX_RETRIES
        self.session: Optional[ClientSession] = None
        self._request_id = 0

    def _create_session(self) -> ClientSession:
        """Фабричный метод для создания сессии"""
        timeout = ClientTimeout(total=self.timeout)
        return ClientSession(timeout=timeout)

    async def __aenter__(self):
        if not self.session:
            self.session = self._create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    def _get_next_request_id(self) -> int:
        """Генерация уникального ID для запроса"""

        self._request_id += 1
        return self._request_id

    def _build_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Построение JSON-RPC запроса"""

        return {
            "jsonrpc": "2.0",
            "id": self._get_next_request_id(),
            "method": method,
            "params": params,
        }

    async def _make_request(
        self, method: str, params: Dict[str, Any], retry_count: int = 0
    ) -> Dict[str, Any]:
        if not self.session:
            raise DeribitConnectionError(
                "Сессия не инициализирована. Используйте контекстный менеджер."
            )

        request_data = self._build_request(method, params)

        try:
            logger.debug(
                "Выполняем запрос к Deribit API",
                extra={"method": method, "params": params, "attempt": retry_count + 1},
            )

            async with self.session.post(self.base_url, json=request_data) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 1))
                    if retry_count < self.max_retries:
                        logger.warning(
                            f"Rate limit (429). Повтор через {retry_after}с."
                        )
                        await asyncio.sleep(retry_after)
                        return await self._make_request(method, params, retry_count + 1)
                    else:
                        raise DeribitAPIError("Превышен лимит запросов (429)", 429)

                if response.status != 200:
                    error_msg = f"HTTP ошибка: {response.status}"
                    logger.error(error_msg)
                    raise DeribitAPIError(error_msg, response.status)

                data = await response.json()

                if "error" in data:
                    error_data = data["error"]
                    error_code = error_data.get("code", 0)
                    error_message = error_data.get("message", "Unknown error")
                    raise DeribitAPIError(error_message, error_code)

                return data.get("result", {})

        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            error_type = (
                "Таймаут" if isinstance(e, asyncio.TimeoutError) else "Сетевая ошибка"
            )
            logger.error(f"{error_type} при запросе к Deribit: {str(e)}")

            if retry_count < self.max_retries:
                wait_time = settings.API_RETRY_DELAY * (
                    settings.API_RETRY_BACKOFF**retry_count
                )
                logger.info(f"Повторная попытка через {wait_time} секунд...")
                await asyncio.sleep(wait_time)
                return await self._make_request(method, params, retry_count + 1)
            else:
                raise DeribitConnectionError(
                    f"Превышено количество попыток после {error_type.lower()}: {str(e)}"
                )

    async def get_index_price(self, index_name: str) -> Dict[str, Any]:
        """
        Получить индексную цену для указанного индекса
        """

        valid_indices = ["btc_usd", "eth_usd"]
        if index_name not in valid_indices:
            raise ValueError(
                f"Недопустимый индекс. Допустимые значения: {valid_indices}"
            )

        params = {"index_name": index_name}
        return await self._make_request("public/get_index_price", params)

    async def get_multiple_index_prices(
        self, indices: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Получить цены для нескольких индексов
        """
        results = {}

        for index_name in indices:
            try:
                price_data = await self.get_index_price(index_name)
                results[index_name] = price_data
            except Exception as e:
                logger.error(f"Ошибка при получении цены для {index_name}: {str(e)}")
                results[index_name] = {"error": str(e)}

        return results

    async def get_server_time(self) -> Dict[str, Any]:
        """Получить текущее время сервера Deribit"""

        return await self._make_request("public/get_time", {})

    async def health_check(self) -> bool:
        """
        Проверка доступности API
        """
        try:
            await self.get_server_time()
            return True
        except Exception:
            return False


_client: Optional[DeribitClient] = None


async def get_deribit_client() -> DeribitClient:
    """
    Получить экземпляр Deribit клиента (синглтон)
    """
    global _client
    if _client is None:
        _client = DeribitClient()
    return _client
