from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class PageLocationsBreakdown(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        location_id: str
        location_name: str
        location_type: str
        num_pages: str
        num_pages_eligible_for_store_visit_reporting: str
        num_unpublished_or_closed_pages: str
        parent_country_code: str
        parent_region_id: str
        parent_region_name: str
