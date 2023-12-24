from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CommercePayout(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        amount: str
        payout_date: str
        payout_reference_id: str
        status: str
        transfer_id: str
