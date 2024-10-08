from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdsCustomPivotsPreview(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        account_name: str
        ad_id: str
        ad_name: str
        adset_id: str
        adset_name: str
        campaign_id: str
        campaign_name: str
        custom_breakdown: str
