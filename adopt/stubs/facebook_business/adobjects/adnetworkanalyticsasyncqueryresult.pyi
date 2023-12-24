from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdNetworkAnalyticsAsyncQueryResult(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        data: str
        error: str
        omitted_results: str
        query_id: str
        results: str
        status: str
