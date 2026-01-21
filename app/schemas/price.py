import re
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timezone
from typing import Optional


class PriceBase(BaseModel):
    """Базовая схема для цены"""

    ticker: str = Field(..., description="Тикер (например, BTC-PERPETUAL)", min_length=3)
    price: float = Field(..., description="Цена", ge=0)
    timestamp: int = Field(..., description="UNIX timestamp в миллисекундах", ge=0)
    source_timestamp: Optional[int] = Field(None, description="Timestamp от Deribit")


    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        v = v.lower()
        pattern = r'^(btc|eth)[-_][a-z0-9]{2,15}$'

        if not re.match(pattern, v):
            raise ValueError("Тикер должен начинаться с btc/eth и иметь формат btc_usd или btc-perpetual")
        return v


class PriceCreate(PriceBase):
    """Схема для создания записи о цене"""
    pass


class PriceUpdate(BaseModel):
    """Схема для обновления (используется редко для трекеров цен)"""

    price: Optional[float] = Field(None, ge=0)
    timestamp: Optional[int] = Field(None, ge=0)


class PriceInDB(PriceBase):
    """Схема для данных из БД"""

    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @property
    def dt_object(self) -> datetime:
        """Вспомогательное свойство для получения объекта datetime из миллисекунд"""

        return datetime.fromtimestamp(self.timestamp / 1000.0, tz=timezone.utc)


class PriceResponse(PriceInDB):
    """Схема ответа API"""

    pass

