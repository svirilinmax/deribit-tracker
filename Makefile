.PHONY: help install dev up down logs test clean

help:
	@echo "Доступные команды:"
	@echo "  install    - установка зависимостей"
	@echo "  dev        - запуск в режиме разработки"
	@echo "  up         - запуск Docker контейнеров"
	@echo "  down       - остановка Docker контейнеров"
	@echo "  logs       - просмотр логов"
	@echo "  test       - запуск тестов"
	@echo "  clean      - очистка временных файлов"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.core.main:app --reload --host 0.0.0.0 --port 8000

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
