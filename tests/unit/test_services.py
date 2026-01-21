from app.services.price_service import PriceService
from app.schemas.price import PriceCreate
from app.db.models import Price


class TestPriceService:
    """Тесты сервиса цен"""

    def test_get_prices(self, db_session, sample_price_data):
        """Тест получения всех цен по тикеру"""

        for i in range(5):
            price_data = sample_price_data.copy()
            price_data["timestamp"] += i * 60000
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        prices = PriceService.get_prices(db_session, ticker="btc_usd", skip=1, limit=2)

        assert len(prices) == 2
        assert all(p.ticker == "btc_usd" for p in prices)
        assert prices[0].timestamp > prices[1].timestamp

    def test_get_prices_empty(self, db_session):
        """Тест получения цен при пустой базе"""

        prices = PriceService.get_prices(db_session, ticker="btc_usd")
        assert len(prices) == 0

    def test_get_latest_price(self, db_session, sample_price_data):
        """Тест получения последней цены"""

        for i in range(3):
            price_data = sample_price_data.copy()
            price_data["timestamp"] += i * 60000
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        latest_price = PriceService.get_latest_price(db_session, "btc_usd")

        assert latest_price is not None
        assert latest_price.ticker == "btc_usd"
        assert latest_price.timestamp == sample_price_data["timestamp"] + 120000

    def test_get_latest_price_not_found(self, db_session):
        """Тест получения последней цены при отсутствии данных"""

        latest_price = PriceService.get_latest_price(db_session, "btc_usd")
        assert latest_price is None

    def test_get_prices_by_date_range(self, db_session, sample_price_data):
        """Тест фильтрации по дате"""

        timestamps = [
            1705593600000,  # 00:00
            1705593660000,  # 00:01
            1705593720000,  # 00:02
            1705593780000,  # 00:03
        ]

        for ts in timestamps:
            price_data = sample_price_data.copy()
            price_data["timestamp"] = ts
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        filtered = PriceService.get_prices_by_date_range(
            db_session,
            ticker="btc_usd",
            start_timestamp=1705593660000,
            end_timestamp=1705593720000
        )

        assert len(filtered) == 2
        assert all(1705593660000 <= p.timestamp <= 1705593720000 for p in filtered)

    def test_get_prices_by_date_range_no_end(self, db_session, sample_price_data):
        """Тест фильтрации без конечной даты"""

        price = Price(**sample_price_data)
        db_session.add(price)
        db_session.commit()

        filtered = PriceService.get_prices_by_date_range(
            db_session,
            ticker="btc_usd",
            start_timestamp=sample_price_data["timestamp"] - 1000
        )

        assert len(filtered) == 1
        assert filtered[0].timestamp == sample_price_data["timestamp"]

    def test_create_price(self, db_session):
        """Тест создания записи о цене"""

        price_create = PriceCreate(
            ticker="btc_usd",
            price=50000.50,
            timestamp=1705593600000,
            source_timestamp=1705593600000000
        )

        created_price = PriceService.create_price(db_session, price_create)

        assert created_price.id is not None
        assert created_price.ticker == "btc_usd"
        assert float(created_price.price) == 50000.50
        assert created_price.timestamp == 1705593600000

        db_price = db_session.query(Price).filter(Price.id == created_price.id).first()
        assert db_price is not None
        assert db_price.ticker == "btc_usd"

    def test_get_stats(self, db_session, sample_price_data):
        """Тест получения статистики"""

        prices = [45000.00, 46000.00, 47000.00, 48000.00, 49000.00]

        for i, price_value in enumerate(prices):
            price_data = sample_price_data.copy()
            price_data["price"] = price_value
            price_data["timestamp"] += i * 60000
            price = Price(**price_data)
            db_session.add(price)
        db_session.commit()

        stats = PriceService.get_stats(db_session, "btc_usd")

        assert stats["count"] == 5
        assert float(stats["min_price"]) == 45000.00
        assert float(stats["max_price"]) == 49000.00
        assert 46500.00 < float(stats["avg_price"]) < 47500.00
        assert stats["first_timestamp"] == sample_price_data["timestamp"]
        assert stats["last_timestamp"] == sample_price_data["timestamp"] + 240000

    def test_get_stats_no_data(self, db_session):
        """Тест статистики при отсутствии данных"""

        stats = PriceService.get_stats(db_session, "btc_usd")

        assert stats["count"] == 0
        assert stats["min_price"] is None
        assert stats["max_price"] is None
        assert stats["avg_price"] is None
        assert stats["first_timestamp"] is None
        assert stats["last_timestamp"] is None
