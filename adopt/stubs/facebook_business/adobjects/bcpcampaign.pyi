from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class BCPCampaign(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ads_permission_required: str
        application_deadline: str
        campaign_goal: str
        campaign_goal_other: str
        content_delivery_deadline: str
        content_delivery_start_date: str
        content_requirements: str
        content_requirements_description: str
        currency: str
        deal_negotiation_type: str
        description: str
        has_free_product: str
        id: str
        name: str
        payment_amount_for_ads: str
        payment_amount_for_content: str
        payment_description: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
