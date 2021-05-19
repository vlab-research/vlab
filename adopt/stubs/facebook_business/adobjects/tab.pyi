from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker
from typing import Any, Optional

class Tab(AbstractCrudObject):
    def __init__(self, fbid: Optional[Any] = ..., parent_id: Optional[Any] = ..., api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        application: str = ...
        custom_image_url: str = ...
        custom_name: str = ...
        id: str = ...
        image_url: str = ...
        is_non_connection_landing_tab: str = ...
        is_permanent: str = ...
        link: str = ...
        name: str = ...
        position: str = ...