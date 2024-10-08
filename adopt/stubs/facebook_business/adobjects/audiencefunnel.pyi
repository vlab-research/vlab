from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AudienceFunnel(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        audience_type_param_name: str
        audience_type_param_tags: str
        custom_audience_groups_info: str
