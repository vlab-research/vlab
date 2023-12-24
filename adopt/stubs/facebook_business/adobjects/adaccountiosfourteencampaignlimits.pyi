from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAccountIosFourteenCampaignLimits(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        campaign_group_limit: str
        campaign_group_limits_details: str
        campaign_limit: str
