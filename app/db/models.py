from sqlalchemy import Column, Integer, String, Numeric, BigInteger, DateTime, Index
from sqlalchemy.sql import func
from .database import Base


class Price(Base):
    """Модель для хранения цен криптовалют"""

    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    price = Column(Numeric(20, 8), nullable=False)
    timestamp = Column(BigInteger, nullable=False)
    source_timestamp = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Индекс для быстрого поиска по тикеру и времени
    __table_args__ = (
        Index('idx_ticker_timestamp', ticker, timestamp.desc()),
        Index('idx_created_at', created_at.desc()),
    )

    def __repr__(self):
        return f"<Price(ticker={self.ticker}, price={self.price}, timestamp={self.timestamp})>"

    def to_dict(self):
        """Конвертировать модель в словарь"""

        return {
            "id": self.id,
            "ticker": self.ticker,
            "price": float(self.price),
            "timestamp": self.timestamp,
            "source_timestamp": self.source_timestamp,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
