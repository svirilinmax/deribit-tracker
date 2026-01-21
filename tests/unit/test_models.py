import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.db.models import Price


class TestPriceModel:
    """Тесты модели Price"""

    def test_create_price(self, db_session, sample_price_data):
        """Тест создания записи о цене"""

        price = Price(**sample_price_data)
        db_session.add(price)
        db_session.commit()
        db_session.refresh(price)

        assert price.id is not None
        assert price.ticker == "btc_usd"
        assert float(price.price) == 50000.50
        assert price.timestamp == 1705593600000
        assert price.source_timestamp == 1705593600000000
        assert isinstance(price.created_at, datetime)

    def test_price_required_fields(self, db_session):
        """Тест обязательных полей"""

        price = Price()
        db_session.add(price)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_price_string_representation(self, db_session, sample_price_data):
        """Тест строкового представления"""

        price = Price(**sample_price_data)
        db_session.add(price)
        db_session.commit()

        expected = f"<Price(ticker=btc_usd, price=50000.50000000, timestamp=1705593600000)>"
        assert str(price) == expected

    def test_price_decimal_precision(self, db_session):
        """Тест точности десятичных чисел"""

        price = Price(
            ticker="btc_usd",
            price=12345.67890123,
            timestamp=1705593600000,
            source_timestamp=1705593600000000
        )
        db_session.add(price)
        db_session.commit()
        db_session.refresh(price)


        assert abs(float(price.price) - 12345.67890123) < 0.00000001

    def test_price_indexing(self, db_session, sample_price_data):
        """Тест поиска по индексам"""

        for i in range(3):
            price_data = sample_price_data.copy()
            price_data["timestamp"] += i * 60000
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        prices = db_session.query(Price).filter(
            Price.ticker == "btc_usd",
            Price.timestamp >= sample_price_data["timestamp"],
            Price.timestamp <= sample_price_data["timestamp"] + 120000
        ).all()

        assert len(prices) == 3
