from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class MIXInsightsResult(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        daily_age_gender_breakdown: str
        daily_audio_library_values: str
        daily_ugc_values: str
        daily_values: str
        metric: str
        monthly_audio_library_values: str
        monthly_ugc_values: str
        monthly_values: str
        percent_growth: str
        shielded_fields: str
        total_age_gender_breakdown: str
        total_audio_library_value: str
        total_country_breakdown: str
        total_locale_breakdown: str
        total_product_breakdown: str
        total_ugc_value: str
        total_value: str
        trending_age: str
        trending_gender: str
        trending_interest: str
        trending_territory: str
