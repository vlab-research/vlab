from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ReportingAudience(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        custom_audiences: str
        custom_audiences_url_param_name: str
        custom_audiences_url_param_type: str
