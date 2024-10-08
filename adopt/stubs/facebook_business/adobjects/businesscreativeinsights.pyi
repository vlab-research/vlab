from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class BusinessCreativeInsights(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        actions: str
        age: str
        country: str
        date_end: str
        date_start: str
        device_platform: str
        gender: str
        impressions: str
        inline_link_clicks: str
        objective: str
        optimization_goal: str
        platform_position: str
        publisher_platform: str
        quality_ranking: str
        video_play_actions: str
        video_thruplay_watched_actions: str
