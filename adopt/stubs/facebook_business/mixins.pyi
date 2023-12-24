from _typeshed import Incomplete
from facebook_business.exceptions import FacebookBadObjectError as FacebookBadObjectError

class CanValidate:
    def remote_validate(self, params: Incomplete | None = None): ...

class CanArchive:
    def remote_delete(self, batch: Incomplete | None = None, failure: Incomplete | None = None, success: Incomplete | None = None): ...
    def remote_archive(self, batch: Incomplete | None = None, failure: Incomplete | None = None, success: Incomplete | None = None): ...

class CannotCreate:
    @classmethod
    def remote_create(cls, *args, **kwargs) -> None: ...

class CannotDelete:
    @classmethod
    def remote_delete(cls, *args, **kwargs) -> None: ...

class CannotUpdate:
    @classmethod
    def remote_update(cls, *args, **kwargs) -> None: ...

class HasObjective:
    class Objective:
        app_installs: str
        brand_awareness: str
        conversions: str
        event_responses: str
        lead_generation: str
        link_clicks: str
        local_awareness: str
        messages: str
        offer_claims: str
        outcome_app_promotion: str
        outcome_awareness: str
        outcome_engagement: str
        outcome_leads: str
        outcome_sales: str
        outcome_traffic: str
        page_likes: str
        post_engagement: str
        product_catalog_sales: str
        reach: str
        store_visits: str
        video_views: str

class HasStatus:
    class Status:
        active: str
        archived: str
        deleted: str
        paused: str

class HasBidInfo:
    class BidInfo:
        actions: str
        clicks: str
        impressions: str
        reach: str
        social: str

class HasAdLabels:
    def add_labels(self, labels: Incomplete | None = None): ...
    def remove_labels(self, labels: Incomplete | None = None): ...

class ValidatesFields:
    def __setitem__(self, key, value) -> None: ...
