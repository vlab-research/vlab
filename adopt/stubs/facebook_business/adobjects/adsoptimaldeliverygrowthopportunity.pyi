from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class AdsOptimalDeliveryGrowthOpportunity(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        child_metadata: str = ...
        metadata: str = ...
        optimization_type: str = ...