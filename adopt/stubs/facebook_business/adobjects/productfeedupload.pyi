from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker
from typing import Any, Optional

class ProductFeedUpload(AbstractCrudObject):
    def __init__(self, fbid: Optional[Any] = ..., parent_id: Optional[Any] = ..., api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        end_time: str = ...
        error_count: str = ...
        error_report: str = ...
        filename: str = ...
        id: str = ...
        input_method: str = ...
        num_deleted_items: str = ...
        num_detected_items: str = ...
        num_invalid_items: str = ...
        num_persisted_items: str = ...
        start_time: str = ...
        url: str = ...
        warning_count: str = ...
    class InputMethod:
        google_sheets_fetch: str = ...
        manual_upload: str = ...
        reupload_last_file: str = ...
        server_fetch: str = ...
        user_initiated_server_fetch: str = ...
    @classmethod
    def get_endpoint(cls): ...
    def api_get(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def create_error_report(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...
    def get_errors(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...