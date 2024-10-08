from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class OrderIDAttributions(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        app_id: str
        attribution_type: str
        attributions: str
        conversion_device: str
        dataset_id: str
        holdout_status: str
        order_id: str
        order_timestamp: str
        pixel_id: str
