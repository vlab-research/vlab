from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CatalogSegmentAllMatchCountLaser(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        date_start: str
        date_stop: str
        event: str
        source: str
        total_matched_content_ids: str
        unique_matched_content_ids: str
