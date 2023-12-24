from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class LookalikeSpec(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        country: str
        is_financial_service: str
        origin: str
        origin_event_name: str
        origin_event_source_name: str
        origin_event_source_type: str
        product_set_name: str
        ratio: str
        starting_ratio: str
        target_countries: str
        target_country_names: str
        type: str
