from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class InsightsResult(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        description: str
        description_from_api_doc: str
        id: str
        name: str
        period: str
        title: str
        values: str
    class DatePreset:
        data_maximum: str
        last_14d: str
        last_28d: str
        last_30d: str
        last_3d: str
        last_7d: str
        last_90d: str
        last_month: str
        last_quarter: str
        last_week_mon_sun: str
        last_week_sun_sat: str
        last_year: str
        maximum: str
        this_month: str
        this_quarter: str
        this_week_mon_today: str
        this_week_sun_today: str
        this_year: str
        today: str
        yesterday: str
    class Period:
        day: str
        days_28: str
        lifetime: str
        month: str
        total_over_range: str
        week: str
