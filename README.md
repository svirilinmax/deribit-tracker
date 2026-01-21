# Deribit Price Tracker

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-5.3-37814A?logo=celery)](https://docs.celeryq.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com/)

# Deribit Price Tracker

Профессиональная система мониторинга цен криптовалют с биржи Deribit. Система автоматически получает индексные цены BTC/USD и ETH/USD каждую минуту, сохраняет их в базу данных и предоставляет REST API для доступа к данным.

## Ключевые особенности

- **Автоматический сбор данных**: Получение цен BTC/USD и ETH/USD каждую минуту через Deribit API
- **Надежное хранение**: Сохранение исторических данных в PostgreSQL
- **Полноценное REST API**: CRUD операции для работы с данными цен
- **Асинхронная обработка**: Использование Celery для фоновых задач
- **Контейнеризация**: Полная Docker-сборка для легкого развертывания
- **Комплексное тестирование**: 113 автоматических тестов с покрытием кода 81%

## Технологический стек

- **Backend**: FastAPI, Python 3.10+
- **База данных**: PostgreSQL 15
- **Очереди задач**: Celery 5.3 с Redis в качестве брокера
- **Контейнеризация**: Docker, Docker Compose
- **ORM**: SQLAlchemy 2.0 с асинхронной поддержкой
- **Миграции**: Alembic
- **HTTP клиент**: aiohttp
- **Тестирование**: pytest с асинхронной поддержкой

## Быстрый старт

### Требования

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.10+ (для локальной разработки)

### Запуск через Docker Compose

1. Клонируйте репозиторий:
```bash
    git clone https://github.com/svirilinmax/deribit-tracker.git
    cd deribit-tracker
```

2. Настройте переменные окружения:
```bash
    cp .env.example .env
    # Отредактируйте .env при необходимости
```

3. Запустите все сервисы:
```bash
    docker-compose up -d --build
```

4. Проверьте статус сервисов:
```bash
    docker-compose ps
```

5. Примените миграции базы данных:
```bash
    docker-compose exec api alembic upgrade head
```

### Проверка работоспособности

После запуска проверьте доступность сервисов:

1. **API документация**: http://localhost:8000/docs
2. **API интерфейс**: http://localhost:8000
3. **Мониторинг Celery (Flower)**: http://localhost:5555
4. **Health check API**: http://localhost:8000/health

## Архитектура системы

### Компоненты системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Deribit API   │◄───│  Celery Worker  │◄───│   Celery Beat   │
│   (внешний)     │    │   (задачи)      │    │  (расписание)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       │
┌─────────────────┐    ┌─────────────────┐               │
│   FastAPI       │    │   PostgreSQL    │◄──────────────┘
│   (REST API)    │───►│   (данные)      │
└─────────────────┘    └─────────────────┘
         ▲                       ▲
         │                       │
┌─────────────────┐    ┌─────────────────┐
│   Клиенты       │    │     Redis       │
│   (HTTP)        │    │  (брокер/кеш)   │
└─────────────────┘    └─────────────────┘
```

### Docker сервисы

- **api**: FastAPI приложение (порт 8000)
- **postgres**: PostgreSQL база данных (порт 5432)
- **redis**: Redis сервер для брокера сообщений (порт 6379)
- **celery_worker**: Celery воркер для выполнения задач
- **celery_beat**: Celery планировщик для периодических задач
- **flower**: Веб-интерфейс для мониторинга Celery (порт 5555)

## REST API

### Основные эндпоинты

Все эндпоинты требуют обязательного query-параметра `ticker` (значения: `btc_usd`, `eth_usd`).

#### 1. Получение всех цен для указанного тикера
```http
GET /api/v1/prices?ticker=btc_usd&skip=0&limit=100
```

**Параметры:**
- `ticker`: Тикер для фильтрации (обязательный)
- `skip`: Количество записей для пропуска (по умолчанию 0)
- `limit`: Максимальное количество записей (по умолчанию 100, максимум 1000)

**Ответ:**
```json
{
  "data": [
    {
      "id": 1,
      "ticker": "btc_usd",
      "price": 95413.23,
      "timestamp": 1768768182422,
      "created_at": "2026-01-18T20:29:43.530431+00:00"
    }
  ],
  "count": 1,
  "ticker": "btc_usd"
}
```

#### 2. Получение последней цены
```http
GET /api/v1/prices/latest?ticker=eth_usd
```

**Ответ:**
```json
{
  "id": 8,
  "ticker": "eth_usd",
  "price": 3349.74,
  "timestamp": 1768768260410,
  "created_at": "2026-01-18T20:31:01.151955+00:00"
}
```

#### 3. Фильтрация цен по дате
```http
GET /api/v1/prices/filter?ticker=btc_usd&start=1768768200000&end=1768768260000
```

**Параметры:**
- `start`: Начальный timestamp в миллисекундах (необязательный)
- `end`: Конечный timestamp в миллисекундах (необязательный)

**Ответ:**
```json
{
  "data": [
    {
      "id": 5,
      "ticker": "btc_usd",
      "price": 95415.31,
      "timestamp": 1768768200232,
      "created_at": "2026-01-18T20:30:00.855229+00:00"
    }
  ],
  "count": 1,
  "ticker": "btc_usd",
  "start": 1768768200000,
  "end": 1768768260000
}
```

#### 4. Получение статистики по ценам
```http
GET /api/v1/prices/stats?ticker=btc_usd
```

**Ответ:**
```json
{
  "ticker": "btc_usd",
  "count": 100,
  "average_price": 95412.45,
  "min_price": 95380.12,
  "max_price": 95450.89,
  "first_price_timestamp": 1768768182422,
  "last_price_timestamp": 1768768782422
}
```

#### 5. Получение доступных тикеров
```http
GET /api/v1/prices/tickers
```

**Ответ:**
```json
{
  "tickers": ["btc_usd", "eth_usd"],
  "count": 2
}
```

#### 6. Создание новой цены (ручное добавление)
```http
POST /api/v1/prices/
Content-Type: application/json

{
  "ticker": "btc_usd",
  "price": 95413.23,
  "timestamp": 1768768182422
}
```

### Эндпоинты для управления задачами

#### 1. Запуск задачи получения цен
```http
POST /api/v1/workers/tasks/fetch_prices
```

#### 2. Получение статуса задачи
```http
GET /api/v1/workers/tasks/{task_id}/status
```

#### 3. Получение информации об очередях
```http
GET /api/v1/workers/queues
```

#### 4. Проверка здоровья Celery
```http
GET /api/v1/workers/health
```

### Служебные эндпоинты

#### Health check
```http
GET /health
```

#### Корневой эндпоинт
```http
GET /
```

## Конфигурация

### Переменные окружения

Создайте файл `.env` на основе `.env.example`:

```env
# Настройки приложения
APP_NAME=Deribit Tracker
APP_ENV=development
DEBUG=False

# База данных
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=deribit_tracker
POSTGRES_USER=deribit_user
POSTGRES_PASSWORD=deribit_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Deribit API
DERIBIT_BASE_URL=https://test.deribit.com/api/v2
DERIBIT_API_TIMEOUT=30

# Логирование
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/app.log

# Настройки retry
API_MAX_RETRIES=3
API_RETRY_DELAY=1
API_RETRY_BACKOFF=2
```

### Celery задачи

Система автоматически выполняет следующие задачи:

1. **fetch_prices_task** - каждую минуту получает цены BTC/USD и ETH/USD
2. **health_check_task** - каждые 5 минут проверяет здоровье системы
3. **cleanup_old_prices_task** - очистка старых данных (можно запустить вручную)

## Структура проекта

```
deribit-tracker/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/           # Реализация эндпоинтов
│   │   │   │   ├── prices.py        # Эндпоинты для работы с ценами
│   │   │   │   └── workers.py       # Эндпоинты для управления задачами
│   │   │   ├── api.py               # Роутер API v1
│   │   │   └── deps.py              # Зависимости FastAPI
│   │   └── exception.py             # Обработка исключений API
│   ├── clients/
│   │   ├── deribit.py               # Клиент для работы с Deribit API
│   │   ├── exceptions.py            # Исключения клиента
│   │   └── schemas.py               # Схемы ответов Deribit
│   ├── core/
│   │   ├── config.py                # Конфигурация приложения
│   │   ├── dependencies.py          # Общие зависимости
│   │   ├── logging.py               # Настройка логирования
│   │   └── main.py                  # Точка входа FastAPI
│   ├── db/
│   │   ├── database.py              # Конфигурация БД
│   │   ├── models.py                # SQLAlchemy модели
│   │   └── session.py               # Управление сессиями
│   ├── schemas/
│   │   └── price.py                 # Pydantic схемы для цен
│   ├── services/
│   │   └── price_service.py         # Бизнес-логика работы с ценами
│   └── workers/
│       ├── celery_app.py            # Конфигурация Celery
│       └── tasks.py                 # Реализация задач
├── alembic/
│   ├── versions/                    # Файлы миграций
│   └── env.py                       # Конфигурация Alembic
├── docker/
│   └── Dockerfile                   # Dockerfile для API
├── logs/                            # Логи приложения
├── tests/                           # Тесты
│   ├── integration/                 # Интеграционные тесты
│   │   ├── test_api.py              # Тесты API
│   │   ├── test_api_edge_cases.py   # Тесты граничных случаев API
│   │   └── test_workers_api.py      # Тесты API для задач
│   ├── unit/                        # Юнит-тесты
│   │   ├── test_clients.py          # Тесты клиента Deribit
│   │   ├── test_models.py           # Тесты моделей БД
│   │   ├── test_schemas.py          # Тесты Pydantic схем
│   │   ├── test_services.py         # Тесты сервисов
│   │   └── test_workers.py          # Тесты Celery задач
│   └── conftest.py                  # Фикстуры pytest
├── .pre-commit-config.yaml
├── docker-compose.yml               # Docker Compose конфигурация
├── requirements.txt                 # Зависимости Python
├── alembic.ini                      # Конфигурация Alembic
├── pytest.ini                       # Конфигурация pytest
└── Makefile                         # Утилиты для разработки
```

## Тестирование

### Обзор тестов

Проект включает 113 автоматических тестов с общим покрытием кода 81%:

- **Интеграционные тесты (31)**: Тестирование API эндпоинтов
- **Юнит-тесты (82)**: Тестирование отдельных компонентов системы

### Запуск тестов

#### Локальный запуск
```bash
    # Все тесты
    pytest -v

    # С покрытием кода
    pytest --cov=app --cov-report=html --cov-report=xml

    # Конкретная категория тестов
    pytest tests/unit/ -v
    pytest tests/integration/ -v

    # Конкретный тестовый файл
    pytest tests/unit/test_clients.py -v
```

#### Запуск в Docker
```bash
    # Запуск всех тестов
    docker-compose exec api pytest -v

    # Тесты с покрытием
    docker-compose exec api pytest --cov=app

    # Создание отчета о покрытии
    docker-compose exec api pytest --cov=app --cov-report=html
```

### Категории тестов

#### Интеграционные тесты (`tests/integration/`)
- **test_api.py**: Основные тесты API эндпоинтов
- **test_api_edge_cases.py**: Тесты граничных случаев и ошибок
- **test_workers_api.py**: Тесты API для управления задачами
- **test_workers_api_extended.py**: Расширенные тесты API для задач с обработкой ошибок

#### Юнит-тесты (`tests/unit/`)
- **test_clients.py**: Тесты клиента Deribit API
- **test_models.py**: Тесты моделей базы данных
- **test_schemas.py**: Тесты Pydantic схем валидации
- **test_services.py**: Тесты бизнес-логики сервисов
- **test_workers.py**: Тесты Celery задач

## Docker команды

### Управление сервисами
```bash
    # Запуск всех сервисов
    docker-compose up -d

    # Остановка всех сервисов
    docker-compose down

    # Пересборка и запуск
    docker-compose up -d --build

    # Просмотр логов
    docker-compose logs -f api
    docker-compose logs -f celery_worker

    # Проверка состояния
    docker-compose ps
```

### Управление базой данных
```bash
    # Применение миграций
    docker-compose exec api alembic upgrade head

    # Создание новой миграции
    docker-compose exec api alembic revision --autogenerate -m "Описание изменений"

    # Откат миграции
    docker-compose exec api alembic downgrade -1

    # Доступ к консоли PostgreSQL
    docker-compose exec postgres psql -U deribit_user -d deribit_tracker
```

### Управление Celery
```bash
# Проверка зарегистрированных задач
    docker-compose exec celery_worker celery -A app.workers.celery_app inspect registered

    # Проверка активных задач
    docker-compose exec celery_worker celery -A app.workers.celery_app inspect active

    # Запуск задачи вручную
    docker-compose exec celery_worker celery -A app.workers.celery_app call fetch_prices_task

    # Просмотр очередей в Redis
    docker-compose exec redis redis-cli keys "celery*"
```

## Мониторинг и диагностика

### Логирование

Логи доступны в следующих местах:

1. **Файлы логов**: `logs/app.log` (структурированный JSON формат)
2. **Docker логи**: `docker-compose logs -f [service_name]`
3. **Celery логи**: Доступны через Flower интерфейс

### Health checks

```bash
    # Проверка здоровья API
    curl http://localhost:8000/health

    # Проверка доступности БД
    docker-compose exec postgres pg_isready -U deribit_user

    # Проверка Redis
    docker-compose exec redis redis-cli ping
```

### Flower мониторинг

Flower предоставляет веб-интерфейс для мониторинга Celery:
- **URL**: http://localhost:5555
- **Функции**: Мониторинг задач, очередей, воркеров
- **Метрики**: Время выполнения, успешные/неуспешные задачи

## Диагностика проблем

### Распространенные проблемы

#### 1. Celery задачи не выполняются
```bash
    # Проверить регистрацию задач
    docker-compose exec celery_worker celery -A app.workers.celery_app inspect registered

    # Проверить наличие воркеров
    docker-compose exec celery_worker celery -A app.workers.celery_app inspect active

    # Проверить подключение к Redis
    docker-compose exec redis redis-cli ping
```

#### 2. Проблемы с подключением к БД
```bash
    # Проверить доступность PostgreSQL
    docker-compose exec postgres pg_isready -U deribit_user

    # Проверить миграции
    docker-compose exec api alembic current

    # Проверить логи приложения
    docker-compose logs -f api | grep -i database
```

#### 3. Ошибки Deribit API
```bash
    # Проверить доступность API Deribit
    curl -X POST https://test.deribit.com/api/v2/public/get_time

    # Проверить логи клиента
    docker-compose logs -f api | grep -i deribit
```

#### 4. Проблемы с памятью
```bash
    # Очистка Docker
    docker system prune -a
    docker volume prune

    # Перезапуск сервисов
    docker-compose down
    docker-compose up -d --build
```

## Производительность и масштабирование

### Оптимизации

1. **Индексы базы данных**: Составные индексы для ускорения запросов по тикеру и времени
2. **Асинхронные операции**: Использование async/await для работы с внешними API
3. **Пул соединений**: Настройка пула соединений SQLAlchemy
4. **Пакетные операции**: Пакетная вставка данных при получении цен

### Масштабирование

Система спроектирована для горизонтального масштабирования:

1. **API сервисы**: Можно запускать несколько экземпляров за балансировщиком нагрузки
2. **Celery workers**: Легко добавлять дополнительные воркеры для обработки задач
3. **PostgreSQL**: Возможность настройки репликации для чтения
4. **Redis**: Поддержка кластеризации для высокой доступности

## Design Decisions

### 1. Архитектурные решения

#### Многослойная архитектура
Проект использует четкое разделение на слои:
- **API слой** (`app/api/`) - обработка HTTP запросов и валидация
- **Сервисный слой** (`app/services/`) - бизнес-логика
- **Слой данных** (`app/db/`) - работа с базой данных
- **Клиентский слой** (`app/clients/`) - взаимодействие с внешними API

**Обоснование:** Такое разделение обеспечивает:
- Высокую связанность внутри слоев и низкую между слоями
- Простое тестирование каждого компонента
- Легкую замену реализации одного слоя без влияния на другие

#### Асинхронный подход
- **aiohttp** для клиента Deribit API вместо requests
- **Асинхронные контекстные менеджеры** для управления сессиями

**Обоснование:**
- Эффективное использование ресурсов при работе с I/O операциями
- Возможность обработки множества одновременных запросов
- Современный подход, соответствующий стандартам Python 3.10+

### 2. Выбор технологий

#### FastAPI vs Django REST Framework
Выбран **FastAPI** по следующим причинам:
- **Производительность:** Основан на Starlette и Pydantic, один из самых быстрых фреймворков
- **Автодокументация:** Автоматическая генерация OpenAPI документации
- **Type hints:** Полная поддержка аннотаций типов
- **Асинхронность:** Нативная поддержка async/await

#### Celery для периодических задач
**Обоснование выбора:**
- **Проверенная надежность:** Производственная система с множеством интеграций
- **Гибкое расписание:** Поддержка crontab, интервалов, солнечных событий
- **Мониторинг:** Интеграция с Flower для визуализации
- **Масштабируемость:** Возможность горизонтального масштабирования воркеров

#### PostgreSQL для хранения данных
**Преимущества выбора:**
- **Надежность:** ACID-совместимая СУБД
- **Производительность:** Эффективные индексы для временных рядов
- **Расширяемость:** Поддержка JSONB, полнотекстового поиска
- **Экосистема:** Широкий выбор инструментов мониторинга и бэкапа

### 3. Решения по обработке данных

#### Структура таблицы prices
```sql
CREATE TABLE prices (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    timestamp BIGINT NOT NULL,
    source_timestamp BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Дизайн-решения:**
1. **`DECIMAL(20,8)` для цен:** Обеспечивает точность до 8 знаков после запятой, что достаточно для криптовалютных цен
2. **Два timestamp поля:**
   - `timestamp` - UNIX timestamp в миллисекундах для API
   - `source_timestamp` - оригинальный timestamp от Deribit в микросекундах для трассировки
3. **Индексы:** Составной индекс `(ticker, timestamp DESC)` для оптимизации запросов по тикеру и времени

#### Стратегия retry для внешних API
```python
# Экспоненциальный backoff с jitter
wait_time = settings.API_RETRY_DELAY * (settings.API_RETRY_BACKOFF ** retry_count)
```

**Обоснование:**
- **Экспоненциальный backoff:** Увеличивает интервалы между попытками
- **Jitter:** Добавляет случайность для предотвращения "stampede effect"
- **Максимум 3 попытки:** Баланс между надежностью и временем ответа

### 4. Решения по обработке ошибок

#### Многоуровневая обработка ошибок
1. **Клиентский уровень:** Обработка сетевых ошибок, таймаутов
2. **Сервисный уровень:** Валидация бизнес-правил
3. **API уровень:** Преобразование в HTTP статус-коды

**Пример:**
```python
try:
    data = await client.get_index_price(index_name)
except DeribitAPIError as e:
    # Логирование с контекстом
    logger.error(f"API error for {index_name}", extra={"error_code": e.code})
    raise
```

### 5. Решения по контейнеризации

#### Docker Compose структура
- **Отдельные сервисы** для каждой компоненты системы
- **Health checks** для всех критических сервисов
- **Volume монтирование** для персистентных данных и логов

**Обоснование:**
- **Изоляция:** Каждый сервис работает в своем контейнере
- **Воспроизводимость:** Идентичная среда разработки и продакшена
- **Масштабируемость:** Легкое добавление реплик воркеров

### 6. Решения по логированию

#### Структурированные логи (JSON)
```json
{
  "timestamp": "2026-01-18T20:29:43.448Z",
  "level": "INFO",
  "message": "Цена сохранена в БД",
  "module": "app.workers.tasks",
  "extra": {
    "ticker": "btc_usd",
    "price": 95413.23,
    "task_id": "685b9993-1fe8-46dc-9dd6-883dbd673c80"
  }
}
```

**Преимущества:**
- **Машинно-читаемый формат:** Легкая интеграция с ELK/Grafana
- **Контекстная информация:** Все необходимые метаданные в каждом логе
- **Фильтрация:** Возможность фильтрации по полям

### 7. Решения по производительности

#### Оптимизация запросов к БД
1. **Пакетная вставка:** Вместо отдельных INSERT для каждой цены
2. **Индексы:** Оптимизированные индексы для частых запросов
3. **Пул соединений:** Настройка SQLAlchemy для эффективного использования соединений

#### Асинхронный Deribit клиент
- **Параллельные запросы:** Возможность одновременного получения цен для нескольких тикеров
- **Подключение keep-alive:** Повторное использование HTTP соединений
- **Таймауты:** Защита от "зависания" запросов

### 8. Решения для будущего масштабирования

#### Защита от перегрузки API
```python
# Rate limiting в Celery
task_annotations={
    "*": {
        "rate_limit": "10/m",  # Ограничение 10 задач в минуту
    }
}
```

#### Возможности для горизонтального масштабирования
1. **Stateless API:** FastAPI приложение не хранит состояние
2. **Redis как брокер:** Поддержка кластеризации
3. **PostgreSQL репликация:** Чтение с реплик для распределения нагрузки

### 9. Компромиссы и trade-offs

#### Простота vs Гибкость
- **Выбрано:** Более простая начальная реализация
- **Компромисс:** Некоторые расширенные функции (аутентификация, WebSocket) не реализованы
- **Обоснование:** Соответствие требованиям ТЗ с возможностью легкого расширения

#### Полнота данных vs Производительность
- **Выбрано:** Сохранение всех исторических данных
- **Компромисс:** Необходимость периодической очистки старых данных
- **Обоснование:** Требования ТЗ не ограничивают объем хранения

### 10. Будущие улучшения

Приоритетные улучшения для production:

1. **Аутентификация API:** JWT токены или API ключи
2. **Rate limiting:** Защита от DDoS атак
3. **Метрики Prometheus:** Мониторинг производительности
4. **Кэширование Redis:** Ускорение часто запрашиваемых данных
5. **Alerting:** Уведомления о проблемах в системе

Раздел "Design Decisions" критически важен, потому что он:
1. **Показывает глубину понимания** архитектурных принципов
2. **Демонстрирует осознанный выбор технологий** с обоснованием
3. **Объясняет компромиссы** и trade-offs, сделанные при проектировании
4. **Показывает forward-thinking** с учетом будущего масштабирования
5. **Документирует rationale** для будущих разработчиков или ревьюеров

## Безопасность

### Рекомендации для production

1. **Изменение паролей по умолчанию**: Обязательно измените пароли в `.env` файле
2. **Настройка HTTPS**: Используйте reverse proxy (nginx, traefik) для HTTPS
3. **Ограничение доступа**: Настройте брандмауэр для доступа только к необходимым портам
4. **Регулярное обновление**: Следите за обновлениями зависимостей
5. **Мониторинг и алертинг**: Настройте мониторинг и уведомления о проблемах

### Защита API

- **Валидация входных данных**: Все параметры валидируются через Pydantic
- **Ограничение запросов**: Ограничение на количество возвращаемых записей
- **Обработка ошибок**: Информативные сообщения об ошибках без раскрытия деталей реализации
- **Логирование**: Структурированное логирование всех операций

## Разработка

### Настройка среды разработки

1. **Установите зависимости**:
```bash
    python -m venv .venv
    source .venv/bin/activate  # На Unix
    # или
    .venv\Scripts\activate  # На Windows
    pip install -r requirements.txt
```

2. **Настройте базу данных**:
```bash
    # Создайте базу данных
    createdb deribit_tracker

    # Примените миграции
    alembic upgrade head
```

3. **Запустите Redis**:
```bash
    # Через Docker
    docker run -d -p 6379:6379 redis

    # Или установите локально
```

4. **Запустите приложение**:
```bash
# Запуск API
    uvicorn app.core.main:app --reload

    # Запуск Celery worker
    celery -A app.workers.celery_app worker --loglevel=info

    # Запуск Celery beat
    celery -A app.workers.celery_app beat --loglevel=info
```

### Создание миграций

```bash
    # Автогенерация миграции на основе изменений моделей
    alembic revision --autogenerate -m "Описание изменений"

    # Применение миграции
    alembic upgrade head
```

### Стиль кода

Проект использует:
- **PEP 8**: Стандартный стиль Python
- **Type hints**: Аннотации типов для всего кода
- **Black**: Автоматическое форматирование кода
- **isort**: Сортировка импортов
- **mypy**: Статическая проверка типов

# Pre-commit хуки

Проект использует pre-commit хуки для автоматической проверки и форматирования кода перед коммитом. 
## Установка pre-commit

```bash
    # Установка пакета pre-commit
    pip install pre-commit
    
    # Установка хуков в локальный репозиторий
    pre-commit install
    
    # Установка хуков для коммита в процессе (prepare-commit-msg)
    pre-commit install --hook-type prepare-commit-msg
```

После установки хуки будут автоматически запускаться при каждой попытке коммита.

## Доступные проверки

Система включает следующие автоматические проверки:

### 1. Форматирование и очистка кода
- **trim trailing whitespace** - автоматическое удаление пробелов в конце строк
- **fix end of files** - обеспечение наличия пустой строки в конце файлов
- **check for added large files** - предотвращение коммита больших файлов (>500KB)

### 2. Проверка форматов файлов
- **check yaml** - валидация YAML файлов (docker-compose.yml, конфигурации)

### 3. Автоматическое форматирование Python кода
- **black** - автоматическое форматирование кода в соответствии со стандартами
- **isort** - автоматическая сортировка импортов

### 4. Проверка стиля кода
- **flake8** - статический анализ кода на соответствие PEP 8

```

## Использование

### Автоматический запуск
Хуки запускаются автоматически при выполнении:
```bash
git commit -m "Сообщение коммита"
```

Если проверки обнаруживают проблемы, коммит блокируется до их исправления.

### Ручной запуск проверок

```bash
    # Запуск всех проверок для всех файлов
    pre-commit run --all-files
    
    # Запуск конкретной проверки
    pre-commit run black --all-files
    pre-commit run flake8 --all-files
    
    # Запуск проверок для staged файлов
    pre-commit run
```

### Пропуск проверок (только в исключительных случаях)
```bash
    # Пропуск всех проверок
    git commit --no-verify -m "Сообщение"
    
    # Пропуск конкретных проверок через переменные окружения
    SKIP=flake8 git commit -m "Сообщение"
```

## Интеграция с IDE

### Visual Studio Code
Добавьте в настройки workspace (.vscode/settings.json):
```json
{
  "editor.formatOnSave": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### PyCharm/IntelliJ IDEA
1. Настройте внешний инструмент для black
2. Включите автоимпорт isort
3. Настройте File Watchers для автоматического форматирования

## Устранение проблем

### Если проверки не запускаются
```bash
    # Переустановка хуков
    pre-commit uninstall
    pre-commit install
    
    # Очистка кэша pre-commit
    pre-commit clean
```

### Если black изменяет слишком много файлов
```bash
    # Запуск black в режиме проверки (без изменений)
    black --check app/
    
    # Применение изменений только к конкретным файлам
    black app/api/v1/endpoints/prices.py
```

### Обновление версий хуков
```bash
    # Автоматическое обновление до последних версий
    pre-commit autoupdate
    
    # Обновление конкретного репозитория
    pre-commit autoupdate --repo https://github.com/psf/black
```

Эта система обеспечивает высокое качество кода и единые стандарты разработки для всех участников проекта.

## Контакты

Проект разработан в рамках тестового задания на позицию Junior Backend Developer.

По вопросам и предложениям:

- **Telegram**: [@maxsvirilin](https://t.me/svirilinmax)
- **Email**: [mak.svirilin@gmail.com](mailto:mak.svirilin@gmail.com)

## Лицензия

Этот проект лицензирован под лицензией MIT - см. файл [LICENSE](LICENSE).
