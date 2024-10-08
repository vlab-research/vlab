from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ContentDeliveryReport(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        content_name: str
        content_url: str
        creator_name: str
        creator_url: str
        estimated_impressions: str
