from fastapi import HTTPException, status


class APIError(HTTPException):
    """Базовое исключение API"""

    def __init__(
        self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(APIError):
    """Ресурс не найден"""

    def __init__(self, detail: str = "Ресурс не найден"):
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class ValidationError(APIError):
    """Ошибка валидации данных"""

    def __init__(self, detail: str = "Ошибка валидации данных"):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class RateLimitError(APIError):
    """Превышен лимит запросов"""

    def __init__(self, detail: str = "Превышен лимит запросов"):
        super().__init__(detail=detail, status_code=status.HTTP_429_TOO_MANY_REQUESTS)
