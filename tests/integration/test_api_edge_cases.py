import asyncio

import pytest
from httpx import AsyncClient, ASGITransport
from app.core.main import app
from app.api.v1.deps import get_db


class TestPricesEdgeCases:
    """Тесты для граничных случаев API цен"""

    def test_get_prices_with_large_skip(self, test_client, db_session, sample_price_data):
        """Тест получения цен с большим skip"""

        from app.db.models import Price

        for i in range(3):
            price_data = sample_price_data.copy()
            price_data["timestamp"] += i * 60000
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        response = test_client.get("/v1/prices/?ticker=btc_usd&skip=10&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_prices_with_zero_limit(self, test_client):
        """Тест получения цен с limit=0"""
        response = test_client.get("/v1/prices/?ticker=btc_usd&limit=0")

        assert response.status_code == 422

    def test_get_prices_with_negative_skip(self, test_client):
        """Тест получения цен с отрицательным skip"""

        response = test_client.get("/v1/prices/?ticker=btc_usd&skip=-1")

        assert response.status_code == 422

    def test_get_prices_with_large_limit(self, test_client):
        """Тест получения цен с limit больше максимального"""

        response = test_client.get("/v1/prices/?ticker=btc_usd&limit=2000")

        assert response.status_code == 422

    def test_filter_prices_with_only_start(self, test_client, db_session, sample_price_data):
        """Тест фильтрации только с начальной датой"""

        from app.db.models import Price

        timestamps = [1705593600000, 1705593660000, 1705593720000]
        for ts in timestamps:
            price_data = sample_price_data.copy()
            price_data["timestamp"] = ts
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        response = test_client.get(f"/v1/prices/filter?ticker=btc_usd&start={timestamps[1]}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_filter_prices_with_only_end(self, test_client, db_session, sample_price_data):
        """Тест фильтрации только с конечной датой"""

        from app.db.models import Price

        # Создаем 3 записи
        timestamps = [1705593600000, 1705593660000, 1705593720000]
        for ts in timestamps:
            price_data = sample_price_data.copy()
            price_data["timestamp"] = ts
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        response = test_client.get(f"/v1/prices/filter?ticker=btc_usd&end={timestamps[1]}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_create_price_duplicate_timestamp(self, test_client, db_session):
        """Тест создания записи с дублирующимся timestamp"""

        from app.db.models import Price

        price_data = {
            "ticker": "btc_usd",
            "price": 50000.50,
            "timestamp": 1705593600000,
            "source_timestamp": 1705593600000000
        }

        response1 = test_client.post("/v1/prices/", json=price_data)
        assert response1.status_code == 201

        response2 = test_client.post("/v1/prices/", json=price_data)

        assert response2.status_code in [200, 201, 409]

    def test_get_stats_empty_database(self, test_client, db_session):
        """Тест получения статистики для пустой базы"""

        from app.db.models import Price

        db_session.query(Price).delete()
        db_session.commit()

        response = test_client.get("/v1/prices/stats?ticker=btc_usd")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["min_price"] is None
        assert data["max_price"] is None

    def test_get_available_tickers_empty(self, test_client, db_session):
        """Тест получения тикеров из пустой базы"""

        from app.db.models import Price

        db_session.query(Price).delete()
        db_session.commit()

        response = test_client.get("/v1/prices/available-tickers")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_ticker_case_sensitivity(self, test_client, db_session, sample_price_data):
        """Тест чувствительности к регистру тикеров"""

        from app.db.models import Price

        price_data_upper = sample_price_data.copy()
        price_data_upper["ticker"] = "BTC_USD"

        price_data_lower = sample_price_data.copy()
        price_data_lower["ticker"] = "btc_usd"
        price_data_lower["timestamp"] += 60000

        for price_data in [price_data_upper, price_data_lower]:
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        response = test_client.get("/v1/prices/?ticker=btc_usd")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_price_with_extreme_values(self, test_client):
        """Тест создания записи с экстремальными значениями"""

        test_cases = [
            {
                "name": "very_small_price",
                "data": {
                    "ticker": "btc_usd",
                    "price": 0.00000001,
                    "timestamp": 1705593600000,
                    "source_timestamp": 1705593600000000
                },
                "should_pass": True
            },
            {
                "name": "very_large_price",
                "data": {
                    "ticker": "btc_usd",
                    "price": 99999999.99999999,
                    "timestamp": 1705593600000,
                    "source_timestamp": 1705593600000000
                },
                "should_pass": True
            },
            {
                "name": "price_with_many_decimals",
                "data": {
                    "ticker": "btc_usd",
                    "price": 50000.12345678,
                    "timestamp": 1705593600000,
                    "source_timestamp": 1705593600000000
                },
                "should_pass": True
            }
        ]

        for test_case in test_cases:
            response = test_client.post("/v1/prices/", json=test_case["data"])

            if test_case["should_pass"]:
                assert response.status_code in [200, 201], f"Failed for {test_case['name']}: {response.text}"
            else:
                assert response.status_code >= 400, f"Should have failed for {test_case['name']}"


    @pytest.mark.asyncio
    async def test_concurrent_requests(self, db_session, sample_price_data):
        """Тест на конкурентные запросы через asyncio"""

        from app.db.models import Price

        db_session.query(Price).delete()
        db_session.commit()

        def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:

                async def make_request(request_num):
                    data = sample_price_data.copy()
                    data["timestamp"] += request_num * 1000
                    data["price"] += request_num * 10
                    response = await ac.post("/v1/prices/", json=data)
                    return response.status_code

                tasks = [make_request(i) for i in range(5)]
                results = await asyncio.gather(*tasks)

            successful = sum(1 for status_code in results if status_code in [200, 201])
            assert successful == 5, f"Not all requests succeeded: {results}"

        finally:
            app.dependency_overrides.clear()


    def test_malformed_json(self, test_client):
        """Тест с некорректным JSON"""

        response = test_client.post(
            "/v1/prices/",
            data='{"ticker": "btc_usd", "price": 50000.50, "timestamp": 1705593600000,',
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_unsupported_content_type(self, test_client):
        """Тест с неподдерживаемым Content-Type"""

        response = test_client.post(
            "/v1/prices/",
            data='{"ticker": "btc_usd", "price": 50000.50, "timestamp": 1705593600000}',
            headers={"Content-Type": "text/plain"}
        )

        assert response.status_code == 415 or response.status_code == 422

    def test_sql_injection_attempt(self, test_client):
        """Тест попытки SQL инъекции"""

        response = test_client.get(
            "/v1/prices/?ticker=btc_usd' OR '1'='1&skip=0&limit=10"
        )

        assert response.status_code in [200, 422]

        if response.status_code == 200:
            data = response.json()
            assert len(data) == 0
