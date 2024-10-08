from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class CustomConversion(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        aggregation_rule: str
        business: str
        creation_time: str
        custom_event_type: str
        data_sources: str
        default_conversion_value: str
        description: str
        event_source_type: str
        first_fired_time: str
        id: str
        is_archived: str
        is_unavailable: str
        last_fired_time: str
        name: str
        offline_conversion_data_set: str
        pixel: str
        retention_days: str
        rule: str
        action_source_type: str
        advanced_rule: str
        event_source_id: str
        custom_conversion_id: str
    class CustomEventType:
        add_payment_info: str
        add_to_cart: str
        add_to_wishlist: str
        complete_registration: str
        contact: str
        content_view: str
        customize_product: str
        donate: str
        facebook_selected: str
        find_location: str
        initiated_checkout: str
        lead: str
        listing_interaction: str
        other: str
        purchase: str
        schedule: str
        search: str
        start_trial: str
        submit_application: str
        subscribe: str
    class ActionSourceType:
        app: str
        business_messaging: str
        chat: str
        email: str
        other: str
        phone_call: str
        physical_store: str
        system_generated: str
        website: str
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_stats(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
