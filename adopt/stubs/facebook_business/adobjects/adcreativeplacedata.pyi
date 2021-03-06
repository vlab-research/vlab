from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class AdCreativePlaceData(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        address_string: str = ...
        label: str = ...
        latitude: str = ...
        location_source_id: str = ...
        longitude: str = ...
        type: str = ...
