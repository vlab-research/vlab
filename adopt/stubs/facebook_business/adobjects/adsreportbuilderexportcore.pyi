from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdsReportBuilderExportCore(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        async_percent_completion: str
        async_report_url: str
        async_status: str
        client_creation_value: str
        expiry_time: str
        export_download_time: str
        export_format: str
        export_name: str
        export_type: str
        has_seen: str
        id: str
        is_sharing: str
        link_sharing_expiration_time: str
        link_sharing_uri: str
        time_completed: str
        time_start: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
