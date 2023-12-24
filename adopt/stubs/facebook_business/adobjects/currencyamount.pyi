from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CurrencyAmount(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        amount: str
        amount_in_hundredths: str
        currency: str
        offsetted_amount: str
