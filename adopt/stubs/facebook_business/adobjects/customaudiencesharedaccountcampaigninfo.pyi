from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CustomAudienceSharedAccountCampaignInfo(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        account_name: str
        adset_excluding_count: str
        adset_including_count: str
        campaign_delivery_status: str
        campaign_objective: str
        campaign_pages: str
        campaign_schedule: str
