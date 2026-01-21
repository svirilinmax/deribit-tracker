from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения"""

    APP_NAME: str = "Deribit Tracker"
    APP_ENV: str = "development"
    DEBUG: bool = False

    # База данных
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "deribit_tracker"
    POSTGRES_USER: str = "deribit_user"
    POSTGRES_PASSWORD: str = "deribit_password"

    @property
    def database_url(self) -> str:
        """Получить URL для подключения к БД"""

        return (
            f"postgresql://{self.POSTGRES_USER}:"  # noqa E231
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"  # noqa E231
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        """Получить URL для подключения к Redis"""

        return (
            f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"  # noqa E231
        )

    DERIBIT_BASE_URL: str = "https://test.deribit.com/api/v2"
    DERIBIT_API_TIMEOUT: int = 30

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = "logs/app.log"

    API_MAX_RETRIES: int = 3
    API_RETRY_DELAY: int = 1
    API_RETRY_BACKOFF: int = 2

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
