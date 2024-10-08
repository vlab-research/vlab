from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class MerchantCompliance(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        active_campaigns: str
        compliance_status: str
        count_down_start_time: str
        purchase: str
        purchase_conversion_value: str
