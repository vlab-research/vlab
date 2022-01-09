from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker
from typing import Any, Optional

class CopyrightReferenceContainer(AbstractCrudObject):
    def __init__(self, fbid: Optional[Any] = ..., parent_id: Optional[Any] = ..., api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        content_type: str = ...
        copyright_creation_time: str = ...
        download_hd_url: str = ...
        duration_in_sec: str = ...
        id: str = ...
        iswc: str = ...
        metadata: str = ...
        published_time: str = ...
        thumbnail_url: str = ...
        title: str = ...
        universal_content_id: str = ...
        writer_names: str = ...