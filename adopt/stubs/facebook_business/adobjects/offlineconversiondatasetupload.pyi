from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class OfflineConversionDataSetUpload(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        api_calls: str
        creation_time: str
        duplicate_entries: str
        event_stats: str
        event_time_max: str
        event_time_min: str
        first_upload_time: str
        id: str
        is_excluded_for_lift: str
        last_upload_time: str
        match_rate_approx: str
        matched_entries: str
        upload_tag: str
        valid_entries: str
    class Order:
        ascending: str
        descending: str
    class SortBy:
        api_calls: str
        creation_time: str
        event_time_max: str
        event_time_min: str
        first_upload_time: str
        is_excluded_for_lift: str
        last_upload_time: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_progress(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_pull_sessions(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
