from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.deps import get_db
from app.core.logging import get_logger
from app.schemas.price import PriceCreate, PriceResponse
from app.services.price_service import PriceService

logger = get_logger(__name__)

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get(
    "/",
    response_model=List[PriceResponse],
    summary="Получить все цены по тикеру",
    description="Возвращает список цен для указанного тикера с пагинацией.",
)
async def get_prices(
    ticker: str = Query(
        ...,
        min_length=3,
        description="Тикер криптовалюты (например: btc_usd, eth_usd)",
        examples=["btc_usd", "eth_usd"],
    ),
    skip: int = Query(
        0, ge=0, description="Количество записей для пропуска (пагинация)", example=0
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Максимальное количество записей для возврата",
        example=100,
    ),
    db: Session = Depends(get_db),
) -> List[PriceResponse]:
    """
    Получить все сохраненные цены для указанного тикера.

    Args:
        ticker: Тикер криптовалюты
        skip: Пропустить первые N записей
        limit: Ограничить количество возвращаемых записей

    Returns:
        Список цен в формате PriceResponse
    """
    logger.info(
        "Запрос всех цен", extra={"ticker": ticker, "skip": skip, "limit": limit}
    )

    try:
        prices = PriceService.get_prices(db, ticker=ticker, skip=skip, limit=limit)

        logger.debug(
            "Успешно получены цены", extra={"ticker": ticker, "count": len(prices)}
        )

        return prices

    except Exception as e:
        logger.error(
            "Ошибка при получении цен", extra={"ticker": ticker, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении цен: {str(e)}",
        )


@router.get(
    "/latest",
    response_model=PriceResponse,
    summary="Получить последнюю цену",
    description="Возвращает последнюю сохраненную цену для указанного тикера.",
)
async def get_latest_price(
    ticker: str = Query(
        ...,
        min_length=3,
        description="Тикер криптовалюты (например: btc_usd, eth_usd)",
        examples=["btc_usd", "eth_usd"],
    ),
    db: Session = Depends(get_db),
) -> PriceResponse:
    """
    Получить последнюю сохраненную цену для указанного тикера.

    Args:
        ticker: Тикер криптовалюты

    Returns:
        Последняя цена в формате PriceResponse

    Raises:
        HTTPException 404: Если цены для указанного тикера не найдены
    """
    logger.info("Запрос последней цены", extra={"ticker": ticker})

    try:
        price = PriceService.get_latest_price(db, ticker)

        if not price:
            logger.warning("Цена не найдена", extra={"ticker": ticker})
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Цены для тикера '{ticker}' не найдены",
            )

        logger.debug(
            "Успешно получена последняя цена",
            extra={
                "ticker": ticker,
                "price": price.price,
                "timestamp": price.timestamp,
            },
        )

        return price

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Ошибка при получении последней цены",
            extra={"ticker": ticker, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении последней цены: {str(e)}",
        )


@router.get(
    "/filter",
    response_model=List[PriceResponse],
    summary="Получить цены с фильтром по дате",
    description="Возвращает цены для указанного тикера в заданном временном диапазоне.",
)
async def filter_prices_by_date(
    ticker: str = Query(
        ...,
        min_length=3,
        description="Тикер криптовалюты (например: btc_usd, eth_usd)",
        examples=["btc_usd", "eth_usd"],
    ),
    start: Optional[int] = Query(
        None,
        ge=0,
        description="Начальный timestamp в миллисекундах",
        example=1672531200000,
    ),
    end: Optional[int] = Query(
        None,
        ge=0,
        description="Конечный timestamp в миллисекундах",
        example=1675123199000,
    ),
    db: Session = Depends(get_db),
) -> List[PriceResponse]:
    """
    Получить цены для указанного тикера в заданном временном диапазоне.

    Args:
        ticker: Тикер криптовалюты
        start: Начальный timestamp (миллисекунды). Если не указан - с начала данных
        end: Конечный timestamp (миллисекунды). Если не указан - до текущего времени

    Returns:
        Список цен в заданном диапазоне

    Raises:
        HTTPException 400: Если start > end
    """
    logger.info(
        "Запрос цен с фильтром по дате",
        extra={"ticker": ticker, "start": start, "end": end},
    )

    if start is not None and end is not None and start > end:
        logger.warning(
            "Некорректный временной диапазон",
            extra={"ticker": ticker, "start": start, "end": end},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Начальный timestamp не может быть больше конечного",
        )

    try:
        prices = PriceService.get_prices_by_date_range(
            db, ticker=ticker, start_timestamp=start, end_timestamp=end
        )

        logger.debug(
            "Успешно получены отфильтрованные цены",
            extra={"ticker": ticker, "count": len(prices), "start": start, "end": end},
        )

        return prices

    except Exception as e:
        logger.error(
            "Ошибка при фильтрации цен",
            extra={"ticker": ticker, "start": start, "end": end, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при фильтрации цен: {str(e)}",
        )


@router.get(
    "/stats",
    response_model=dict,
    summary="Получить статистику по ценам",
    description="Возвращает статистическую информацию по ценам для указанного тикера.",
)
async def get_price_stats(
    ticker: str = Query(
        ...,
        min_length=3,
        description="Тикер криптовалюты (например: btc_usd, eth_usd)",
        examples=["btc_usd", "eth_usd"],
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Получить статистику по ценам для указанного тикера.

    Статистика включает:
    - count: общее количество записей
    - min_price: минимальная цена
    - max_price: максимальная цена
    - avg_price: средняя цена
    - first_timestamp: timestamp первой записи
    - last_timestamp: timestamp последней записи

    Args:
        ticker: Тикер криптовалюты

    Returns:
        Словарь со статистикой
    """
    logger.info("Запрос статистики по ценам", extra={"ticker": ticker})

    try:
        stats = PriceService.get_stats(db, ticker)

        logger.debug(
            "Успешно получена статистика",
            extra={"ticker": ticker, "count": stats.get("count")},
        )

        return stats

    except Exception as e:
        logger.error(
            "Ошибка при получении статистики", extra={"ticker": ticker, "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении статистики: {str(e)}",
        )


@router.post(
    "/",
    response_model=PriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую запись о цене",
    description="Создает новую запись о цене в базе данных. "
    "В основном для тестирования.",
)
async def create_price(
    price_data: PriceCreate,
    db: Session = Depends(get_db),
) -> PriceResponse:
    """
    Создать новую запись о цене.

    Примечание: Этот эндпоинт в основном предназначен для тестирования.
    В production ценами управляет Celery задача.

    Args:
        price_data: Данные для создания записи о цене

    Returns:
        Созданная запись о цене
    """
    logger.info(
        "Создание записи о цене",
        extra={"ticker": price_data.ticker, "price": price_data.price},
    )

    try:
        price = PriceService.create_price(db, price_data)

        logger.debug(
            "Успешно создана запись о цене",
            extra={"ticker": price.ticker, "price_id": price.id},
        )

        return price

    except Exception as e:
        logger.error(
            "Ошибка при создании записи о цене",
            extra={"ticker": price_data.ticker, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании записи о цене: {str(e)}",
        )


@router.get(
    "/available-tickers",
    response_model=List[str],
    summary="Получить список доступных тикеров",
    description="Возвращает список тикеров, для которых есть данные в базе.",
)
async def get_available_tickers(
    db: Session = Depends(get_db),
) -> List[str]:
    """
    Получить список уникальных тикеров, для которых есть данные в базе.

    Returns:
        Список уникальных тикеров
    """
    logger.info("Запрос списка доступных тикеров")

    try:
        from sqlalchemy import distinct

        from app.db.models import Price

        tickers = db.query(distinct(Price.ticker)).order_by(Price.ticker).all()
        result = [ticker[0] for ticker in tickers]

        logger.debug(
            "Успешно получен список тикеров",
            extra={"tickers": result, "count": len(result)},
        )

        return result

    except Exception as e:
        logger.error("Ошибка при получении списка тикеров", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении списка тикеров: {str(e)}",
        )
