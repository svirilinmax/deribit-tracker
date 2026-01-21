from typing import Generator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.clients.deribit import get_deribit_client


def get_db_dependency() -> Generator[Session, None, None]:
    """Зависимость для получения сессии БД"""

    return get_db()


async def get_deribit_client_dependency():
    """Зависимость для получения клиента Deribit"""

    return await get_deribit_client()
