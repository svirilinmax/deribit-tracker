from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models import Price
from app.schemas.price import PriceCreate, PriceUpdate


class PriceService:
    """Сервис для работы с ценами"""

    @staticmethod
    def create_price(db: Session, price_data: PriceCreate) -> Price:
        """Создать запись о цене"""

        db_price = Price(
            ticker=price_data.ticker,
            price=price_data.price,
            timestamp=price_data.timestamp,
            source_timestamp=price_data.source_timestamp,
        )
        db.add(db_price)
        db.commit()
        db.refresh(db_price)
        return db_price

    @staticmethod
    def get_price(db: Session, price_id: int) -> Optional[Price]:
        """Получить цену по ID"""

        return db.query(Price).filter(Price.id == price_id).first()

    @staticmethod
    def get_prices(
        db: Session, ticker: str, skip: int = 0, limit: int = 100
    ) -> List[Price]:
        """Получить список цен по тикеру"""

        return (
            db.query(Price)
            .filter(Price.ticker == ticker)
            .order_by(desc(Price.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_latest_price(db: Session, ticker: str) -> Optional[Price]:
        """Получить последнюю цену по тикеру"""

        return (
            db.query(Price)
            .filter(Price.ticker == ticker)
            .order_by(desc(Price.timestamp))
            .first()
        )

    @staticmethod
    def get_prices_by_date_range(
        db: Session,
        ticker: str,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
    ) -> List[Price]:
        """Получить цены по тикеру в диапазоне дат"""

        query = db.query(Price).filter(Price.ticker == ticker)

        if start_timestamp:
            query = query.filter(Price.timestamp >= start_timestamp)

        if end_timestamp:
            query = query.filter(Price.timestamp <= end_timestamp)

        return query.order_by(desc(Price.timestamp)).all()

    @staticmethod
    def update_price(
        db: Session, price_id: int, price_data: PriceUpdate
    ) -> Optional[Price]:
        """Обновить запись о цене"""

        db_price = db.query(Price).filter(Price.id == price_id).first()
        if not db_price:
            return None

        update_data = price_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_price, field, value)

        db.commit()
        db.refresh(db_price)
        return db_price

    @staticmethod
    def delete_price(db: Session, price_id: int) -> bool:
        """Удалить запись о цене"""

        db_price = db.query(Price).filter(Price.id == price_id).first()
        if not db_price:
            return False

        db.delete(db_price)
        db.commit()
        return True

    @staticmethod
    def get_stats(db: Session, ticker: str) -> Dict[str, Any]:
        """Получить статистику по ценам для тикера"""

        from sqlalchemy import func

        result = (
            db.query(
                func.count(Price.id).label("count"),
                func.min(Price.price).label("min_price"),
                func.max(Price.price).label("max_price"),
                func.avg(Price.price).label("avg_price"),
                func.min(Price.timestamp).label("first_timestamp"),
                func.max(Price.timestamp).label("last_timestamp"),
            )
            .filter(Price.ticker == ticker)
            .first()
        )

        return {
            "count": result.count if result else 0,
            "min_price": float(result.min_price)
            if result and result.min_price
            else None,
            "max_price": float(result.max_price)
            if result and result.max_price
            else None,
            "avg_price": float(result.avg_price)
            if result and result.avg_price
            else None,
            "first_timestamp": result.first_timestamp if result else None,
            "last_timestamp": result.last_timestamp if result else None,
        }
