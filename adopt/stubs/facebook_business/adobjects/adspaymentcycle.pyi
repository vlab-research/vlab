from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdsPaymentCycle(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        created_time: str
        multiplier: str
        requested_threshold_amount: str
        threshold_amount: str
        updated_time: str
