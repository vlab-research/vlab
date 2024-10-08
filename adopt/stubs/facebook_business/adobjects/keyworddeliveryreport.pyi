from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class KeywordDeliveryReport(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        estimated_clicks: str
        estimated_conversions: str
        estimated_cost: str
        estimated_cpc: str
        estimated_ctr: str
        estimated_cvr: str
        estimated_impressions: str
        estimated_returns: str
        keyword: str
