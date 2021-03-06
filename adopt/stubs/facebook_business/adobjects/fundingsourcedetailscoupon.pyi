from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class FundingSourceDetailsCoupon(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        amount: str = ...
        currency: str = ...
        display_amount: str = ...
        expiration: str = ...
