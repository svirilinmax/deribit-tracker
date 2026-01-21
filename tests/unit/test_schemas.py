from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.price import PriceBase, PriceCreate, PriceResponse


class TestPriceSchemas:
    """Тесты схем цен"""

    def test_price_base_schema(self):
        """Тест базовой схемы"""

        data = {"ticker": "btc_usd", "price": 50000.50, "timestamp": 1705593600000}

        price = PriceBase(**data)
        assert price.ticker == "btc_usd"
        assert price.price == 50000.50
        assert price.timestamp == 1705593600000

    def test_price_create_schema_valid(self, sample_price_data):
        """Тест схемы создания - валидные данные"""

        price = PriceCreate(**sample_price_data)

        assert price.ticker == "btc_usd"
        assert price.price == 50000.50
        assert price.timestamp == 1705593600000
        assert price.source_timestamp == 1705593600000000

    def test_price_create_schema_invalid(self):
        """Тест схемы создания - невалидные данные"""

        with pytest.raises(ValidationError):
            PriceCreate(ticker="invalid", price=50000.50, timestamp=1705593600000)

        with pytest.raises(ValidationError):
            PriceCreate(ticker="btc_usd", price=-100, timestamp=1705593600000)

        with pytest.raises(ValidationError):
            PriceCreate(ticker="btc_usd", price=50000.50, timestamp=-1)

    def test_price_response_schema(self, sample_price_data):
        """Тест схемы ответа"""

        data = sample_price_data.copy()
        data["id"] = 1
        data["created_at"] = datetime.utcnow()

        price = PriceResponse(**data)

        assert price.id == 1
        assert price.ticker == "btc_usd"
        assert price.price == 50000.50
        assert price.timestamp == 1705593600000
        assert isinstance(price.created_at, datetime)

    def test_price_schema_validation_constraints(self):
        """Тест ограничений валидации"""

        def test_price_schema_validation_constraints(self):
            """Тест ограничений валидации"""

            with pytest.raises(ValidationError):
                PriceCreate(ticker="btcusd", price=50000.50, timestamp=1705593600000)

            with pytest.raises(ValidationError):
                PriceCreate(ticker="b_usd", price=50000.50, timestamp=1705593600000)

            with pytest.raises(ValidationError):
                PriceCreate(ticker="btc_usd", price=0, timestamp=1705593600000)

            with pytest.raises(ValidationError):
                PriceCreate(ticker="btc_usd", price=50000.50, timestamp=-1000)

    def test_price_schema_serialization(self):
        """Тест сериализации/десериализации"""

        data = {
            "ticker": "eth_usd",
            "price": 2500.75,
            "timestamp": 1705593600000,
            "source_timestamp": 1705593600000000,
        }

        price_create = PriceCreate(**data)

        price_dict = price_create.model_dump()

        assert price_dict["ticker"] == "eth_usd"
        assert price_dict["price"] == 2500.75
        assert price_dict["timestamp"] == 1705593600000
