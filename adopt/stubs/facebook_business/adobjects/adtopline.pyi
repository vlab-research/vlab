from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdTopline(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        client_approval_date: str
        created_by: str
        created_date: str
        description: str
        flight_end_date: str
        flight_start_date: str
        func_cap_amount: str
        func_cap_amount_with_offset: str
        func_line_amount: str
        func_line_amount_with_offset: str
        func_price: str
        func_price_with_offset: str
        gender: str
        id: str
        impressions: str
        io_number: str
        is_bonus_line: str
        keywords: str
        last_updated_by: str
        last_updated_date: str
        line_number: str
        line_position: str
        line_type: str
        location: str
        max_age: str
        max_budget: str
        min_age: str
        price_per_trp: str
        product_type: str
        rev_assurance_approval_date: str
        targets: str
        trp_updated_time: str
        trp_value: str
        uom: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
