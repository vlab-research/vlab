from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdsReportBuilderSavedReport(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        action_report_time: str
        ad_account_id: str
        attribution_windows: str
        comparison_date_interval: str
        creation_source: str
        creation_time: str
        currency: str
        date_interval: str
        date_preset: str
        default_attribution_windows: str
        dimension_groups: str
        dimensions: str
        filtering: str
        formatting: str
        id: str
        last_access_by: str
        last_access_time: str
        last_report_snapshot_id: str
        last_report_snapshot_time: str
        last_shared_report_expiration: str
        limit: str
        locked_dimensions: str
        metrics: str
        report_name: str
        report_snapshot_async_percent_completion: str
        report_snapshot_async_status: str
        schedule_frequency: str
        scope: str
        show_deprecate_aw_banner: str
        sorting: str
        start_date: str
        status: str
        subscribers: str
        update_by: str
        update_time: str
        user: str
        user_dimensions: str
        user_metrics: str
        view_type: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
