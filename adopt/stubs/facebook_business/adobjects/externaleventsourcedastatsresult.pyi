from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ExternalEventSourceDAStatsResult(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        count_content_ids: str
        count_content_ids_match_any_catalog: str
        count_fires: str
        count_fires_match_any_catalog: str
        date: str
        percentage_missed_users: str
