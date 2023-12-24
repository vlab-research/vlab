from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.helpers.adreportrunmixin import AdReportRunMixin as AdReportRunMixin
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdReportRun(AdReportRunMixin, AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        async_percent_completion: str
        async_status: str
        date_start: str
        date_stop: str
        emails: str
        friendly_name: str
        id: str
        is_bookmarked: str
        is_running: str
        schedule_id: str
        time_completed: str
        time_ref: str
        action_attribution_windows: str
        action_breakdowns: str
        action_report_time: str
        breakdowns: str
        date_preset: str
        default_summary: str
        export_columns: str
        export_format: str
        export_name: str
        fields: str
        filtering: str
        level: str
        product_id_limit: str
        sort: str
        summary: str
        summary_action_breakdowns: str
        time_increment: str
        time_range: str
        time_ranges: str
        use_account_attribution_setting: str
        use_unified_attribution_setting: str
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_insights(self, fields: Incomplete | None = None, params: Incomplete | None = None, is_async: bool = False, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
