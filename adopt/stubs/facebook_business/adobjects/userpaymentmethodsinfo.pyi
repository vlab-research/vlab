from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class UserPaymentMethodsInfo(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        available_card_types: str
        available_payment_methods: str
        available_payment_methods_details: str
        country: str
        currency: str
        existing_payment_methods: str
