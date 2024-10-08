from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdCampaignStats(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        actions: str
        adgroup_id: str
        campaign_id: str
        campaign_ids: str
        clicks: str
        end_time: str
        id: str
        impressions: str
        inline_actions: str
        io_number: str
        is_completed: str
        line_number: str
        newsfeed_position: str
        social_clicks: str
        social_impressions: str
        social_spent: str
        social_unique_clicks: str
        social_unique_impressions: str
        spent: str
        start_time: str
        topline_id: str
        unique_clicks: str
        unique_impressions: str
