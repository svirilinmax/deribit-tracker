import sys
from unittest.mock import Mock

mock_settings = Mock()
mock_settings.DATABASE_URL = "sqlite:///./test.db"
mock_settings.REDIS_URL = "redis://localhost:6379/0"
mock_settings.CELERY_BROKER_URL = "redis://localhost:6379/0"
mock_settings.CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
mock_settings.DEBUG = False
mock_settings.DERIBIT_BASE_URL = "https://test.deribit.com/api/v2"
mock_settings.DERIBIT_API_TIMEOUT = 30
mock_settings.APP_NAME = "Deribit Tracker Test"
mock_settings.APP_ENV = "test"
mock_settings.LOG_LEVEL = "INFO"
mock_settings.LOG_FILE = None
mock_settings.database_url = "sqlite:///./test.db"
mock_settings.redis_url = "redis://localhost:6379/0"

sys.modules["app.core.config.settings"] = mock_settings
