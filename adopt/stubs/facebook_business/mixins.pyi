from facebook_business.exceptions import FacebookBadObjectError as FacebookBadObjectError
from typing import Any, Optional

class CanValidate:
    def remote_validate(self, params: Optional[Any] = ...): ...

class CanArchive:
    def remote_delete(self, batch: Optional[Any] = ..., failure: Optional[Any] = ..., success: Optional[Any] = ...): ...
    def remote_archive(self, batch: Optional[Any] = ..., failure: Optional[Any] = ..., success: Optional[Any] = ...): ...

class CannotCreate:
    @classmethod
    def remote_create(cls, *args: Any, **kwargs: Any) -> None: ...

class CannotDelete:
    @classmethod
    def remote_delete(cls, *args: Any, **kwargs: Any) -> None: ...

class CannotUpdate:
    @classmethod
    def remote_update(cls, *args: Any, **kwargs: Any) -> None: ...

class HasObjective:
    class Objective:
        brand_awareness: str = ...
        canvas_app_engagement: str = ...
        canvas_app_installs: str = ...
        event_responses: str = ...
        lead_generation: str = ...
        local_awareness: str = ...
        mobile_app_engagement: str = ...
        mobile_app_installs: str = ...
        none: str = ...
        offer_claims: str = ...
        page_likes: str = ...
        post_engagement: str = ...
        link_clicks: str = ...
        conversions: str = ...
        video_views: str = ...
        product_catalog_sales: str = ...

class HasStatus:
    class Status:
        active: str = ...
        archived: str = ...
        deleted: str = ...
        paused: str = ...

class HasBidInfo:
    class BidInfo:
        actions: str = ...
        clicks: str = ...
        impressions: str = ...
        reach: str = ...
        social: str = ...

class HasAdLabels:
    def add_labels(self, labels: Optional[Any] = ...): ...
    def remove_labels(self, labels: Optional[Any] = ...): ...

class ValidatesFields:
    def __setitem__(self, key: Any, value: Any) -> None: ...
