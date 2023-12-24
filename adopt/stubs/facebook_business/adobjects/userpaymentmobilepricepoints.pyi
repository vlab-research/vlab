from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class UserPaymentMobilePricepoints(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        mobile_country: str
        phone_number_last4: str
        pricepoints: str
        user_currency: str
