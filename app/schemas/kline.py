from pydantic import BaseModel
from typing import Literal


class KlineData(BaseModel):
    ts: int                  # timestamp в миллисекундах
    o: float                 # open
    h: float                 # high
    l: float                 # low
    c: float                 # close
    v: float                 # volume
    t: float                 # turnover (объем в деньгах)
    dt: str                  # дата в человекочитаемом виде


class KlineUpdateData(BaseModel):
    symbol: str              # например, BTCUSDT
    interval: int            # интервал свечи в секундах или минутах
    ex: str                  # биржа, например 'bybit'
    data: KlineData          # данные свечи


class KlineUpdate(BaseModel):
    type: Literal['kline_update']
    data: KlineUpdateData