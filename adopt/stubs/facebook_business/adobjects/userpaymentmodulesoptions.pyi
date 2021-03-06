from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class UserPaymentModulesOptions(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str = ...
        available_payment_options: str = ...
        country: str = ...
        currency: str = ...
