from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdVolume(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_volume_break_down: str
        ads_running_or_in_review_count: str
        future_limit_activation_date: str
        future_limit_on_ads_running_or_in_review: str
        individual_accounts_ad_volume: str
        is_gpa_page: str
        limit_on_ads_running_or_in_review: str
        owning_business_ad_volume: str
        partner_business_ad_volume: str
        user_role: str
