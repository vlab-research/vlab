from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CollaborativeAdsPartnerBusinesses(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        collaborative_ads_partner_businesses_info: str
        dedicated_partner_business_info: str
