from unittest.mock import MagicMock, Mock, patch


class TestWorkersAPIExtended:
    """Расширенные тесты API для управления Celery задачами"""

    def test_trigger_fetch_prices_with_error(self, workers_test_client):
        """Тест запуска задачи с ошибкой"""
        with patch("app.api.v1.endpoints.workers.celery_app") as mock_celery:
            mock_celery.tasks = {}
            mock_celery.tasks["fetch_prices_task"] = Mock(
                apply_async=Mock(side_effect=Exception("Task not registered"))
            )

            response = workers_test_client.post("/v1/trigger-fetch-prices")

            assert response.status_code == 500
            assert "ошибка при запуске задачи" in response.json()["detail"].lower()

    def test_get_task_status_with_failed_task(self, workers_test_client):
        """Тест получения статуса неудачной задачи"""

        with patch("app.api.v1.endpoints.workers.celery_app") as mock_celery:
            mock_task = Mock()
            mock_task.status = "FAILURE"
            mock_task.ready = Mock(return_value=True)
            mock_task.get = Mock(side_effect=Exception("Task failed"))

            mock_celery.AsyncResult = Mock(return_value=mock_task)

            response = workers_test_client.get("/v1/tasks/failed-task-id")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "FAILURE"
            assert data["ready"] is True
            assert "error" in data

    def test_check_celery_health_timeout(self, workers_test_client):
        """Тест проверки здоровья с таймаутом"""

        with patch("app.api.v1.endpoints.workers.celery_app") as mock_celery:
            mock_task = Mock()
            mock_task.id = "test-task-id-123"
            mock_task.status = "PENDING"
            mock_task.get = Mock(side_effect=Exception("Task timeout"))

            mock_celery.tasks = {
                "health_check_task": Mock(apply_async=Mock(return_value=mock_task))
            }

            response = workers_test_client.get("/v1/health")

            assert response.status_code == 500
            assert "ошибка при проверке здоровья" in response.json()["detail"].lower()

    def test_get_queue_info_with_redis_error(self, workers_test_client):
        """Тест получения информации об очередях с ошибкой Redis"""

        with patch("redis.Redis") as mock_redis_class, patch(
            "app.api.v1.endpoints.workers.celery_app"
        ) as mock_celery:
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping = Mock(side_effect=Exception("Redis error"))
            mock_redis_class.from_url.return_value = mock_redis_instance

            mock_inspector = MagicMock()
            mock_inspector.active.return_value = None
            mock_inspector.registered.return_value = None

            mock_celery.control.inspect.return_value = mock_inspector
            mock_celery.conf.broker_url = "redis://localhost:6379/0"

            response = workers_test_client.get("/v1/queues")

            assert response.status_code == 200
            data = response.json()
            assert data["redis"]["connected"] is False
            assert data["workers"]["count"] == 0

    def test_get_queue_info_no_inspector(self, workers_test_client):
        """Тест получения информации об очередях без инспектора"""

        with patch("redis.Redis") as mock_redis_class, patch(
            "app.api.v1.endpoints.workers.celery_app"
        ) as mock_celery:
            mock_redis_instance = MagicMock()
            mock_redis_instance.ping.return_value = True
            mock_redis_class.from_url.return_value = mock_redis_instance

            mock_celery.control.inspect.return_value = None
            mock_celery.conf.broker_url = "redis://localhost:6379/0"

            response = workers_test_client.get("/v1/queues")

            assert response.status_code == 200
            data = response.json()
            assert data["redis"]["connected"] is True
            assert data["workers"]["count"] == 0

    def test_trigger_multiple_tasks(self, workers_test_client):
        """Тест запуска нескольких задач"""

        with patch("app.api.v1.endpoints.workers.celery_app") as mock_celery:
            task_ids = []

            def mock_apply_async():
                task = Mock()
                task.id = f"test-task-{len(task_ids)}"
                task_ids.append(task.id)
                return task

            mock_celery.tasks = {
                "fetch_prices_task": Mock(apply_async=mock_apply_async)
            }

            responses = []
            for i in range(3):
                response = workers_test_client.post("/v1/trigger-fetch-prices")
                responses.append(response)

            assert len(task_ids) == 3
            assert len(set(task_ids)) == 3

            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data["task_id"].startswith("test-task-")

    def test_task_status_workflow(self, workers_test_client):
        """Тест полного workflow задачи"""

        with patch("app.api.v1.endpoints.workers.celery_app") as mock_celery:
            # 1. Запускаем задачу
            task_mock = Mock()
            task_mock.id = "workflow-task-id"

            mock_celery.tasks = {
                "fetch_prices_task": Mock(apply_async=Mock(return_value=task_mock))
            }

            response1 = workers_test_client.post("/v1/trigger-fetch-prices")
            assert response1.status_code == 200
            task_id = response1.json()["task_id"]

            task_mock.status = "PENDING"
            task_mock.ready = Mock(return_value=False)

            mock_celery.AsyncResult = Mock(return_value=task_mock)

            response2 = workers_test_client.get(f"/v1/tasks/{task_id}")
            assert response2.status_code == 200
            assert response2.json()["status"] == "PENDING"

            task_mock.status = "SUCCESS"
            task_mock.ready = Mock(return_value=True)
            task_mock.get = Mock(return_value={"result": "success"})

            response3 = workers_test_client.get(f"/v1/tasks/{task_id}")
            assert response3.status_code == 200
            assert response3.json()["status"] == "SUCCESS"
            assert response3.json()["ready"] is True
