from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ShadowIGMediaBoostedInsightsResult(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        description: str
        name: str
        organic_media_id: str
        source_type: str
        title: str
        values: str
