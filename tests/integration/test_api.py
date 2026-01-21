class TestPricesAPI:
    """Тесты API эндпоинтов для цен"""

    def test_get_prices_success(self, test_client, db_session, sample_price_data):
        """Тест получения всех цен"""

        from app.db.models import Price

        # Очищаем таблицу перед тестом
        db_session.query(Price).delete()
        db_session.commit()

        for i in range(3):
            price_data = sample_price_data.copy()
            price_data["timestamp"] += i * 60000
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        response = test_client.get("/v1/prices/?ticker=btc_usd&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["ticker"] == "btc_usd" for item in data)

    def test_get_prices_missing_ticker(self, test_client):
        """Тест получения цен без указания тикера"""

        response = test_client.get("/v1/prices/")
        assert response.status_code == 422

    def test_get_prices_invalid_ticker(self, test_client, db_session):
        """Тест получения цен с невалидным тикером"""

        response = test_client.get("/v1/prices/?ticker=invalid_ticker")

        if response.status_code == 200:
            data = response.json()
            assert len(data) == 0
        else:
            assert response.status_code == 422

    def test_get_prices_pagination(self, test_client, db_session, sample_price_data):
        """Тест пагинации"""

        from app.db.models import Price

        db_session.query(Price).delete()
        db_session.commit()

        for i in range(5):
            price_data = sample_price_data.copy()
            price_data["timestamp"] += i * 60000
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        response1 = test_client.get("/v1/prices/?ticker=btc_usd&skip=0&limit=2")
        data1 = response1.json()
        assert len(data1) == 2

        response2 = test_client.get("/v1/prices/?ticker=btc_usd&skip=2&limit=2")
        data2 = response2.json()
        assert len(data2) == 2

        assert data1[0]["timestamp"] != data2[0]["timestamp"]

    def test_get_latest_price_success(self, test_client, db_session, sample_price_data):
        """Тест получения последней цены"""

        from app.db.models import Price

        db_session.query(Price).delete()
        db_session.commit()

        for i in range(3):
            price_data = sample_price_data.copy()
            price_data["timestamp"] += i * 60000
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        response = test_client.get("/v1/prices/latest?ticker=btc_usd")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "btc_usd"

        assert data["timestamp"] == sample_price_data["timestamp"] + 120000

    def test_get_latest_price_not_found(self, test_client, db_session):
        """Тест получения последней цены при отсутствии данных"""

        from app.db.models import Price

        db_session.query(Price).delete()
        db_session.commit()

        response = test_client.get("/v1/prices/latest?ticker=btc_usd")
        assert response.status_code == 404
        assert "не найдены" in response.json()["detail"].lower()

    def test_filter_prices_by_date(self, test_client, db_session, sample_price_data):
        """Тест фильтрации по дате"""

        from app.db.models import Price

        db_session.query(Price).delete()
        db_session.commit()

        timestamps = [1705593600000, 1705593660000, 1705593720000]

        for ts in timestamps:
            price_data = sample_price_data.copy()
            price_data["timestamp"] = ts
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        response = test_client.get(
            "/v1/prices/filter?"
            f"ticker=btc_usd&"
            f"start={timestamps[1]}&"
            f"end={timestamps[2]}"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(timestamps[1] <= item["timestamp"] <= timestamps[2] for item in data)

    def test_filter_prices_invalid_range(self, test_client):
        """Тест фильтрации с некорректным диапазоном"""

        response = test_client.get(
            "/v1/prices/filter?ticker=btc_usd&start=1000&end=500"
        )
        assert response.status_code == 400
        assert "не может быть больше" in response.json()["detail"].lower()

    def test_filter_prices_no_dates(self, test_client, db_session, sample_price_data):
        """Тест фильтрации без указания дат"""

        from app.db.models import Price

        db_session.query(Price).delete()
        db_session.commit()

        price = Price(**sample_price_data)
        db_session.add(price)
        db_session.commit()

        response = test_client.get("/v1/prices/filter?ticker=btc_usd")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["ticker"] == "btc_usd"

    def test_get_price_stats(self, test_client, db_session, sample_price_data):
        """Тест получения статистики"""

        from app.db.models import Price

        db_session.query(Price).delete()
        db_session.commit()

        prices = [45000.00, 46000.00, 47000.00]

        for i, price_value in enumerate(prices):
            price_data = sample_price_data.copy()
            price_data["price"] = price_value
            price_data["timestamp"] += i * 60000
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        response = test_client.get("/v1/prices/stats?ticker=btc_usd")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert float(data["min_price"]) == 45000.00
        assert float(data["max_price"]) == 47000.00

    def test_get_available_tickers(self, test_client, db_session, sample_price_data):
        """Тест получения доступных тикеров"""

        from app.db.models import Price

        db_session.query(Price).delete()
        db_session.commit()

        tickers = ["btc_usd", "eth_usd", "btc_usd"]

        for ticker in tickers:
            price_data = sample_price_data.copy()
            price_data["ticker"] = ticker
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        response = test_client.get("/v1/prices/available-tickers")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert "btc_usd" in data
        assert "eth_usd" in data
        assert data[0] == "btc_usd"

    def test_create_price(self, test_client, db_session):
        """Тест создания записи о цене"""

        from app.db.models import Price

        db_session.query(Price).delete()
        db_session.commit()

        price_data = {
            "ticker": "btc_usd",
            "price": 50000.50,
            "timestamp": 1705593600000,
            "source_timestamp": 1705593600000000,
        }

        response = test_client.post("/v1/prices/", json=price_data)

        assert (
            response.status_code == 201
        ), f"Expected 201, got {response.status_code}: {response.text}"

        data = response.json()
        assert data["ticker"] == "btc_usd"
        assert data["price"] == 50000.50
        assert data["id"] is not None

    def test_create_price_invalid_data(self, test_client):
        """Тест создания записи с невалидными данными"""

        invalid_data = {"ticker": "bt", "price": -100, "timestamp": 1705593600000}

        response = test_client.post("/v1/prices/", json=invalid_data)
        assert response.status_code == 422

    def test_root_endpoint(self, test_client):
        """Тест корневого эндпоинта"""

        response = test_client.get("/")
        assert response.status_code == 200
        assert (
            "deribit" in response.json()["message"].lower()
            or "tracker" in response.json()["message"].lower()
        )

    def test_health_endpoint(self, test_client):
        """Тест health check эндпоинта"""

        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
