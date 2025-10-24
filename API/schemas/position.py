import time
import uuid

from pydantic import BaseModel
from typing import Literal, Any


class PositionSchema(BaseModel):
    class Config:
        from_attributes = True

    id: int

    symbol_name: str = 'BTCUSDT'
    status: str

    uuid: str
    category: Literal['spot', 'option']
    side: Literal['buy', 'sell']
    qty_tokens: str
    price: str
    is_test: bool

    created_at: Any
