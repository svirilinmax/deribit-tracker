from unittest.mock import MagicMock, Mock, patch


class TestWorkersAPI:
    """Тесты API для управления Celery задачами"""

    def test_trigger_fetch_prices(self, workers_test_client):
        """Тест запуска задачи получения цен"""

        with patch("app.api.v1.endpoints.workers.celery_app") as mock_celery:
            mock_task = Mock()
            mock_task.id = "test-task-id-123"

            mock_celery.tasks = {
                "fetch_prices_task": Mock(apply_async=Mock(return_value=mock_task))
            }

            response = workers_test_client.post("/v1/trigger-fetch-prices")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "test-task-id-123"
            assert data["status"] == "PENDING"

    def test_get_task_status(self, workers_test_client):
        """Тест получения статуса задачи"""

        with patch("app.api.v1.endpoints.workers.celery_app") as mock_celery:
            mock_task = Mock()
            mock_task.status = "SUCCESS"
            mock_task.ready = Mock(return_value=True)
            mock_task.get = Mock(return_value={"result": "success"})

            mock_celery.AsyncResult = Mock(return_value=mock_task)

            response = workers_test_client.get("/v1/tasks/test-task-id-123")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "test-task-id-123"
            assert data["status"] == "SUCCESS"
            assert data["ready"] is True

    def test_check_celery_health(self, workers_test_client):
        """Тест проверки здоровья Celery"""

        with patch("app.api.v1.endpoints.workers.celery_app") as mock_celery:
            mock_task = Mock()
            mock_task.id = "test-task-id-123"
            mock_task.status = "SUCCESS"
            mock_task.get = Mock(return_value={"status": "healthy"})

            mock_celery.tasks = {
                "health_check_task": Mock(apply_async=Mock(return_value=mock_task))
            }

            response = workers_test_client.get("/v1/health")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "test-task-id-123"
            assert data["result"]["status"] == "healthy"

    def test_get_queue_info(self, workers_test_client):
        """Тест получения информации об очередях"""

        with patch("redis.Redis") as mock_redis_class, patch(
            "app.api.v1.endpoints.workers.celery_app"
        ) as mock_celery:
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.from_url.return_value = mock_redis_instance

            mock_inspector = MagicMock()
            mock_inspector.active.return_value = {"worker1@hostname": []}
            mock_inspector.registered.return_value = {
                "worker1@hostname": ["fetch_prices_task"]
            }

            mock_celery.control.inspect.return_value = mock_inspector
            mock_celery.conf.broker_url = "redis://localhost:6379/0"

            response = workers_test_client.get("/v1/queues")

            assert response.status_code == 200
            data = response.json()
            assert "queues" in data
            assert "workers" in data
            assert "redis" in data
            assert data["redis"]["connected"] is True

    def test_get_task_status_not_found(self, workers_test_client):
        """Тест получения статуса несуществующей задачи"""

        with patch("app.api.v1.endpoints.workers.celery_app") as mock_celery:
            mock_task = Mock()
            mock_task.status = "PENDING"
            mock_task.ready = Mock(return_value=False)

            mock_celery.AsyncResult = Mock(return_value=mock_task)

            response = workers_test_client.get("/v1/tasks/non-existent-task")

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "non-existent-task"
            assert data["status"] == "PENDING"
            assert data["ready"] is False
