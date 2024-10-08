from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAccountPromotionProgressBar(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        adaccount_permission: str
        coupon_currency: str
        coupon_value: str
        expiration_time: str
        progress_completed: str
        promotion_type: str
        spend_requirement_in_cent: str
        spend_since_enrollment: str
