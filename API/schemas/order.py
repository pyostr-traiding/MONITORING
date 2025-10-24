from typing import Literal, Any

from pydantic import BaseModel


class OrderSchema(BaseModel):
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

    created_at: Any