from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.helpers.adimagemixin import AdImageMixin as AdImageMixin
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker
from typing import Any, Optional

class AdImage(AdImageMixin, AbstractCrudObject):
    def __init__(self, fbid: Optional[Any] = ..., parent_id: Optional[Any] = ..., api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str = ...
        created_time: str = ...
        creatives: str = ...
        hash: str = ...
        height: str = ...
        id: str = ...
        is_associated_creatives_in_adgroups: str = ...
        name: str = ...
        original_height: str = ...
        original_width: str = ...
        permalink_url: str = ...
        status: str = ...
        updated_time: str = ...
        url: str = ...
        url_128: str = ...
        width: str = ...
        bytes: str = ...
        copy_from: str = ...
        filename: str = ...
    class Status:
        active: str = ...
        deleted: str = ...
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id: Any, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def api_get(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...