from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging


def create_application() -> FastAPI:
    """Создание и настройка FastAPI приложения"""

    # Настраиваем логирование
    setup_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        description="API для мониторинга цен с биржи Deribit",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/v1")

    @app.get("/")
    async def root():
        """Корневой эндпоинт"""

        return {
            "message": "Deribit Tracker API",
            "version": "1.0.0",
            "environment": settings.APP_ENV,
        }

    @app.get("/health")
    async def health_check():
        """Health check эндпоинт"""

        return {"status": "healthy", "service": settings.APP_NAME}

    return app


app = create_application()
