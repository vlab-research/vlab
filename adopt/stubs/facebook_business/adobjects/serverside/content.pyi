from typing import Any

class Content:
    param_types: Any = ...
    def __init__(self, product_id: str=..., quantity: int=..., item_price: float=...) -> None: ...
    @property
    def product_id(self): ...
    @product_id.setter
    def product_id(self, product_id: Any) -> None: ...
    @property
    def quantity(self): ...
    @quantity.setter
    def quantity(self, quantity: Any) -> None: ...
    @property
    def item_price(self): ...
    @item_price.setter
    def item_price(self, item_price: Any) -> None: ...
    def normalize(self): ...
    def to_dict(self): ...
    def to_str(self): ...
    def __eq__(self, other: Any) -> Any: ...
    def __ne__(self, other: Any) -> Any: ...
