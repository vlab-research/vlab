from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class BrandRequest(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_countries: str
        additional_contacts: str
        approval_level: str
        cells: str
        countries: str
        deny_reason: str
        end_time: str
        estimated_reach: str
        id: str
        is_multicell: str
        locale: str
        max_age: str
        min_age: str
        questions: str
        region: str
        request_status: str
        review_date: str
        start_time: str
        status: str
        submit_date: str
        total_budget: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
