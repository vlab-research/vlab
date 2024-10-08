from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ResellerGuidance(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ad_account_first_spend_date: str
        ad_account_id: str
        adopted_guidance_l7d: str
        advertiser_name: str
        attributed_to_reseller_l7d: str
        available_guidance: str
        benchmark_report_link: str
        guidance_adoption_rate_l7d: str
        no_adsets_gte_benchmark: str
        no_adsets_lt_benchmark: str
        nurtured_by_reseller_l7d: str
        planning_agency_name: str
        recommendation_time: str
        reporting_ds: str
        reseller: str
        revenue_l30d: str
        ultimate_advertiser_name: str
