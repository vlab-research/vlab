from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class CatalogSmartPixelSettings(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        allowed_domains: str
        available_property_filters: str
        catalog: str
        cbb_custom_override_filters: str
        cbb_default_filter: str
        cbb_default_filter_crawl_params: str
        cbb_override_type_field_mapping: str
        defaults: str
        filters: str
        id: str
        is_cbb_enabled: str
        is_create_enabled: str
        is_delete_enabled: str
        is_update_enabled: str
        microdata_format_precedence: str
        pixel: str
        property_filter: str
        retention_time_sec: str
        trusted_domains: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
