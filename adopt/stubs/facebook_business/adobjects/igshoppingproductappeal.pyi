from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class IGShoppingProductAppeal(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        eligible_for_appeal: str
        product_appeal_status: str
        product_id: str
        rejection_reasons: str
        review_status: str
