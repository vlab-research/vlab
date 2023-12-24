from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CanvasAdSettings(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        is_canvas_collection_eligible: str
        lead_form_created_time: str
        lead_form_name: str
        lead_gen_form_id: str
        leads_count: str
        product_set_id: str
        use_retailer_item_ids: str
