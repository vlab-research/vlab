from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdCampaignMetricsMetadata(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        boosted_component_optimization: str
        creation_flow_tips: str
        default_opted_in_placements: str
        delivery_growth_optimizations: str
        duplication_flow_tips: str
        edit_flow_tips: str
