from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCreativeMarketingMessageStructuredSpec(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        buttons: str
        footer: str
        greeting: str
        language: str
        referenced_adgroup_id: str
        whats_app_business_phone_number_id: str
