from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class SavedAudience(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account: str
        approximate_count_lower_bound: str
        approximate_count_upper_bound: str
        delete_time: str
        description: str
        id: str
        name: str
        operation_status: str
        owner_business: str
        page_deletion_marked_delete_time: str
        permission_for_actions: str
        run_status: str
        sentence_lines: str
        targeting: str
        time_created: str
        time_updated: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
