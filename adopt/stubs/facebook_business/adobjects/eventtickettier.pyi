from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class EventTicketTier(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        currency: str
        description: str
        end_sales_time: str
        end_show_time: str
        fee_settings: str
        id: str
        maximum_quantity: str
        metadata: str
        minimum_quantity: str
        name: str
        price: str
        priority: str
        retailer_id: str
        seating_map_image_url: str
        start_sales_time: str
        start_show_time: str
        status: str
        total_quantity: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
