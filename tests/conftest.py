import pytest
import asyncio
from typing import Generator, Dict, Any
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import tracemalloc

def pytest_configure(config):
    tracemalloc.start()


TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для асинхронных тестов"""

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Создание тестовой базы данных один раз для всех тестов"""

    with patch('app.core.config.settings') as mock_settings:
        mock_settings.database_url = TEST_DATABASE_URL
        mock_settings.DATABASE_URL = TEST_DATABASE_URL
        mock_settings.DEBUG = False
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_settings.CELERY_BROKER_URL = "redis://localhost:6379/0"
        mock_settings.CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
        mock_settings.DERIBIT_BASE_URL = "https://test.deribit.com/api/v2"
        mock_settings.DERIBIT_API_TIMEOUT = 30
        mock_settings.APP_NAME = "Deribit Tracker Test"
        mock_settings.APP_ENV = "test"
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FILE = None

        from app.db.database import Base
        Base.metadata.create_all(bind=engine)

        yield



@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Сессия базы данных для тестов"""

    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def end_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def test_client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient для тестирования FastAPI"""

    with patch('app.core.config.settings') as mock_settings, \
            patch('app.db.database.SessionLocal', TestingSessionLocal), \
            patch('app.db.session.SessionLocal', TestingSessionLocal), \
            patch('app.db.database.engine', engine):

        mock_settings.database_url = TEST_DATABASE_URL
        mock_settings.DATABASE_URL = TEST_DATABASE_URL
        mock_settings.DEBUG = False
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_settings.CELERY_BROKER_URL = "redis://localhost:6379/0"
        mock_settings.CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
        mock_settings.DERIBIT_BASE_URL = "https://test.deribit.com/api/v2"
        mock_settings.DERIBIT_API_TIMEOUT = 30
        mock_settings.APP_NAME = "Deribit Tracker Test"
        mock_settings.APP_ENV = "test"
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FILE = None

        from app.core.main import create_application
        app = create_application()

        from app.api.v1.deps import get_db as original_get_db

        def override_get_db():
            try:
                yield db_session
            finally:
                try:
                    db_session.commit()
                except:
                    db_session.rollback()
                    raise

        app.dependency_overrides[original_get_db] = override_get_db

        with TestClient(app) as client:
            yield client

        app.dependency_overrides.clear()


@pytest.fixture
def sample_price_data() -> Dict[str, Any]:
    """Фикстура с тестовыми данными цен"""

    return {
        "ticker": "btc_usd",
        "price": 50000.50,
        "timestamp": 1705593600000,
        "source_timestamp": 1705593600000000
    }


@pytest.fixture
def mock_aiohttp_client():
    """Mock для aiohttp.ClientSession"""

    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"index_price": 50000.50}
        })

        mock_session_instance = AsyncMock()
        mock_session_instance.post = AsyncMock(return_value=mock_response)
        mock_session_instance.close = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        yield mock_session


@pytest.fixture
def workers_test_client():
    """Отдельный клиент для workers тестов"""


    with patch('app.core.config.settings') as mock_settings, \
            patch('app.db.database.SessionLocal', TestingSessionLocal), \
            patch('app.db.session.SessionLocal', TestingSessionLocal), \
            patch('app.db.database.engine', engine):

        mock_settings.database_url = TEST_DATABASE_URL
        mock_settings.DATABASE_URL = TEST_DATABASE_URL
        mock_settings.DEBUG = False
        mock_settings.REDIS_URL = "redis://localhost:6379/0"
        mock_settings.CELERY_BROKER_URL = "redis://localhost:6379/0"
        mock_settings.CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
        mock_settings.DERIBIT_BASE_URL = "https://test.deribit.com/api/v2"
        mock_settings.DERIBIT_API_TIMEOUT = 30
        mock_settings.APP_NAME = "Deribit Tracker Test"
        mock_settings.APP_ENV = "test"
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_FILE = None

        from app.core.main import create_application
        app = create_application()

        with TestClient(app) as client:
            yield client
