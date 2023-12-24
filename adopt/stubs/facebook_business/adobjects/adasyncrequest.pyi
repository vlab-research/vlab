from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdAsyncRequest(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        async_request_set: str
        created_time: str
        id: str
        input: str
        result: str
        scope_object_id: str
        status: str
        type: str
        updated_time: str
    class Statuses:
        canceled: str
        canceled_dependency: str
        error: str
        error_conflicts: str
        error_dependency: str
        initial: str
        in_progress: str
        pending_dependency: str
        process_by_ad_async_engine: str
        process_by_event_processor: str
        success: str
        user_canceled: str
        user_canceled_dependency: str
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
