from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class ThirdPartyPartnerPanelScheduled(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        adentities_ids: str
        cadence: str
        country: str
        created_time: str
        description: str
        end_time: str
        id: str
        modified_time: str
        owner_instance_id: str
        owner_panel_id: str
        owner_panel_name: str
        start_time: str
        status: str
        study_type: str
    class Status:
        cancelled: str
        created: str
        finished: str
        ongoing: str
    class StudyType:
        brand_lift: str
        panel_sales_attribution: str
        reach: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
