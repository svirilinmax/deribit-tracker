class DeribitClientError(Exception):
    """Базовое исключение для клиента Deribit"""

    pass


class DeribitAPIError(DeribitClientError):
    """Ошибка API Deribit"""

    def __init__(self, message: str, code: int = 0):
        self.code = code
        super().__init__(f"{message} (код: {code})")


class DeribitConnectionError(DeribitClientError):
    """Ошибка соединения с Deribit"""

    pass


class DeribitRateLimitError(DeribitAPIError):
    """Превышение лимита запросов"""

    pass


class DeribitValidationError(DeribitClientError):
    """Ошибка валидации данных"""

    pass
