from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CopyrightAttributionInsights(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        l7_attribution_page_view: str
        l7_attribution_page_view_delta: str
        l7_attribution_video_view: str
        l7_attribution_video_view_delta: str
        metrics_ending_date: str
