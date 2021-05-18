from facebook_business.adobjects.adsinsights import AdsInsights as AdsInsights
from typing import Any, Optional

class BusinessMixin:
    def get_insights(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., is_async: bool = ...): ...
