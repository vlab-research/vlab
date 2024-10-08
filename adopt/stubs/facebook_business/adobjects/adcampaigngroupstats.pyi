from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCampaignGroupStats(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        actions: str
        campaign_group_id: str
        clicks: str
        end_time: str
        impressions: str
        inline_actions: str
        social_clicks: str
        social_impressions: str
        social_spent: str
        social_unique_clicks: str
        social_unique_impressions: str
        spent: str
        start_time: str
        unique_clicks: str
        unique_impressions: str
