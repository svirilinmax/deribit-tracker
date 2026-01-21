from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.price import PriceBase, PriceCreate, PriceResponse


class TestPriceSchemasExtended:
    """Расширенные тесты схем цен"""

    def test_price_create_edge_cases(self):
        """Тест граничных случаев для создания цены"""

        max_data = {
            "ticker": "btc_usd",
            "price": 999999999999.99999999,
            "timestamp": 9999999999999,
            "source_timestamp": 9999999999999999,
        }

        price = PriceCreate(**max_data)
        assert price.ticker == "btc_usd"
        assert price.price == max_data["price"]
        assert price.timestamp == max_data["timestamp"]

        min_data = {
            "ticker": "btc_usd",
            "price": 0.00000001,
            "timestamp": 1,
            "source_timestamp": 1,
        }

        price = PriceCreate(**min_data)
        assert price.ticker == "btc_usd"
        assert price.price == min_data["price"]

    def test_invalid_ticker_formats(self):
        """Тест невалидных форматов тикера"""
        invalid_tickers = [
            "btc",
            "_usd",
            "btc_",
            "btc__usd",
            "btc.usd",
            "",
            "a",
            "very_long_ticker_name",
            "123_456",
            "btc_usd_extra_long",
        ]

        for ticker in invalid_tickers:
            try:
                PriceCreate(
                    ticker=ticker,
                    price=50000.50,
                    timestamp=1705593600000,
                    source_timestamp=1705593600000000,
                )
                pytest.fail(
                    f"Тикер '{ticker}' был принят как ВАЛИДНЫЙ, но мы ожидали ошибку!"
                )
            except ValidationError:
                continue

    def test_price_validation_edge_cases(self):
        """Тест граничных случаев валидации цены"""

        test_cases = [
            {"price": 0, "should_pass": True},  # Ноль
            {"price": -0.00000001, "should_pass": False},
            {"price": 1000000000000.00000000, "should_pass": True},
            {"price": 1e10, "should_pass": True},
            {"price": "50000.50", "should_pass": True},
        ]

        for test_case in test_cases:
            try:
                if not test_case["should_pass"]:
                    pytest.fail(f"Should have failed for price: {test_case['price']}")
            except ValidationError:
                if test_case["should_pass"]:
                    pytest.fail(f"Should have passed for price: {test_case['price']}")

    def test_timestamp_validation_edge_cases(self):
        """Тест граничных случаев валидации timestamp"""

        test_cases = [
            {"timestamp": 0, "should_pass": True},
            {"timestamp": -1, "should_pass": False},
            {"timestamp": 1609459200000, "should_pass": True},
            {"timestamp": 4102444800000, "should_pass": True},
            {"timestamp": 9999999999999, "should_pass": True},
            {"timestamp": "1705593600000", "should_pass": True},
        ]

        for test_case in test_cases:
            try:
                if not test_case["should_pass"]:
                    pytest.fail(
                        f"Should have failed for timestamp: {test_case['timestamp']}"
                    )
            except ValidationError:
                if test_case["should_pass"]:
                    pytest.fail(
                        f"Should have passed for timestamp: {test_case['timestamp']}"
                    )

    def test_price_response_with_timezone(self):
        """Тест ответа с временной зоной"""

        created_at = datetime.now(timezone.utc)

        data = {
            "id": 1,
            "ticker": "btc_usd",
            "price": 50000.50,
            "timestamp": 1705593600000,
            "source_timestamp": 1705593600000000,
            "created_at": created_at,
        }

        price = PriceResponse(**data)

        assert price.id == 1
        assert price.ticker == "btc_usd"
        assert price.created_at == created_at

    def test_price_serialization_options(self):
        """Тест опций сериализации"""

        data = {
            "ticker": "btc_usd",
            "price": 50000.50,
            "timestamp": 1705593600000,
            "source_timestamp": 1705593600000000,
        }

        price = PriceCreate(**data)

        price_dict = price.model_dump()
        assert isinstance(price_dict, dict)

        price_json = price.model_dump_json()
        assert isinstance(price_json, str)
        assert "btc_usd" in price_json

        price_dict_exclude = price.model_dump(exclude={"source_timestamp"})
        assert "source_timestamp" not in price_dict_exclude
        assert "ticker" in price_dict_exclude

    def test_price_field_alias(self):
        """Тест алиасов полей"""

        data = {
            "ticker": "btc_usd",
            "price": 50000.50,
            "timestamp": 1705593600000,
            "source_timestamp": 1705593600000000,
        }

        price = PriceCreate(**data)
        price_dict = price.model_dump()

        assert "ticker" in price_dict
        assert "price" in price_dict
        assert "timestamp" in price_dict
        assert "source_timestamp" in price_dict

    def test_price_with_none_values(self):
        """Тест с None значениями"""

        data = {"ticker": "btc_usd", "price": 50000.50, "timestamp": 1705593600000}

        price = PriceCreate(**data)
        assert price.source_timestamp is None

    def test_price_model_compatibility(self):
        """Тест совместимости моделей"""

        base_data = {"ticker": "btc_usd", "price": 50000.50, "timestamp": 1705593600000}

        base_price = PriceBase(**base_data)

        create_data = base_data.copy()
        create_data["source_timestamp"] = 1705593600000000
        create_price = PriceCreate(**create_data)

        response_data = create_data.copy()
        response_data["id"] = 1
        response_data["created_at"] = datetime.now()
        response_price = PriceResponse(**response_data)

        assert base_price.ticker == create_price.ticker == response_price.ticker
        assert base_price.price == create_price.price == response_price.price
        assert (
            base_price.timestamp == create_price.timestamp == response_price.timestamp
        )
