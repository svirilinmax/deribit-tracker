from pydantic import BaseModel, Field
from typing import Optional, List


class DeribitIndexPrice(BaseModel):
    """Схема для ответа public/get_index_price"""

    index_price: float = Field(..., description="Текущая индексная цена")
    estimated_delivery_price: Optional[float] = Field(
        None, description="Расчетная цена поставки"
    )

    class Config:
        from_attributes = True


class DeribitServerTime(BaseModel):
    """Схема для ответа public/get_time"""

    milliseconds: Optional[int] = Field(None, description="Время в миллисекундах")

    class Config:
        from_attributes = True


class DeribitResponse(BaseModel):
    """Базовая схема для ответов Deribit API"""

    jsonrpc: str = Field("2.0", description="Версия JSON-RPC")
    id: int = Field(..., description="ID запроса")
    result: dict = Field(..., description="Результат запроса")
    testnet: bool = Field(..., description="Флаг тестовой среды")
    usIn: int = Field(..., description="Время получения запроса (микросекунды)")
    usOut: int = Field(..., description="Время отправки ответа (микросекунды)")
    usDiff: int = Field(..., description="Время обработки (микросекунды)")

    class Config:
        from_attributes = True
