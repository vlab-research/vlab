from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class PartnerIntegrationLinked(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ads_pixel: str
        application: str
        completed_integration_types: str
        external_business_connection_id: str
        external_id: str
        has_oauth_token: str
        id: str
        mbe_app_id: str
        mbe_asset_id: str
        mbe_external_business_id: str
        name: str
        offline_conversion_data_set: str
        page: str
        partner: str
        product_catalog: str
        setup_status: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
