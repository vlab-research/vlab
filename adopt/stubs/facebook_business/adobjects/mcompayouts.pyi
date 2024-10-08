from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class McomPayouts(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        number_of_orders: str
        order_ids: str
        payout_amount: str
        payout_provider_reference_id: str
        payout_status: str
        payout_time: str
        provider: str
