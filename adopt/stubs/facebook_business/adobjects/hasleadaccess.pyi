from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class HasLeadAccess(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        app_has_leads_permission: str
        can_access_lead: str
        enabled_lead_access_manager: str
        failure_reason: str
        failure_resolution: str
        is_page_admin: str
        page_id: str
        user_has_leads_permission: str
        user_id: str
