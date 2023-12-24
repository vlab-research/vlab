from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ManagedPartnerBusiness(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_account: str
        catalog_segment: str
        extended_credit: str
        page: str
        seller_business_info: str
        seller_business_status: str
        template: str
