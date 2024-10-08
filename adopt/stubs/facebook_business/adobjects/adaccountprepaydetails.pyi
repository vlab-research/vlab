from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAccountPrepayDetails(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        default_funding_amount: str
        max_acceptable_amount: str
        min_acceptable_amount: str
        should_collect_business_details: str
