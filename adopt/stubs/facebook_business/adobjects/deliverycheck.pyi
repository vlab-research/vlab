from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class DeliveryCheck(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        check_name: str = ...
        description: str = ...
        extra_info: str = ...
        summary: str = ...
