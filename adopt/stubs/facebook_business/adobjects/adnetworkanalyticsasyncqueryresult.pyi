from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class AdNetworkAnalyticsAsyncQueryResult(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        data: str = ...
        error: str = ...
        query_id: str = ...
        results: str = ...
        status: str = ...