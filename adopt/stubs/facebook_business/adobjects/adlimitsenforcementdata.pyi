from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdLimitsEnforcementData(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_limit_on_page: str
        ad_limit_on_scope: str
        ad_volume_on_page: str
        ad_volume_on_scope: str
        is_admin: str
        page_name: str
