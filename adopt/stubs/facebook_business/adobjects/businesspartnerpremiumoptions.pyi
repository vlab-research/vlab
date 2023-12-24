from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class BusinessPartnerPremiumOptions(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        enable_basket_insight: str
        enable_extended_audience_retargeting: str
        retailer_custom_audience_config: str
