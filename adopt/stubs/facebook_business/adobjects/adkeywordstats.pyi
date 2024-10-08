from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdKeywordStats(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        actions: str
        clicks: str
        cost_per_total_action: str
        cost_per_unique_click: str
        cpc: str
        cpm: str
        cpp: str
        ctr: str
        frequency: str
        id: str
        impressions: str
        name: str
        reach: str
        spend: str
        total_actions: str
        total_unique_actions: str
        unique_actions: str
        unique_clicks: str
        unique_ctr: str
        unique_impressions: str
    @classmethod
    def get_endpoint(cls): ...
