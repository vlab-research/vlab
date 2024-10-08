from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdAccountOptimizationGoalsAEMv2Eligibility(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        is_disabled: str
        optimization_goal: str
    class OptimizationGoal:
        ad_recall_lift: str
        app_installs: str
        app_installs_and_offsite_conversions: str
        conversations: str
        derived_events: str
        engaged_users: str
        event_responses: str
        impressions: str
        in_app_value: str
        landing_page_views: str
        lead_generation: str
        link_clicks: str
        meaningful_call_attempt: str
        messaging_appointment_conversion: str
        messaging_purchase_conversion: str
        none: str
        offsite_conversions: str
        page_likes: str
        post_engagement: str
        profile_visit: str
        quality_call: str
        quality_lead: str
        reach: str
        reminders_set: str
        subscribers: str
        thruplay: str
        value: str
        visit_instagram_profile: str
